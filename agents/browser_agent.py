"""Agent 7 - Browser Automation Agent (Wellfound Auto-Apply).

Handles authenticated portal actions using a persistent Playwright storage
state (`wellfound_session.json`) produced by `python auth_wellfound.py`.

Action modes:
  - AUTO_APPLY=false (Default / Copilot Mode): fills the apply modal with the
    tailored note and STOPS for human review — never submits.
  - AUTO_APPLY=true  (Autonomous Mode): types the note with human typing
    jitter (40-120ms/key), adds randomized 5-15s delays, and submits.
"""
from __future__ import annotations

import json
import os
import random
import time
from typing import Optional

from config import (
    AUTO_APPLY,
    BROWSER_HEADLESS,
    WELLFOUND_PROFILE_URL,
    WELLFOUND_SESSION_FILE,
)
from logger import log

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _session_path() -> str:
    return os.path.join(PROJECT_ROOT, WELLFOUND_SESSION_FILE)


def _typing_jitter(page, selector: str, text: str) -> None:
    """Type text with humanized 40-120ms per-key cadence."""
    for ch in text:
        page.keyboard.type(ch)
        time.sleep(random.uniform(0.04, 0.12))


class BrowserAgent:
    """Playwright automation for Wellfound with humanized cadence & guardrails."""

    name = "browser"

    def __init__(self, auto_apply: bool = AUTO_APPLY, headless: bool = BROWSER_HEADLESS):
        self.auto_apply = auto_apply
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None

    @property
    def session_ready(self) -> bool:
        return os.path.exists(_session_path())

    def _launch(self):
        if self._context is not None:
            return self._context
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        kwargs = {}
        if self.session_ready:
            kwargs["storage_state"] = _session_path()
        self._context = self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            **kwargs,
        )
        return self._context

    def close(self) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self._context = self._browser = self._playwright = None

    def open_job(self, job_url: str) -> None:
        """Open a Wellfound job listing; raises if no session is stored."""
        if not self.session_ready:
            raise RuntimeError(
                "No Wellfound session found. Run `python auth_wellfound.py` first."
            )
        ctx = self._launch()
        page = ctx.new_page()
        log.info(f"[browser] opening job {job_url}")
        page.goto(job_url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(random.uniform(3.0, 6.0))
        return page

    def apply(self, job_url: str, note: str) -> dict:
        """Drive the Wellfound apply flow for a single job.

        Copilot mode (AUTO_APPLY=false): fills the modal note and stops,
        leaving the user to review & submit with one click.
        """
        if not self.session_ready:
            raise RuntimeError(
                "No Wellfound session found. Run `python auth_wellfound.py` first."
            )
        page = self.open_job(job_url)
        submitted = False
        try:
            # Click the primary apply / "Easy Apply" CTA.
            for sel in ("button:has-text('Apply')", "a:has-text('Apply')"):
                btn = page.locator(sel).first
                if btn.is_visible():
                    btn.click()
                    break
            time.sleep(random.uniform(2.0, 4.0))

            # Fill the message/cover note textarea if present.
            note_area = page.locator("textarea, [contenteditable='true']").first
            if note_area.is_visible():
                note_area.click()
                _typing_jitter(page, note_area, note[:1200])

            if self.auto_apply:
                time.sleep(random.uniform(5.0, 15.0))  # humanized pause
                submit = page.locator("button:has-text('Submit'), button:has-text('Apply')").first
                if submit.is_visible():
                    submit.click()
                    submitted = True
                time.sleep(random.uniform(2.0, 5.0))
            else:
                log.info("[browser] copilot mode: application prefilled, awaiting human review")
        finally:
            page.close()
        return {"job_url": job_url, "submitted": submitted, "mode": "auto" if self.auto_apply else "copilot"}

    def __repr__(self) -> str:
        return f"<BrowserAgent auto_apply={self.auto_apply}>"