"""Standalone Gmail OAuth bootstrapper.

Run once interactively to authorize Google OAuth and write `token.json`:

    python auth_gmail.py

The resulting `token.json` is consumed by send_gmail.py (git-ignored).
Only the requested scopes are granted; no extra permissions.
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "credentials.json")


def main() -> None:
    if not os.path.exists(CREDENTIALS_FILE):
        raise SystemExit(
            f"credentials.json not found at {CREDENTIALS_FILE}.\n"
            "Download it from Google Cloud Console -> APIs & Services -> "
            "Credentials -> OAuth 2.0 Client IDs (Desktop app)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print(f"\n[auth] token saved to {TOKEN_FILE}")
    print("[auth] Gmail access granted. You can now run: python send_gmail.py")


if __name__ == "__main__":
    main()