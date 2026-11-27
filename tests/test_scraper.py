from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from exceptions import ScraperError
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


def test_scraper_authorized_direct_archive_url():
    scraper = FitGirlScraper()
    url = "https://authorized.example.com/files/game.part01.rar"
    repack = scraper.scrape_url(url)
    assert len(repack.parts) == 1
    assert repack.parts[0].filename == "game.part01.rar"
    assert repack.parts[0].share_url == url
    assert repack.parts[0].direct_url == url


def test_scraper_authorized_direct_zip_with_fragment():
    scraper = FitGirlScraper()
    url = "https://authorized.example.com/download?id=123#MyArchive.zip"
    repack = scraper.scrape_url(url)
    assert len(repack.parts) == 1
    assert repack.parts[0].filename == "MyArchive.zip"
    assert repack.parts[0].direct_url == "https://authorized.example.com/download?id=123"


def test_scraper_search_game_blocked_raises_scraper_error():
    scraper = FitGirlScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch("scraper.cffi_requests.get", return_value=mock_resp), \
         patch.object(scraper.session, "get", return_value=mock_resp):
        with pytest.raises(ScraperError) as exc_info:
            scraper.search_game("God of War")
        assert "Access blocked" in str(exc_info.value)
        assert "Cloudflare" in exc_info.value.details


def test_scraper_ssl_eof_error_raises_scraper_error():
    scraper = FitGirlScraper()
    ssl_err = requests.exceptions.SSLError("EOF occurred in violation of protocol (_ssl.c:1032)")

    with patch("scraper.HAS_CURL_CFFI", False), \
         patch.object(scraper.session, "get", side_effect=ssl_err):
        with pytest.raises(ScraperError) as exc_info:
            scraper.search_game("God of War")
        assert "SSL/TLS handshake was terminated" in exc_info.value.details


def test_scraper_search_success_parsing():
    scraper = FitGirlScraper()
    sample_html = (
        '<html><body><article><h1 class="entry-title">'
        '<a href="https://fitgirl-repacks.site/god-of-war/">God of War (v1.0.12)</a>'
        '</h1></article></body></html>'
    )
    with patch.object(scraper, "_fetch_html", return_value=sample_html):
        results = scraper.search_game("god of war")
        assert len(results) == 1
        assert results[0]["title"] == "God of War (v1.0.12)"
        assert results[0]["url"] == "https://fitgirl-repacks.site/god-of-war/"


def test_scraper_dl_fuckingfast_recognized_as_direct():
    scraper = FitGirlScraper()
    url = "https://dl.fuckingfast.co/download/abcdef123456/game.part01.rar"
    repack = scraper.scrape_url(url)
    assert len(repack.parts) == 1
    assert repack.parts[0].filename == "game.part01.rar"
    assert repack.parts[0].direct_url == url


def test_scraper_local_txt_manifest(tmp_path):
    manifest_file = tmp_path / "links.txt"
    manifest_file.write_text(
        "https://dl.fuckingfast.co/part01.rar\n"
        "https://dl.fuckingfast.co/part02.rar\n"
        "# Comment\n",
        encoding="utf-8"
    )
    scraper = FitGirlScraper()
    repack = scraper.scrape_url(str(manifest_file))
    assert len(repack.parts) == 2
    assert repack.parts[0].filename == "part01.rar"
    assert repack.parts[0].direct_url == "https://dl.fuckingfast.co/part01.rar"
    assert repack.parts[1].filename == "part02.rar"
    assert repack.parts[1].direct_url == "https://dl.fuckingfast.co/part02.rar"



