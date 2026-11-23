from __future__ import annotations

import pytest

from scraper import DownloadItem, FitGirlScraper


def test_download_item_defaults():
    item = DownloadItem(
        filename="game.part01.rar",
        share_url="https://fuckingfast.co/test"
    )
    assert item.filename == "game.part01.rar"
    assert item.is_optional is False
    assert item.is_selective is False
    assert item.direct_url is None

def test_scraper_url_validation():
    scraper = FitGirlScraper()
    with pytest.raises(ValueError, match="URL cannot be empty"):
        scraper.scrape_url("")

def test_scraper_direct_fuckingfast_url():
    scraper = FitGirlScraper()
    url = "https://fuckingfast.co/abc123xyz#game.part01.rar"
    repack = scraper.scrape_url(url)
    assert len(repack.parts) == 1
    assert repack.parts[0].filename == "game.part01.rar"
    assert repack.parts[0].share_url == "https://fuckingfast.co/abc123xyz"
