"""Stage 5 - Gmail Draft & Delivery Engine (OAuth2, RFC-compliant MIME).

Idempotent status lifecycle:
    drafted        -> send_gmail.py -> draft_created   (Gmail Draft ID stored)
    draft_created  -> send_gmail.py -> sent            (when delivered / AUTO_SEND=True)

Uses Python's standard `email.message.EmailMessage` with utf-8 charset and
explicit RFC 2822 headers (To, Subject, Content-Type: text/html) so UTF-8
content and MIME headers survive encoding round-trips.

Authentication uses the token.json written by `python auth_gmail.py`; the
script never attempts an interactive browser flow in a background context.
"""
import os
from base64 import urlsafe_b64encode
from email.message import EmailMessage
from email.utils import formataddr

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import AUTO_SEND
from db import get_conn, get_leads_by_status, update_lead

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "credentials.json")


def get_service():
    """Load/refresh token.json. Never starts an interactive OAuth flow."""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"token.json not found at {TOKEN_FILE}. Run `python auth_gmail.py` "
            "once to authorize Gmail access."
        )
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise PermissionError(
                "Gmail credentials are invalid and have no refresh token. "
                "Re-run `python auth_gmail.py`."
            )
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def build_message(to_email: str, subject: str, body_html: str) -> EmailMessage:
    """Construct an RFC 2822-compliant UTF-8 HTML message via EmailMessage."""
    msg = EmailMessage()
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Content-Type"] = "text/html; charset=utf-8"
    msg.set_content(body_html, subtype="html", charset="utf-8")
    return msg


def encode_raw(msg: EmailMessage) -> str:
    """Base64url-encode the full RFC 2822 message for the Gmail API."""
    return urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def create_draft(service, to_email: str, subject: str, body_html: str) -> dict:
    raw = encode_raw(build_message(to_email, subject, body_html))
    return (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )


def send_message(service, to_email: str, subject: str, body_html: str) -> dict:
    raw = encode_raw(build_message(to_email, subject, body_html))
    return (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )


def _subject(lead: dict) -> str:
    base = "Re: {role} role at {company}".format(
        role=(lead.get("role_title") or "Engineering"),
        company=lead["company"],
    )
    return base[:120]


def _load_body_html(company: str) -> str | None:
    """Load the locally-saved draft body (drafted state) as HTML."""
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in company)
    path = os.path.join(PROJECT_ROOT, "drafts", f"{safe}.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        lines = f.readlines()
    body_start = 0
    for i, line in enumerate(lines):
        if not line.startswith(("To:", "Company:", "Role:")) and line.strip():
            body_start = i
            break
    plain = "".join(lines[body_start:]).strip()
    html = "<html><body><pre>{body}</pre></body></html>".format(
        body=plain.replace("\n", "<br>")
    )
    return html


def stage_send(limit: int = 25) -> int:
    """Process leads in `drafted` (create Gmail draft) and, when AUTO_SEND,
    advance `draft_created` leads to `sent`. Idempotent by design."""
    conn = get_conn()
    service = None  # lazily built on first lead that needs an API call
    done = 0

    def _svc():
        nonlocal service
        if service is None:
            service = get_service()
        return service

    # Phase 1: drafted -> draft_created
    drafted = get_leads_by_status(conn, "drafted", limit=limit)
    for lead in drafted:
        to_email = lead.get("email")
        body_html = _load_body_html(lead["company"])
        if not to_email:
            update_lead(conn, lead["id"], status="skipped")
            continue
        if not body_html:
            print(f"[send] no draft file for {lead['company']}; skipping.")
            update_lead(conn, lead["id"], status="skipped")
            continue
        try:
            if AUTO_SEND:
                send_message(_svc(), to_email, _subject(lead), body_html)
                update_lead(conn, lead["id"], status="sent")
            else:
                result = create_draft(_svc(), to_email, _subject(lead), body_html)
                update_lead(
                    conn,
                    lead["id"],
                    gmail_draft_id=result.get("id"),
                    status="draft_created",
                )
            done += 1
        except HttpError as e:
            print(f"[send] failed to create draft for {lead['company']}: {e}")

    # Phase 2 (AUTO_SEND only): draft_created -> sent
    if AUTO_SEND:
        created = get_leads_by_status(conn, "draft_created", limit=limit)
        for lead in created:
            draft_id = lead.get("gmail_draft_id")
            if not draft_id:
                update_lead(conn, lead["id"], status="drafted")
                continue
            body_html = _load_body_html(lead["company"])
            to_email = lead.get("email")
            if not to_email or not body_html:
                continue
            try:
                _svc().users().drafts().send(
                    userId="me", body={"id": draft_id}
                ).execute()
                update_lead(conn, lead["id"], status="sent")
                done += 1
            except HttpError as e:
                print(f"[send] failed to send draft {draft_id}: {e}")

    print(f"[send] processed {done} emails ({'sent' if AUTO_SEND else 'drafted'}).")
    return done


if __name__ == "__main__":
    stage_send()