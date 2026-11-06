"""Export the pipeline's leads into human-usable records.

Writes four artifacts after each pipeline run:
  1. exports/companies.csv        - every company found  (name, brief, status, funding, stage, region, role)
  2. exports/contacts.csv         - every enriched contact (company, contact name/title, email, confidence,
                                    LinkedIn company/profile, X/Twitter, fit score)
  3. exports/emails/<Company>.txt - one personalized outreach email per drafted company
  4. exports/pipeline_export.csv  - ALL of the above line-by-line in columns, one row per company

All files are CSV/UTF-8 and open cleanly in Excel / Google Sheets.
"""
import os
import csv
import sqlite3

from config import DB_PATH
from db import get_conn, update_lead

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")


def _conn() -> sqlite3.Connection:
    return get_conn()


def _brief(lead: dict) -> str:
    """Best-effort 1-2 line company summary from posting_text/fit_reason."""
    if lead.get("fit_reason"):
        return lead["fit_reason"]
    pt = (lead.get("posting_text") or "").strip()
    return pt[:180].replace("\n", " ") if pt else ""


def export_companies(conn) -> str:
    rows = conn.execute(
        """SELECT company, company_domain, funding_stage, funding_info, region,
                  role_title, status, fit_score, fit_reason, posting_text
           FROM leads ORDER BY created_at"""
    ).fetchall()
    path = os.path.join(EXPORTS_DIR, "companies.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Company", "Domain", "Funding Stage", "Funding", "Region",
                    "Role", "Status", "Score", "Brief"])
        for r in rows:
            lead = dict(zip(("company", "domain", "funding_stage", "funding", "region",
                           "role", "status", "score", "posting"), r))
            w.writerow([
                lead["company"], lead["domain"], lead["funding_stage"], lead["funding"],
                lead["region"], lead["role"] or "", lead["status"], lead["score"],
                _brief(lead),
            ])
    return path


def export_contacts(conn) -> str:
    rows = conn.execute(
        "SELECT company, company_domain, contact_name, contact_title, email, "
        "email_confidence, linkedin_company_url, linkedin_contact_url, x_url, "
        "fit_score, status FROM leads"
    ).fetchall()
    path = os.path.join(EXPORTS_DIR, "contacts.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Company", "Domain", "Contact", "Title", "Email", "Confidence",
                    "LinkedIn Cmp", "LinkedIn Per", "X/Twitter", "Fit", "Status"])
        for lead in [dict(zip(("company", "domain", "name", "title", "email", "conf",
                              "lnkd_c", "lnkd_p", "x", "fit", "status"), r)) for r in rows]:
            w.writerow([lead["company"], lead["domain"], lead["name"], lead["title"],
                        lead["email"], lead["conf"], lead["lnkd_c"], lead["lnkd_p"],
                        lead["x"], lead["fit"], lead["status"]])
    return path


def _read_draft(company: str) -> str | None:
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in company)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drafts", f"{safe}.txt")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig") as f:
        lines = f.readlines()
    body_start = 0
    for i, line in enumerate(lines):
        if not line.startswith(("To:", "Company:", "Role:")) and line.strip():
            body_start = i
            break
    return "".join(lines[body_start:]).strip()


def export_emails(conn) -> list[str]:
    rows = conn.execute(
        "SELECT company, email, gmail_draft_id, status FROM leads "
        "WHERE status IN ('drafted','sent') OR (email IS NOT NULL AND email != '')"
    ).fetchall()
    paths = []
    for r in rows:
        company, email, draft_id, status = r
        body = _read_draft(company)
        if not body:
            continue
        safe = "".join(c if c.isalnum() or c in " .-_" else "_" for c in company)
        path = os.path.join(EXPORTS_DIR, "emails", f"{safe}.txt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(f"# {company}\n")
            f.write(f"To: {email or ''}\n")
            f.write(f"Status: {status}\n\n")
            f.write(body)
        paths.append(path)
    return paths


def export_combined(conn) -> str:
    """One CSV with EVERYTHING per company, line by line, in columns."""
    rows = conn.execute("SELECT * FROM leads").fetchall()
    colnames = [d[0] for d in conn.execute("SELECT * FROM leads").description]
    path = os.path.join(EXPORTS_DIR, "pipeline_export.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(colnames)
        for r in rows:
            w.writerow([("" if v is None else str(v)) for v in r])
    return path


def run_exports() -> dict:
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(EXPORTS_DIR, "emails"), exist_ok=True)
    conn = _conn()
    results = {
        "companies": export_companies(conn),
        "contacts": export_contacts(conn),
        "emails": export_emails(conn),
        "combined": export_combined(conn),
    }
    print("[export] wrote companies/contacts/emails/combined to exports/")
    return results


if __name__ == "__main__":
    print(run_exports())