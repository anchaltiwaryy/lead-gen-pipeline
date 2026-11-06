"""Stage 3 - Multi-tier email enrichment engine.

For each 'qualified' lead, cascades through 4 tiers until an email is found:
  Tier 0: Public email scraped from company's own website -> accept directly.
  Tier 1a: Apollo.io Web Session (APOLLO_COOKIE) -> up to 10,000 free reveals/year
           via app.apollo.io internal API, runs headlessly on GitHub Actions.
  Tier 1b: Apollo.io REST API (APOLLO_API_KEY) -> 60 credits/month on free tier.
  Tier 2: Pattern-guess + SMTP RCPT-TO on personal name (e.g. first.last@domain).
  Tier 3: Generic mailbox SMTP probe (hello@, founders@, hr@, careers@, team@).

Applies to 'qualified' leads only - never runs on 'new'.

GitHub Actions Setup:
  - Store your Apollo session cookie as a GitHub Secret named APOLLO_COOKIE.
  - Grab it from: app.apollo.io DevTools -> Application -> Cookies -> _apollo_session
  - Cookie lifespan is typically 30-90 days. On expiry, pipeline auto-falls back to SMTP.
"""
import socket
import smtplib
import json
import time
import random
import urllib.parse
import urllib.request
import dns.resolver
from config import SMTP_FROM_ADDR, SMTP_TIMEOUT, GUESSED_EMAILS_TO_DRAFT, APOLLO_API_KEY, APOLLO_COOKIE, APOLLO_CSRF_TOKEN, APOLLO_APP_TOKEN
from db import get_conn, get_leads_by_status, update_lead

PATTERNS = [
    "{first}.{last}",
    "{first}{last}",
    "{first}",
    "{f}{last}",
    "{first}.{l}",
    "{f}.{last}",
]
HARD_REJECT = (550, 551, 553, 554)

# Hosts that return 250 for arbitrary recipients to prevent enumeration
# (Google Workspace, Outlook/Office365, iCloud, Fastmail PRD). RCPT-TO is
# unreliable there, so any result is only ever 'guessed', never 'verified'.
ANTI_ENUM_HOST_FRAGMENTS = (
    "google.com",
    ".google.com",
    "outlook.com",
    "mail.protection.outlook",
    "guard.icloud.com",
    "fastmail",
)


def _mx_is_anti_enum(mx_host: str) -> bool:
    return any(frag in mx_host for frag in ANTI_ENUM_HOST_FRAGMENTS)


def guess_candidates(first: str, last: str, domain: str) -> list:
    """Generate candidate local-parts from common name patterns."""
    fname, lname = first.lower().strip(), last.lower().strip()
    if not fname and not lname:
        return []
    seen, out = set(), []
    for p in PATTERNS:
        local = p.format(
            first=fname, last=lname,
            f=fname[0] if fname else "",
            l=lname[0] if lname else "",
        ).strip(".")
        if not local:
            continue
        addr = f"{local}@{domain}"
        if addr not in seen:
            seen.add(addr)
            out.append(addr)
    return out


def get_mx(domain: str):
    """Lowest-preference MX host for the domain, or None."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        ordered = sorted(answers, key=lambda r: r.preference)
        return str(ordered[0].exchange).rstrip(".")
    except Exception:
        return None


def _open_mx_session(mx_host: str, from_addr: str = SMTP_FROM_ADDR, timeout: int = SMTP_TIMEOUT):
    """Open + handshake one SMTP session, ready for RCPT checks. Return the
    smtplib obj, or None if the server can't be reached/handshaken."""
    try:
        s = smtplib.SMTP(mx_host, 25, timeout=timeout)
        s.ehlo("verify.example.com")
        code, _ = s.mail(from_addr)
        if code not in (250, 252):
            s.quit()
            return None
        return s
    except (socket.gaierror, socket.timeout, smtplib.SMTPServerDisconnected, OSError):
        return None


def _rcpt_result(smtp, address: str, timeout: int = SMTP_TIMEOUT):
    """RCPT TO on an open session. True=exists (250), False=hard reject,
    None=inconclusive (soft-fail / grey-list / network drop)."""
    try:
        code, _ = smtp.rcpt(address)
    except (smtplib.SMTPServerDisconnected, socket.timeout, OSError):
        return None
    if code == 250:
        return True
    if code in HARD_REJECT:
        return False
    return None


def smtp_check(email: str, mx_host: str, from_addr: str = SMTP_FROM_ADDR, timeout: int = SMTP_TIMEOUT):
    """Single-address convenience wrapper (one call, one session)."""
    s = _open_mx_session(mx_host, from_addr, timeout)
    if s is None:
        return None
    try:
        return _rcpt_result(s, email, timeout)
    finally:
        try:
            s.quit()
        except Exception:
            pass


def find_email(first: str, last: str, domain: str):
    """Returns (email, confidence) with confidence in {'verified','guessed','none'}.

    Order matters to minimize greylisting/rate-limiting:
    1. Probe a fake address FIRST on a single SMTP session. If it forwards, the
       domain is catch-all -> short-circuit with the best pattern guess ('guessed')
       after exactly one RCPT, never fishing through candidates.
    2. Otherwise walk the candidate patterns on that SAME session; first 200 ->
       'verified'.
    3. Hard reject everywhere -> 'none'.
    """
    if not domain:
        return None, "none"
    mx = get_mx(domain)
    if not mx:
        return None, "none"

    candidates = guess_candidates(first, last, domain)
    session = _open_mx_session(mx)
    if session is None:
        return None, "none"
    try:
        # 1. Probe a guaranteed-bogus address FIRST on this single session.
        #    True -> host accepts anything (catch-all or anti-enumeration).
        probe = f"verify-probe-{id(mx)}@{domain}"
        accepts_anything = _rcpt_result(session, probe) is True

        # 2. Real candidates, same session, no fresh connect per attempt.
        best = None
        for c in candidates:
            if _rcpt_result(session, c) is True:
                best = c
                break

        if best is None:
            return None, "none"
        # 3. Confidence: never 'verified' when the host accepts the probe OR is
        #    a known anti-enumeration provider (its 250s are selective/phantom).
        if accepts_anything or _mx_is_anti_enum(mx):
            return best, "guessed"
        return best, "verified"
    finally:
        try:
            session.quit()
        except Exception:
            pass


def split_name(name: str):
    parts = name.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return name, ""
    return " ".join(parts[:-1]), parts[-1]


def build_linkedin_search_url(company: str, first: str, last: str) -> str:
    """Plain search-engine query for the LinkedIn profile URL. URL-discovery
    only - never logs in or scrapes LinkedIn itself."""
    q = f"{company} {first} {last} linkedin founder".strip()
    return "https://www.google.com/search?q=" + urllib.parse.quote(q)


def gate_status(conf: str, has_email: bool) -> str:
    """Confidence -> status routing at the enrich->draft boundary.

    Pure function (easily unit-tested):
      - no email            -> 'skipped'
      - verified, or guessed with GUESSED_EMAILS_TO_DRAFT on -> 'enriched'
      - guessed (flag off)  -> 'needs_review' (held for manual confirmation)
    """
    if not has_email:
        return "skipped"
    if conf == "guessed" and not GUESSED_EMAILS_TO_DRAFT:
        return "needs_review"
    return "enriched"


def apollo_lookup(domain: str, company: str = "") -> dict | None:
    """Tier 1b: Query Apollo.io REST API by domain.
    Returns dict with {email, contact_name, contact_title, linkedin_url} or None.
    Free tier limit: 60 credits/month."""
    if not APOLLO_API_KEY or not domain:
        return None
    try:
        url = "https://api.apollo.io/api/v1/people/match"
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": APOLLO_API_KEY,
        }
        payload = {
            "api_key": APOLLO_API_KEY,
            "domain": domain,
            "organization_name": company,
            "person_titles": [
                "Founder", "Co-Founder", "CEO", "Chief Executive Officer",
                "CTO", "Head of People", "HR Manager", "VP Engineering"
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                res = json.loads(resp.read().decode("utf-8"))
                person = res.get("person")
                if person and person.get("email"):
                    first = person.get("first_name") or ""
                    last = person.get("last_name") or ""
                    name = f"{first} {last}".strip() or person.get("name")
                    return {
                        "email": person.get("email"),
                        "contact_name": name,
                        "contact_title": person.get("title"),
                        "linkedin_url": person.get("linkedin_url"),
                    }
    except Exception as e:
        print(f"[apollo][api] lookup exception for {domain}: {e}")
    return None


def apollo_session_lookup(domain: str, company: str = "") -> dict | None:
    """Tier 1a: Query Apollo.io via web session cookie.

    Uses app.apollo.io's internal search endpoint — the same one the web UI calls.
    Free account gets up to 10,000 email reveals/year this way (vs 60/month on REST API).

    Required cookies (grab from DevTools -> Application -> Cookies -> app.apollo.io):
      APOLLO_COOKIE      = value of '_leadgenie_session' cookie
      APOLLO_CSRF_TOKEN  = value of 'X-CSRF-TOKEN' cookie
      APOLLO_APP_TOKEN   = value of 'app_token' cookie

    GitHub Actions: store each as a separate GitHub Secret, injected as env vars.
    Cookie lifespan: typically 30-90 days. On 401/expiry, returns None and
    the pipeline automatically falls back to SMTP without crashing.
    """
    if not APOLLO_COOKIE or not domain:
        return None
    try:
        url = "https://app.apollo.io/api/v1/mixed_people/search"
        # Build cookie header with all relevant tokens
        cookie_parts = [f"_leadgenie_session={APOLLO_COOKIE}"]
        if APOLLO_APP_TOKEN:
            cookie_parts.append(f"app_token={APOLLO_APP_TOKEN}")
        cookie_str = "; ".join(cookie_parts)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": cookie_str,
            "X-CSRF-TOKEN": APOLLO_CSRF_TOKEN or "",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://app.apollo.io/people",
            "Origin": "https://app.apollo.io",
        }
        payload = {
            "person_titles": [
                "Founder", "Co-Founder", "CEO", "Chief Executive Officer",
                "CTO", "Head of People", "HR Manager", "VP Engineering",
                "Head of Recruiting", "Talent Acquisition"
            ],
            "organization_domains": [domain],
            "page": 1,
            "per_page": 5,
            "contact_email_status_cd": ["verified"],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 401:
                print("[apollo][session] Cookie expired or invalid. Falling back to SMTP.")
                return None
            if resp.status != 200:
                return None
            res = json.loads(resp.read().decode("utf-8"))
            people = res.get("people") or res.get("contacts") or []
            # Pick the first person with a revealed email
            for person in people:
                email = (person.get("email") or "").strip()
                if not email or email.startswith("email_"):
                    # email_XXXX@domain is an unrevealed placeholder
                    continue
                first = person.get("first_name") or ""
                last = person.get("last_name") or ""
                name = f"{first} {last}".strip() or person.get("name")
                linkedin = (
                    person.get("linkedin_url")
                    or (person.get("contact") or {}).get("linkedin_url")
                )
                print(f"[apollo][session] hit for {domain}: {name} <{email}>")
                return {
                    "email": email,
                    "contact_name": name,
                    "contact_title": person.get("title"),
                    "linkedin_url": linkedin,
                }
        return None
    except Exception as e:
        print(f"[apollo][session] exception for {domain}: {e}")
    return None


def _run_enrich_for(conn, leads) -> int:
    done = 0
    for lead in leads:
        name = (lead.get("contact_name") or "").strip()
        domain = (lead.get("company_domain") or "").strip()
        company = lead.get("company") or ""

        # Tier 0: Public email found on the company's own site -> accept without SMTP.
        if lead.get("email_confidence") == "public" and lead.get("email"):
            update_lead(
                conn, lead["id"],
                linkedin_url=build_linkedin_search_url(company, "", ""),
                status="enriched",
            )
            done += 1
            continue

        if not domain:
            update_lead(conn, lead["id"], status="skipped")
            continue

        apollo_data = None

        # Tier 1a: Apollo.io Web Session (highest free yield - 10,000 reveals/year)
        if APOLLO_COOKIE:
            apollo_data = apollo_session_lookup(domain, company)
            # Polite throttle - avoid hammering Apollo from CI
            time.sleep(random.uniform(2.0, 4.0))

        # Tier 1b: Apollo.io REST API (60 credits/month on free tier)
        if not apollo_data and APOLLO_API_KEY:
            apollo_data = apollo_lookup(domain, company)

        # If Apollo (either tier) returned a contact, save and move on.
        if apollo_data and apollo_data.get("email"):
            fields = {
                "email": apollo_data["email"],
                "email_confidence": "verified",
                "status": "enriched",
            }
            if apollo_data.get("contact_name"):
                fields["contact_name"] = apollo_data["contact_name"]
            if apollo_data.get("contact_title"):
                fields["contact_title"] = apollo_data["contact_title"]
            fields["linkedin_url"] = (
                apollo_data.get("linkedin_url")
                or build_linkedin_search_url(company, apollo_data.get("contact_name") or "", "")
            )
            update_lead(conn, lead["id"], **fields)
            done += 1
            continue

        # Tier 2: Personal SMTP - pattern-guess {first}.{last}@domain from founder name.
        email = None
        conf = "none"
        if name:
            first, last = split_name(name)
            email, conf = find_email(first, last, domain)

        # Tier 3: Generic SMTP fallback (hello@, founders@, hr@, careers@, team@).
        if not email:
            email, conf = _find_generic_email(domain)

        linkedin_url = build_linkedin_search_url(company, "", "")
        update_lead(
            conn,
            lead["id"],
            email=email,
            email_confidence=conf,
            linkedin_url=linkedin_url,
            status=gate_status(conf, bool(email)),
        )
        done += 1
    return done


# Mailboxes commonly present and public-facing on company sites. We SMTP-verify
# these when no personal contact is known - a real, free lead-generation path.
GENERIC_MAILBOXES = ["hello", "team", "hr", "careers", "jobs", "info", "contact", "founders", "hi"]


def _find_generic_email(domain: str):
    """Probe common public mailboxes via SMTP. Returns (email, confidence)."""
    mx = get_mx(domain)
    if not mx:
        return None, "none"
    session = _open_mx_session(mx)
    if session is None:
        return None, "none"
    try:
        probe = f"verify-probe-{id(mx)}@{domain}"
        accepts_anything = _rcpt_result(session, probe) is True
        for box in GENERIC_MAILBOXES:
            addr = f"{box}@{domain}"
            if _rcpt_result(session, addr) is True:
                conf = "guessed" if (accepts_anything or _mx_is_anti_enum(mx)) else "verified"
                return addr, conf
        return None, "none"
    finally:
        try:
            session.quit()
        except Exception:
            pass


def enrich_qualified(limit: int = 25) -> int:
    conn = get_conn()
    leads = get_leads_by_status(conn, "qualified", limit=limit)
    done = _run_enrich_for(conn, leads)
    print(f"[enrich] attempted {done} leads.")
    return done


def promote_to_draft(lead_id: int) -> None:
    """Manual-review helper: after confirming a 'guessed' address by hand, promote
    the lead into the draft queue. Usage: python enrich_email.py --promote <id>."""
    conn = get_conn()
    update_lead(conn, lead_id, status="enriched")
    print(f"[enrich] promoted lead {lead_id} to enriched (ready for drafting).")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--promote":
        promote_to_draft(int(sys.argv[2]))
    else:
        enrich_qualified()