import re
from dataclasses import dataclass, field
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import TIMEOUT, USER_AGENT
from exceptions import ScraperError

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    cffi_requests = None  # type: ignore[assignment]
    HAS_CURL_CFFI = False

BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


@dataclass
class DownloadItem:
    filename: str
    share_url: str
    is_optional: bool = False
    is_selective: bool = False
    direct_url: str | None = None
    size_bytes: int = 0
    error_message: str | None = None

@dataclass
class GameRepack:
    title: str
    page_url: str
    parts: list[DownloadItem] = field(default_factory=list)
    optionals: list[DownloadItem] = field(default_factory=list)

class FitGirlScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)

    def _fetch_html(self, url: str) -> str:
        """
        Fetches HTML from a remote URL with TLS impersonation (curl_cffi) if available,
        falling back to standard requests.Session.
        Raises ScraperError on network failures, SSL handshake drops, or HTTP errors.
        """
        last_error: Exception | None = None

        # 1. Try curl_cffi with chrome TLS fingerprint impersonation if available
        if HAS_CURL_CFFI and cffi_requests is not None:
            try:
                cffi_resp = cffi_requests.get(
                    url,
                    impersonate="chrome",
                    headers=BROWSER_HEADERS,
                    timeout=TIMEOUT,
                )
                if cffi_resp.status_code == 200:
                    return cffi_resp.text
                if cffi_resp.status_code == 403:
                    raise ScraperError(
                        f"Access blocked by fitgirl-repacks.site (HTTP {cffi_resp.status_code}).",
                        details=(
                            "Cloudflare or site policy prevented automated access. "
                            "Please open the game page in your browser and paste the repack URL directly."
                        ),
                    )
                cffi_resp.raise_for_status()
                return cffi_resp.text
            except ScraperError:
                raise
            except Exception as e:
                last_error = e

        # 2. Fallback to standard requests.Session
        try:
            req_resp = self.session.get(url, headers=BROWSER_HEADERS, timeout=TIMEOUT)
            if req_resp.status_code == 403:
                raise ScraperError(
                    f"Access blocked by fitgirl-repacks.site (HTTP {req_resp.status_code}).",
                    details=(
                        "Cloudflare or site security policy rejected the automated request. "
                        "Please open the game page in your web browser and paste the URL directly."
                    ),
                )
            req_resp.raise_for_status()
            return req_resp.text
        except ScraperError:
            raise
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            if "SSL" in err_msg or "EOF" in err_msg:
                details = (
                    "SSL/TLS handshake was terminated by the host or your ISP. "
                    "This often happens when Cloudflare detects automated tools or an ISP blocks the domain. "
                    "You can search directly in your browser and paste the repack URL."
                )
            elif "Max retries exceeded" in err_msg or "Failed to establish a new connection" in err_msg:
                details = (
                    "Failed to establish connection to fitgirl-repacks.site. "
                    "Please check your network connection or DNS settings."
                )
            else:
                details = "Could not fetch web page. Try searching directly in your browser."

            raise ScraperError(
                f"Failed to fetch {url}",
                details=details,
            ) from (e or last_error)

    def scrape_url(self, url: str) -> GameRepack:
        """Scrapes a FitGirl repack page and extracts all FuckingFast links."""
        url = url.strip()
        if not url:
            raise ValueError("URL cannot be empty.")

        # Check if url points to a local text manifest of URLs
        clean_path_str = url.replace("file://", "").strip().strip('"').strip("'")
        local_txt = Path(clean_path_str)
        if local_txt.is_file() and local_txt.suffix.lower() == ".txt":
            try:
                raw_lines = local_txt.read_text(encoding="utf-8").splitlines()
                lines = [line_entry.strip() for line_entry in raw_lines if line_entry.strip() and not line_entry.strip().startswith("#")]
                if lines:
                    manifest_parts: list[DownloadItem] = []
                    for idx, line in enumerate(lines, 1):
                        part_no_hash = line.split("#")[0]
                        part_path = part_no_hash.split("?")[0]
                        fn = line.split("#")[-1] if "#" in line else part_path.split("/")[-1] or f"part{idx:02d}.bin"
                        is_direct_part = any(part_path.lower().endswith(ext) for ext in (
                            ".rar", ".7z", ".zip", ".bin", ".iso", ".exe", ".tar", ".gz",
                            ".part1.rar", ".part01.rar", ".001", ".pkg", ".msi"
                        )) or "dl.fuckingfast.co" in line
                        manifest_parts.append(DownloadItem(
                            filename=fn,
                            share_url=line,
                            direct_url=line if is_direct_part else None
                        ))
                    return GameRepack(
                        title=f"Batch Manifest ({local_txt.stem})",
                        page_url=str(local_txt),
                        parts=manifest_parts,
                        optionals=[]
                    )
            except Exception:
                pass

        # Ensure scheme
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        # Direct file or archive URL from authorized sources (in path or hash fragment)
        archive_extensions = (
            ".rar", ".7z", ".zip", ".bin", ".iso", ".exe", ".tar", ".gz",
            ".part1.rar", ".part01.rar", ".001", ".pkg", ".msi"
        )
        url_without_hash = url.split("#")[0]
        url_path = url_without_hash.split("?")[0]
        fragment = url.split("#")[1] if "#" in url else ""

        is_direct = (
            any(url_path.lower().endswith(ext) for ext in archive_extensions) or
            any(fragment.lower().endswith(ext) for ext in archive_extensions) or
            "dl.fuckingfast.co" in url_without_hash
        )
        if is_direct:
            if fragment:
                base_url = url_without_hash
                filename = fragment
            else:
                base_url = url
                filename = url_path.split("/")[-1] or "download.bin"

            item = DownloadItem(
                filename=filename,
                share_url=base_url,
                direct_url=base_url  # Direct authorized download URL
            )
            return GameRepack(
                title=f"Authorized Download ({filename})",
                page_url=url,
                parts=[item],
                optionals=[]
            )

        # If user pasted a direct fuckingfast link instead of a repack page
        if "fuckingfast.co" in url:
            filename = ""
            if "#" in url:
                base_url, fragment = url.split("#", 1)
                filename = fragment
            else:
                base_url = url
                filename = base_url.split("/")[-1] or "download.rar"
            item = DownloadItem(filename=filename, share_url=base_url)
            return GameRepack(
                title=f"Direct Link ({filename})",
                page_url=url,
                parts=[item],
                optionals=[]
            )

        html_text = self._fetch_html(url)
        soup = BeautifulSoup(html_text, "html.parser")

        # Extract title
        title_tag = soup.find("h1", class_="entry-title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown Game Repack"

        # Find all fuckingfast links
        ff_anchors = [
            a for a in soup.find_all("a", href=True)
            if "fuckingfast.co" in a["href"]
        ]

        parts: list[DownloadItem] = []
        optionals: list[DownloadItem] = []
        seen_urls = set()

        for a in ff_anchors:
            href = str(a.get("href", "")).strip()
            text = a.get_text(strip=True)

            # Determine filename from text or URL hash fragment
            filename = ""
            if "#" in href:
                base_url, fragment = href.split("#", 1)
                filename = fragment
            else:
                base_url = href

            if not filename:
                filename = text or base_url.split("/")[-1]

            clean_share_url = base_url
            if clean_share_url in seen_urls:
                continue
            seen_urls.add(clean_share_url)

            is_optional = "optional" in filename.lower()
            is_selective = "selective" in filename.lower()

            item = DownloadItem(
                filename=filename,
                share_url=clean_share_url,
                is_optional=is_optional,
                is_selective=is_selective
            )

            if is_optional or is_selective:
                optionals.append(item)
            else:
                parts.append(item)

        if not parts and not optionals:
            raise ValueError(
                "No FuckingFast links found on this page.\n\n"
                "Please verify this is an official FitGirl repack page (fitgirl-repacks.site) "
                "that includes 'Filehoster: FuckingFast' mirrors."
            )

        # Sort parts naturally (part01, part02, etc.)
        def natural_sort_key(item: DownloadItem):
            numbers = re.findall(r"\d+", item.filename)
            return [int(n) for n in numbers] if numbers else [item.filename]

        parts.sort(key=natural_sort_key)
        optionals.sort(key=lambda x: x.filename)

        return GameRepack(
            title=title,
            page_url=url,
            parts=parts,
            optionals=optionals
        )

    def search_game(self, query: str) -> list[dict[str, str]]:
        """Searches FitGirl site and returns matching results (title and url)."""
        search_url = f"https://fitgirl-repacks.site/?s={requests.utils.quote(query)}"
        html_text = self._fetch_html(search_url)
        soup = BeautifulSoup(html_text, "html.parser")
        results = []

        articles = soup.find_all("article")
        for art in articles:
            title_a = art.find("h1", class_="entry-title")
            if title_a:
                link = title_a.find("a", href=True)
                if link:
                    results.append({
                        "title": link.get_text(strip=True),
                        "url": str(link.get("href", ""))
                    })
        return results
