from __future__ import annotations

from exceptions import (
    BrowserNotFoundError,
    ConfigurationError,
    DiskSpaceError,
    DownloadError,
    ExtractionError,
    FitGirlDownloaderError,
    IncompleteDownloadError,
    NoLinksFoundError,
    PathTraversalError,
    RangeNotSupportedError,
    ResolverError,
    ScraperError,
    SecurityError,
    UnpackerNotFoundError,
    VerificationError,
)


def test_exception_hierarchy():
    # Base
    err = FitGirlDownloaderError("Base error", "Extra details")
    assert str(err) == "Base error (Extra details)"
    assert isinstance(err, Exception)

    # Scraper
    scraper_err = ScraperError("Scraper error")
    assert isinstance(scraper_err, FitGirlDownloaderError)

    no_links = NoLinksFoundError("No links found")
    assert isinstance(no_links, ScraperError)

    # Resolver
    resolver_err = ResolverError("Resolver error")
    assert isinstance(resolver_err, FitGirlDownloaderError)

    browser_not_found = BrowserNotFoundError("No browser")
    assert isinstance(browser_not_found, ResolverError)

    # Downloader
    dl_err = DownloadError("Download failed")
    assert isinstance(dl_err, FitGirlDownloaderError)

    range_err = RangeNotSupportedError("Range not supported")
    assert isinstance(range_err, DownloadError)

    incomplete_err = IncompleteDownloadError("Truncated stream")
    assert isinstance(incomplete_err, DownloadError)

    disk_err = DiskSpaceError("Disk full")
    assert isinstance(disk_err, DownloadError)

    # Verifier & Extractor
    verif_err = VerificationError("Corrupted parts")
    assert isinstance(verif_err, FitGirlDownloaderError)

    extract_err = ExtractionError("Unpack failed")
    assert isinstance(extract_err, FitGirlDownloaderError)

    unpacker_err = UnpackerNotFoundError("7z missing")
    assert isinstance(unpacker_err, ExtractionError)

    # Security
    sec_err = SecurityError("Security violation")
    assert isinstance(sec_err, FitGirlDownloaderError)

    traversal_err = PathTraversalError("Path traversal detected")
    assert isinstance(traversal_err, SecurityError)

    # Configuration
    cfg_err = ConfigurationError("Invalid setting")
    assert isinstance(cfg_err, FitGirlDownloaderError)
