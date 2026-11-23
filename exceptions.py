"""
Domain-specific exception hierarchy for the FitGirl Repack Downloader.
Replaces broad exception handling with structured, typed errors.
"""

from __future__ import annotations


class FitGirlDownloaderError(Exception):
    """Base exception for all FitGirl Downloader errors."""

    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


class ConfigurationError(FitGirlDownloaderError):
    """Raised when application configuration or settings are invalid."""


class ScraperError(FitGirlDownloaderError):
    """Raised when parsing or scraping a FitGirl repack page fails."""


class NoLinksFoundError(ScraperError):
    """Raised when a repack page contains no supported download links."""


class ResolverError(FitGirlDownloaderError):
    """Raised when resolving direct download links fails."""


class BrowserNotFoundError(ResolverError):
    """Raised when no compatible browser executable is found on the system."""


class DownloadError(FitGirlDownloaderError):
    """Raised when a file download operation encounters an error."""


class RangeNotSupportedError(DownloadError):
    """Raised when an HTTP Range request was sent but server returned full body (HTTP 200)."""


class IncompleteDownloadError(DownloadError):
    """Raised when a download ends before transferring the expected total byte count."""


class DiskSpaceError(DownloadError):
    """Raised when insufficient storage remains on the target volume."""


class VerificationError(FitGirlDownloaderError):
    """Raised when archive verification fails (e.g. missing parts or corrupted headers)."""


class ExtractionError(FitGirlDownloaderError):
    """Raised when archive extraction fails."""


class UnpackerNotFoundError(ExtractionError):
    """Raised when neither WinRAR nor 7-Zip executable is available."""


class SecurityError(FitGirlDownloaderError):
    """Base security error for access boundary or input validation violations."""


class PathTraversalError(SecurityError):
    """Raised when a filename or path attempts to escape the destination directory."""
