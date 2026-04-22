import json
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path


class AuthManager:
    """
    Manages automatic token refresh for the Upwork scraper.

    Token state (last_refresh timestamp) is persisted to disk in
    auth/token_state.json so restarts do NOT trigger unnecessary
    refreshes if the tokens are still valid.

    Refresh only happens when:
    1. No token_state.json exists (first ever run)
    2. 11+ hours have passed since the last refresh
    3. A 403/401 error is detected in the scraper loop
    """

    TOKEN_LIFETIME_HOURS = 11
    CHECK_INTERVAL_SECONDS = 1800
    SCRIPT_PATH = Path(__file__).parent / "fetch_cookies.py"
    STATE_PATH  = Path(__file__).parent / "token_state.json"
    COOKIES_PATH = Path(__file__).parent / "saved_cookies.json"

    def __init__(self, scraper):
        self.scraper = scraper
        self.last_refresh: datetime | None = self._load_state()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_refresh(self) -> bool:
        """Returns True only if no refresh has occurred or 11h have passed."""
        if self.last_refresh is None:
            return True
        return datetime.now() - self.last_refresh >= timedelta(hours=self.TOKEN_LIFETIME_HOURS)

    def refresh(self):
        """
        Run fetch_cookies.py as a subprocess, parse JSON output,
        inject fresh credentials into the scraper, save timestamp.
        """
        with self._lock:
            try:
                print("[AUTH] Starting token refresh (subprocess mode)...")
                cookies, auth_token = self._extract_credentials()

                if cookies:
                    self.scraper.update_credentials(cookies, auth_token)
                    self.last_refresh = datetime.now()
                    self._save_state(cookies, auth_token)
                    print(f"[AUTH] Tokens refreshed successfully at "
                          f"{self.last_refresh.strftime('%H:%M:%S')} — "
                          f"{len(cookies)} cookies extracted.")
                else:
                    print("[AUTH] WARNING: No cookies extracted. Keeping existing credentials.")

            except Exception as e:
                print(f"[AUTH] ERROR during token refresh: {e}")
                print("[AUTH] Will retry at next check interval.")

    def start_background_refresh(self):
        """
        Starts a daemon thread that checks every 30 minutes
        whether a refresh is needed and refreshes automatically.
        """
        # Show time until next refresh at startup
        if self.last_refresh:
            elapsed = datetime.now() - self.last_refresh
            remaining = timedelta(hours=self.TOKEN_LIFETIME_HOURS) - elapsed
            hours, rem = divmod(int(remaining.total_seconds()), 3600)
            minutes = rem // 60
            print(f"[AUTH] Next refresh in {hours}h {minutes}m. Background thread started.")
        else:
            print("[AUTH] Background refresh thread started.")

        def _loop():
            while True:
                if self.should_refresh():
                    self.refresh()
                threading.Event().wait(timeout=self.CHECK_INTERVAL_SECONDS)

        self._thread = threading.Thread(
            target=_loop, daemon=True, name="AuthRefreshThread"
        )
        self._thread.start()

    # ------------------------------------------------------------------
    # Private: state persistence
    # ------------------------------------------------------------------

    def _save_state(self, cookies: dict, auth_token: str | None):
        """Saves refresh timestamp AND cookies to disk."""
        try:
            self.STATE_PATH.write_text(
                json.dumps({"last_refresh": self.last_refresh.isoformat()})
            )
            self.COOKIES_PATH.write_text(
                json.dumps({"cookies": cookies, "auth_token": auth_token})
            )
        except Exception as e:
            print(f"[AUTH] Could not save token state: {e}")

    def _load_state(self) -> datetime | None:
        """Loads timestamp from disk and injects saved cookies into scraper."""
        try:
            if self.STATE_PATH.exists():
                data = json.loads(self.STATE_PATH.read_text())
                ts = datetime.fromisoformat(data["last_refresh"])
                elapsed = datetime.now() - ts
                hours = int(elapsed.total_seconds() // 3600)

                # Load saved cookies back into scraper
                if self.COOKIES_PATH.exists():
                    cdata = json.loads(self.COOKIES_PATH.read_text())
                    self.scraper.update_credentials(
                        cdata.get("cookies", {}),
                        cdata.get("auth_token")
                    )
                    print(f"[AUTH] Loaded saved credentials from disk ({hours}h old).")
                return ts
        except Exception as e:
            print(f"[AUTH] Could not load token state: {e}")
        return None

    # ------------------------------------------------------------------
    # Private: subprocess execution
    # ------------------------------------------------------------------

    def _extract_credentials(self) -> tuple[dict, str | None]:
        """
        Runs auth/fetch_cookies.py in a separate Python process.
        Selenium's own asyncio loop runs in that isolated process.
        """
        result = subprocess.run(
            [sys.executable, str(self.SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=90,
        )

        stdout = result.stdout.strip()
        if not stdout:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"fetch_cookies.py produced no output. "
                f"Exit: {result.returncode}. Err: {stderr[:200]}"
            )

        data = json.loads(stdout)
        if "error" in data:
            raise RuntimeError(f"fetch_cookies.py: {data['error']}")

        return data.get("cookies", {}), data.get("auth_token")
