"""
SQLite persistent job storage and recovery module.
Manages download jobs, parts, and resumption across application restarts using WAL mode.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class JobStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PAUSED = "PAUSED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PartStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class JobRecord:
    id: str
    title: str
    page_url: str
    download_dir: str
    total_files: int = 0
    total_bytes: int = 0
    downloaded_bytes: int = 0
    status: JobStatus = JobStatus.PENDING
    created_at: float = 0.0
    updated_at: float = 0.0
    error_message: str | None = None


@dataclass
class PartRecord:
    id: int | None
    job_id: str
    filename: str
    part_number: int
    share_url: str
    direct_url: str | None = None
    total_bytes: int = 0
    downloaded_bytes: int = 0
    status: PartStatus = PartStatus.PENDING
    checksum_sha256: str | None = None
    created_at: float = 0.0
    updated_at: float = 0.0


class JobStorage:
    """Manages SQLite job and part persistence with ACID guarantees."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a managed SQLite connection that closes promptly on exit.

        Prevents open file locks on Windows volumes.
        """
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    page_url TEXT NOT NULL,
                    download_dir TEXT NOT NULL,
                    total_files INTEGER NOT NULL DEFAULT 0,
                    total_bytes INTEGER NOT NULL DEFAULT 0,
                    downloaded_bytes INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    error_message TEXT
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    part_number INTEGER NOT NULL,
                    share_url TEXT NOT NULL,
                    direct_url TEXT,
                    total_bytes INTEGER NOT NULL DEFAULT 0,
                    downloaded_bytes INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    checksum_sha256 TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(job_id, filename)
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_parts_job_id ON download_parts(job_id);")

    def create_or_update_job(
        self,
        job_id: str,
        title: str,
        page_url: str,
        download_dir: Path,
        total_files: int = 0,
        total_bytes: int = 0,
        status: JobStatus = JobStatus.PENDING,
    ) -> JobRecord:
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (id, title, page_url, download_dir, total_files, total_bytes, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    total_files = excluded.total_files,
                    total_bytes = excluded.total_bytes,
                    updated_at = excluded.updated_at;
            """, (job_id, title, page_url, str(download_dir), total_files, total_bytes, status.value, now, now))

        job = self.get_job(job_id)
        if job is None:
            raise RuntimeError(f"Failed to create or retrieve job {job_id}")
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            return JobRecord(
                id=row["id"],
                title=row["title"],
                page_url=row["page_url"],
                download_dir=row["download_dir"],
                total_files=row["total_files"],
                total_bytes=row["total_bytes"],
                downloaded_bytes=row["downloaded_bytes"],
                status=JobStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                error_message=row["error_message"],
            )

    def get_job_by_url(self, page_url: str) -> JobRecord | None:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE page_url = ?", (page_url,))
            row = cur.fetchone()
            if not row:
                return None
            return JobRecord(
                id=row["id"],
                title=row["title"],
                page_url=row["page_url"],
                download_dir=row["download_dir"],
                total_files=row["total_files"],
                total_bytes=row["total_bytes"],
                downloaded_bytes=row["downloaded_bytes"],
                status=JobStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                error_message=row["error_message"],
            )

    def update_job_status(
        self, job_id: str, status: JobStatus, error_message: str | None = None
    ) -> None:
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE jobs
                SET status = ?, error_message = ?, updated_at = ?
                WHERE id = ?;
            """, (status.value, error_message, now, job_id))

    def save_parts(self, job_id: str, parts: list[dict]) -> None:
        now = time.time()
        with self._get_connection() as conn:
            for idx, p in enumerate(parts, 1):
                conn.execute("""
                    INSERT INTO download_parts (
                        job_id, filename, part_number, share_url, direct_url,
                        total_bytes, downloaded_bytes, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_id, filename) DO UPDATE SET
                        direct_url = COALESCE(excluded.direct_url, download_parts.direct_url),
                        total_bytes = CASE WHEN excluded.total_bytes > 0 THEN excluded.total_bytes ELSE download_parts.total_bytes END,
                        updated_at = excluded.updated_at;
                """, (
                    job_id,
                    p["filename"],
                    p.get("part_number", idx),
                    p["share_url"],
                    p.get("direct_url"),
                    p.get("total_bytes", 0),
                    p.get("downloaded_bytes", 0),
                    p.get("status", PartStatus.PENDING.value),
                    now,
                    now
                ))

    def update_part_progress(
        self,
        job_id: str,
        filename: str,
        downloaded_bytes: int,
        total_bytes: int = 0,
        status: PartStatus = PartStatus.DOWNLOADING,
        checksum: str | None = None,
    ) -> None:
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE download_parts
                SET downloaded_bytes = ?,
                    total_bytes = CASE WHEN ? > 0 THEN ? ELSE total_bytes END,
                    status = ?,
                    checksum_sha256 = COALESCE(?, checksum_sha256),
                    updated_at = ?
                WHERE job_id = ? AND filename = ?;
            """, (downloaded_bytes, total_bytes, total_bytes, status.value, checksum, now, job_id, filename))

            # Recalculate aggregate downloaded_bytes for job
            conn.execute("""
                UPDATE jobs
                SET downloaded_bytes = (
                    SELECT COALESCE(SUM(downloaded_bytes), 0)
                    FROM download_parts
                    WHERE job_id = ?
                ),
                updated_at = ?
                WHERE id = ?;
            """, (job_id, now, job_id))

    def get_parts(self, job_id: str) -> list[PartRecord]:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM download_parts WHERE job_id = ? ORDER BY part_number ASC;",
                (job_id,)
            )
            rows = cur.fetchall()
            return [
                PartRecord(
                    id=row["id"],
                    job_id=row["job_id"],
                    filename=row["filename"],
                    part_number=row["part_number"],
                    share_url=row["share_url"],
                    direct_url=row["direct_url"],
                    total_bytes=row["total_bytes"],
                    downloaded_bytes=row["downloaded_bytes"],
                    status=PartStatus(row["status"]),
                    checksum_sha256=row["checksum_sha256"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def list_jobs(self, status: JobStatus | None = None) -> list[JobRecord]:
        with self._get_connection() as conn:
            if status:
                cur = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC;", (status.value,))
            else:
                cur = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC;")
            rows = cur.fetchall()
            return [
                JobRecord(
                    id=row["id"],
                    title=row["title"],
                    page_url=row["page_url"],
                    download_dir=row["download_dir"],
                    total_files=row["total_files"],
                    total_bytes=row["total_bytes"],
                    downloaded_bytes=row["downloaded_bytes"],
                    status=JobStatus(row["status"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    error_message=row["error_message"],
                )
                for row in rows
            ]
