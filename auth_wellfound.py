"""Standalone Wellfound session bootstrapper.

Run once interactively to log in and persist the Playwright storage state to
`wellfound_session.json` (git-ignored) for reuse by agents/browser_agent.py:

    python auth_wellfound.py

A real headed Chrome window opens; complete the login by hand (or via your
Google/GitHub SSO). On success the session cookie storage is saved.
"""
import os

from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(
    PROJECT_ROOT, os.getenv("WELLFOUND_SESSION_FILE", "wellfound_session.json")
)
LOGIN_URL = "https://wellfound.com/login"
PROFILE_URL = "https://wellfound.com/account/profile"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        print("[auth] Opening Wellfound login... complete the login in the browser.")
        page.goto(LOGIN_URL, timeout=120000, wait_until="domcontentloaded")
        try:
            page.wait_for_url("**/account/**", timeout=180000)
        except Exception:
            print("[auth] Login flow not completed within 3 minutes; continuing anyway.")
        context.storage_state(path=SESSION_FILE)
        print(f"[auth] Session saved to {SESSION_FILE}")
        browser.close()


if __name__ == "__main__":
    main()