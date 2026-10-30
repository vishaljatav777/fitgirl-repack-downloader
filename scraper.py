import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from config import USER_AGENT, TIMEOUT

@dataclass
class DownloadItem:
    filename: str
    share_url: str
    is_optional: bool = False
    is_selective: bool = False
    direct_url: Optional[str] = None
    size_bytes: int = 0

@dataclass
class GameRepack:
    title: str
    page_url: str
    parts: List[DownloadItem] = field(default_factory=list)
    optionals: List[DownloadItem] = field(default_factory=list)

class FitGirlScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape_url(self, url: str) -> GameRepack:
        """Scrapes a FitGirl repack page and extracts all FuckingFast links."""
        url = url.strip()
        if not url:
            raise ValueError("URL cannot be empty.")

        # Ensure scheme
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

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

        response = self.session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract title
        title_tag = soup.find("h1", class_="entry-title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown Game Repack"
        
        # Find all fuckingfast links
        ff_anchors = [
            a for a in soup.find_all("a", href=True)
            if "fuckingfast.co" in a["href"]
        ]
        
        parts: List[DownloadItem] = []
        optionals: List[DownloadItem] = []
        seen_urls = set()

        for a in ff_anchors:
            href = a["href"].strip()
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

    def search_game(self, query: str) -> List[Dict[str, str]]:
        """Searches FitGirl site and returns matching results (title and url)."""
        search_url = f"https://fitgirl-repacks.site/?s={requests.utils.quote(query)}"
        response = self.session.get(search_url, timeout=TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        articles = soup.find_all("article")
        for art in articles:
            title_a = art.find("h1", class_="entry-title")
            if title_a:
                link = title_a.find("a", href=True)
                if link:
                    results.append({
                        "title": link.get_text(strip=True),
                        "url": link["href"]
                    })
        return results
