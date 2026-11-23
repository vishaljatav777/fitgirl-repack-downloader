from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

# Force offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from downloader import ActiveFileProgress, DownloadTelemetry
from gui.main_window import MainWindow
from services import DownloadManagerService
from settings import AppSettings
from storage import JobStorage


def test_main_window_instantiation(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_gui.db"
        storage = JobStorage(db_path)
        service = DownloadManagerService(storage=storage)

        window = MainWindow(service=service)
        qtbot.addWidget(window)

        assert "FitGirl Repack Downloader" in window.windowTitle()
        assert window.stack.count() == 8
        assert window.stack.currentIndex() == 0  # Dashboard
        assert len(window.nav_buttons) == 8


def test_main_window_tab_navigation(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_gui.db"
        storage = JobStorage(db_path)
        service = DownloadManagerService(storage=storage)

        window = MainWindow(service=service)
        qtbot.addWidget(window)

        # Test switching across all 8 views
        for i in range(8):
            window.switch_view(i)
            assert window.stack.currentIndex() == i
            assert window.nav_buttons[i].isChecked() is True


def test_dashboard_view_metrics_update(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "db.sqlite")
        service = DownloadManagerService(storage=storage)
        window = MainWindow(service=service)
        qtbot.addWidget(window)

        window.dashboard_view.update_metrics(
            speed_mb=25.5,
            net_mbps=204.0,
            transferred_str="5.20 GB",
            completed_count=3
        )

        assert "25.5 MB/s" in cast(Any, window.dashboard_view.speed_card).value_label.text()
        assert "204.0 Mbps" in cast(Any, window.dashboard_view.net_card).value_label.text()
        assert "5.20 GB" in cast(Any, window.dashboard_view.transferred_card).value_label.text()
        assert "3" in cast(Any, window.dashboard_view.completed_card).value_label.text()


def test_active_downloads_telemetry_update(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "db.sqlite")
        service = DownloadManagerService(storage=storage)
        window = MainWindow(service=service)
        qtbot.addWidget(window)

        telemetry = DownloadTelemetry(
            total_bytes=1000,
            downloaded_bytes=500,
            completed_files=1,
            total_files=2,
            current_speed_bytes=1024 * 1024 * 5,
            net_bandwidth_mbps=40.0,
            elapsed_seconds=10.0,
            eta_seconds=10.0,
            active_files={
                "part01.rar": ActiveFileProgress(
                    filename="part01.rar",
                    downloaded_bytes=500,
                    total_bytes=1000,
                    speed_bytes_sec=1024 * 1024 * 5,
                    percentage=0.5
                )
            }
        )

        window.active_view.update_telemetry(telemetry)
        assert window.active_view.overall_bar.value() == 50
        assert window.active_view.table.rowCount() == 1
        item = window.active_view.table.item(0, 1)
        assert item is not None and item.text() == "part01.rar"


def test_settings_view_load_and_save(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        s = AppSettings(
            download_dir=Path(tmpdir) / "dl",
            extract_dir=Path(tmpdir) / "ext",
            max_concurrent_downloads=4,
            auto_extract=False,
            include_optionals=True
        )
        service = DownloadManagerService(settings=s, storage=JobStorage(Path(tmpdir) / "s.db"))
        window = MainWindow(service=service)
        qtbot.addWidget(window)

        assert window.settings_view.workers_slider.value() == 4
        assert window.settings_view.auto_extract_cb.isChecked() is False
        assert window.settings_view.optionals_cb.isChecked() is True


def test_diagnostics_view_update(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "d.db")
        service = DownloadManagerService(storage=storage)
        window = MainWindow(service=service)
        qtbot.addWidget(window)

        diag = {
            "browser_ready": True,
            "browser_path": "C:/Program Files/Brave/brave.exe",
            "unrar_ready": False,
            "unrar_path": "",
            "download_dir": tmpdir,
            "storage_free_gb": 120.5,
            "storage_total_gb": 500.0,
        }
        window.diagnostics_view.update_diagnostics(diag)
        assert cast(Any, window.diagnostics_view.browser_card).badge.text() == "READY"
        assert cast(Any, window.diagnostics_view.unrar_card).badge.text() == "MANUAL"


def test_close_event_clean_shutdown(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "c.db")
        service = DownloadManagerService(storage=storage)
        window = MainWindow(service=service)
        qtbot.addWidget(window)

        # When no active downloads are running, close should be accepted cleanly
        event = MagicMock()
        window.closeEvent(event)
        assert event.accept.called
