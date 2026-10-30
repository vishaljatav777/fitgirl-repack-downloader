import json
import time
import threading
from pathlib import Path
from typing import List, Optional, Callable
from playwright.sync_api import sync_playwright
from config import get_browser_path, USER_AGENT, BASE_DIR
from scraper import DownloadItem

CACHE_FILE = BASE_DIR / "resolved_cache.json"

class FuckingFastResolver:
    def __init__(
        self,
        headless: bool = True,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.browser_path = get_browser_path()
        if not self.browser_path:
            raise RuntimeError(
                "No compatible browser (Brave / Chrome / Edge) found on system."
            )
        self.headless = headless
        self.log_callback = log_callback
        self.cache = self._load_cache()
        self._stop_event = threading.Event()

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def stop(self):
        self._stop_event.set()

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    now = time.time()
                    return {
                        k: v for k, v in data.items()
                        if (now - v.get("timestamp", 0)) < 72000
                    }
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass

    def resolve_single_page(self, page, share_url: str) -> Optional[str]:
        if share_url in self.cache:
            return self.cache[share_url]["direct_url"]

        if self.is_stopped():
            return None

        direct_url = None

        def on_response(res):
            nonlocal direct_url
            hx = res.headers.get("hx-redirect")
            if hx and "dl.fuckingfast.co" in hx:
                direct_url = hx

        def on_download(download):
            nonlocal direct_url
            if download.url and "dl.fuckingfast.co" in download.url:
                direct_url = download.url
                download.cancel()

        page.on("response", on_response)
        page.on("download", on_download)

        try:
            page.goto(share_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)

            if self.is_stopped():
                return None

            btn = page.wait_for_selector(
                "a.link-button, a:has-text('DOWNLOAD'), button:has-text('DOWNLOAD')",
                timeout=15000
            )
            if not btn:
                return None

            btn.click()
            page.wait_for_timeout(2000)

            if not direct_url:
                try:
                    btn.click()
                except Exception:
                    pass

                for _ in range(15):
                    if direct_url or self.is_stopped():
                        break
                    page.wait_for_timeout(500)

            if direct_url:
                self.cache[share_url] = {
                    "direct_url": direct_url,
                    "timestamp": time.time()
                }
                self._save_cache()

            return direct_url
        except Exception as e:
            return None
        finally:
            page.remove_listener("response", on_response)
            page.remove_listener("download", on_download)

    def resolve_batch(
        self,
        items: List[DownloadItem],
        progress_callback: Optional[Callable[[int, int, DownloadItem], None]] = None
    ) -> List[DownloadItem]:
        self._stop_event.clear()
        total = len(items)
        resolved_count = 0

        uncached_indices = []
        for idx, item in enumerate(items):
            if item.share_url in self.cache:
                item.direct_url = self.cache[item.share_url]["direct_url"]
                resolved_count += 1
                if progress_callback:
                    progress_callback(resolved_count, total, item)
            else:
                uncached_indices.append(idx)

        if not uncached_indices or self.is_stopped():
            return items

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=self.browser_path,
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ],
                ignore_default_args=["--enable-automation"]
            )
            context = browser.new_context(
                accept_downloads=True,
                user_agent=USER_AGENT
            )
            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            for idx in uncached_indices:
                if self.is_stopped():
                    break
                item = items[idx]
                direct = self.resolve_single_page(page, item.share_url)
                if direct:
                    item.direct_url = direct
                resolved_count += 1
                if progress_callback:
                    progress_callback(resolved_count, total, item)

            browser.close()

        return items
