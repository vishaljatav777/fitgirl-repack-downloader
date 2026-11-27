from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

# Force offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtWidgets import QMessageBox

from downloader import ActiveFileProgress, DownloadTelemetry
from gui.main_window import MainWindow
from services import DownloadManagerService
from settings import AppSettings
from storage import JobStorage


@pytest.fixture(autouse=True)
def mock_qmessagebox():
    """Prevent any modal QMessageBox from blocking headless test execution."""
    with patch("PySide6.QtWidgets.QMessageBox.information") as m_info, \
         patch("PySide6.QtWidgets.QMessageBox.warning") as m_warn, \
         patch("PySide6.QtWidgets.QMessageBox.critical") as m_crit, \
         patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes) as m_quest:
        yield (m_info, m_warn, m_crit, m_quest)



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


def test_queue_view_search_and_selection(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "q.db")
        service = DownloadManagerService(storage=storage)

        with patch.object(service, "search_repacks", return_value=[{"title": "Elden Ring Deluxe", "url": "https://fitgirl-repacks.site/elden-ring/"}]), \
             patch("PySide6.QtWidgets.QMessageBox.warning"), \
             patch("PySide6.QtWidgets.QMessageBox.critical"):
            window = MainWindow(service=service)
            qtbot.addWidget(window)
            queue_view = window.queue_view

            # Mock start_download_flow so no scraping / network / modal dialog is triggered
            with patch.object(window, "start_download_flow"):
                # Test search emission
                with qtbot.waitSignal(queue_view.search_requested, timeout=1000) as blocker:
                    queue_view.search_input.setText("Elden Ring")
                    queue_view.search_btn.click()
                assert blocker.args[0] == "Elden Ring"

                # Results table populated
                assert queue_view.results_table.rowCount() == 1
                item = queue_view.results_table.item(0, 0)
                assert item is not None and item.text() == "Elden Ring Deluxe"

                # Test download requested emission
                with qtbot.waitSignal(queue_view.download_requested, timeout=1000) as blocker:
                    queue_view.results_table.selectRow(0)
                    queue_view.download_btn.click()
                assert blocker.args[0] == "https://fitgirl-repacks.site/elden-ring/"


def test_history_view_display_and_actions(qtbot):
    from storage import JobRecord, JobStatus

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "h.db")
        service = DownloadManagerService(storage=storage)
        with patch.object(service, "resume_job"), patch("PySide6.QtWidgets.QMessageBox.warning"):
            window = MainWindow(service=service)
            qtbot.addWidget(window)

            history_view = window.history_view
            job = JobRecord(
                id="job_123",
                title="Cyberpunk 2077",
                page_url="https://site.co/cp",
                download_dir=tmpdir,
                total_files=5,
                total_bytes=10000,
                status=JobStatus.COMPLETED,
                created_at=1000.0,
                updated_at=2000.0,
            )
            history_view.display_jobs([job])

            assert history_view.table.rowCount() == 1
            item = history_view.table.item(0, 0)
            assert item is not None and item.text() == "Cyberpunk 2077"

            # Test resume request emission
            with qtbot.waitSignal(history_view.resume_job_requested, timeout=1000) as blocker:
                history_view.table.selectRow(0)
                history_view.resume_btn.click()
            assert blocker.args[0] == "job_123"

            # Test open folder invokes os.startfile
            with patch("os.startfile") as mock_startfile:
                history_view.table.selectRow(0)
                history_view.open_folder_btn.click()
                assert mock_startfile.called


def test_extract_view_actions(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        storage = JobStorage(tmp_path / "e.db")
        service = DownloadManagerService(storage=storage)
        window = MainWindow(service=service)
        qtbot.addWidget(window)

        extract_view = window.extract_view
        extract_view.folder_input.setText(str(tmp_path))

        # Test verify emission
        with qtbot.waitSignal(extract_view.verify_requested, timeout=1000) as blocker:
            extract_view.verify_btn.click()
        assert blocker.args[0] == tmp_path

        # Test display verification output
        extract_view.set_verification_result(True, 3, [])
        assert "verified complete" in extract_view.status_lbl.text()

        # Test extract emission
        with qtbot.waitSignal(extract_view.extract_requested, timeout=1000) as blocker:
            extract_view.extract_btn.click()
        assert blocker.args[0] == tmp_path


def test_about_view_content(qtbot):
    from PySide6.QtWidgets import QLabel

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "a.db")
        service = DownloadManagerService(storage=storage)
        window = MainWindow(service=service)
        qtbot.addWidget(window)

        about_view = window.about_view
        header_lbl = about_view.findChild(QLabel, "viewHeader")
        assert header_lbl is not None
        assert "About" in header_lbl.text()

