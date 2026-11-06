"""Google Sheets push - mirror pipeline exports into a spreadsheet.

Uses the same Google OAuth pattern as send_gmail.py (credentials.json ->
sheets_token.json), but with spreadsheet scope. Reads the CSVs written by
export_results.run_exports() and puts each into its own tab.

Usage:
    python export_results.py    # 1) write companies/contacts/emails/combined CSVs
    python sheets_push.py       # 2) create/reuse Spreadsheet + fill tabs atomically
"""
import os
import csv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from export_results import EXPORTS_DIR, run_exports

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TOKEN_FILE = "sheets_token.json"
CREDENTIALS_FILE = "credentials.json"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SPREADSHEET_TITLE = "Startup Pipeline"
# tab name -> relative CSV filename inside EXPORTS_DIR
TAB_SOURCES = [
    ("Companies", "companies.csv"),
    ("Contacts", "contacts.csv"),
    ("Emails", "pipeline_export.csv"),
]


def get_service():
    creds = None
    token_path = os.path.join(PROJECT_ROOT, TOKEN_FILE)
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_path = os.path.join(PROJECT_ROOT, CREDENTIALS_FILE)
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("sheets", "v4", credentials=creds)


def _csv_values(name: str) -> list[list[str]]:
    path = os.path.join(EXPORTS_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} missing - run python export_results.py first")
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def _ensure_tabs(svc, sid: str):
    current = svc.spreadsheets().get(spreadsheetId=sid).execute().get("sheets", [])
    have = {s["properties"]["title"] for s in current}
    for tab, _ in TAB_SOURCES:
        if tab not in have:
            svc.spreadsheets().batchUpdate(
                spreadsheetId=sid,
                body={"requests": [
                    {"addSheet": {"properties": {"title": tab}}}
                ]},
            ).execute()


def _column_letters(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def push(service, spreadsheet_id: str | None = None) -> str:
    if spreadsheet_id:
        sid = spreadsheet_id
    else:
        info = service.spreadsheets().create(
            body={"properties": {"title": SPREADSHEET_TITLE}}
        ).execute()
        sid = info["spreadsheetId"]

    _ensure_tabs(service, sid)
    for tab, csvname in TAB_SOURCES:
        values = _csv_values(csvname)
        if not values:
            continue
        ncols, nrows = len(values[0]), len(values)
        # blank the tab first so deleted rows don't linger
        last_col = _column_letters(ncols)
        rng = f"{tab}!A1:{last_col}{nrows + 1}" if nrows else f"{tab}!A1"
        service.spreadsheets().values().clear(
            spreadsheetId=sid, range=rng, body={}
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=sid,
            range=f"{tab}!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
        print(f"[sheets] filled {tab}: {nrows} rows x {ncols} cols")
    return sid


if __name__ == "__main__":
    run_exports()
    svc = get_service()
    sid = push(svc)
    print(f"\nOpen: https://docs.google.com/spreadsheets/d/{sid}")