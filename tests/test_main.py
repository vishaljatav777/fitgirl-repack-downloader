from __future__ import annotations
import pytest
from main import format_bytes, format_seconds, make_progress_bar

def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes(1536 * 1024) == "1.5 MB"
    assert format_bytes(2 * 1024 * 1024 * 1024) == "2.00 GB"

def test_format_seconds():
    assert format_seconds(30) == "30s"
    assert format_seconds(90) == "1m 30s"
    assert format_seconds(3665) == "1h 01m 05s"
    assert format_seconds(0) == "0s"
    assert format_seconds(-10) == "0s"

def test_make_progress_bar():
    bar_0 = make_progress_bar(0.0, width=10)
    assert "░" * 10 in bar_0

    bar_50 = make_progress_bar(0.5, width=10)
    assert "█" * 5 in bar_50
    assert "░" * 5 in bar_50

    bar_100 = make_progress_bar(1.0, width=10)
    assert "█" * 10 in bar_100
