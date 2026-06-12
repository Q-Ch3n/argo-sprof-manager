from __future__ import annotations

import csv
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from argo_sprof_manager import argo_sprof_core as core


TERMINAL_STATUSES = {"completed", "canceled", "failed"}
ACTIVE_STATUSES = {"queued", "running", "paused", "cancel_requested"}

DownloadFunc = Callable[
    [dict[str, Any], Path, int, int, bool, bool, threading.Event | None],
    tuple[bool, str],
]


def default_download_func(
    row: dict[str, Any],
    output_dir: Path,
    timeout: int,
    retries: int,
    force: bool,
    allow_insecure_ssl_fallback: bool,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, str]:
    local_path = output_dir / str(row["local_filename"])
    return core.download_file_atomic(
        url=str(row["sprof_url"]),
        outfile=local_path,
        timeout=timeout,
        retries=retries,
        force=force,
        ssl_context=core.make_ssl_context(verify_ssl=True),
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
        cancel_event=cancel_event,
    )


@dataclass
class DownloadJob:
    rows: list[dict[str, Any]]
    output_dir: Path
    timeout: int
    retries: int
    workers: int
    force: bool
    allow_insecure_ssl_fallback: bool
    download_func: DownloadFunc = default_download_func
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    status: str = "queued"
    submitted: int = 0
    completed: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    recent_lines: list[str] = field(default_factory=list)
    message: str = ""
    started_at: float | None = None
    updated_at: float | None = None
    manifest_path: Path | None = None

    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _pause_requested: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _cancel_requested: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def progress(self) -> float:
        return 1.0 if self.total == 0 else min(1.0, self.completed / self.total)

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self.started_at = time.time()
            self.updated_at = self.started_at
            self.status = "queued"
        self._thread = threading.Thread(target=self._run, name=f"argo-sprof-download-{self.job_id}", daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._pause_requested.set()
        with self._lock:
            if self.status not in TERMINAL_STATUSES:
                self.status = "paused"
                self.message = "Pause requested; downloads already in progress may finish."
                self.updated_at = time.time()

    def resume(self) -> None:
        self._pause_requested.clear()
        with self._lock:
            if self.status not in TERMINAL_STATUSES:
                self.status = "running"
                self.message = "Download resumed."
                self.updated_at = time.time()

    def cancel(self) -> None:
        self._cancel_requested.set()
        with self._lock:
            if self.status not in TERMINAL_STATUSES:
                self.status = "cancel_requested"
                self.message = "Cancel requested; downloads already in progress may finish."
                self.updated_at = time.time()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self.status,
                "submitted": self.submitted,
                "completed": self.completed,
                "total": self.total,
                "progress": self.progress,
                "results": list(self.results),
                "recent_lines": list(self.recent_lines),
                "message": self.message,
                "started_at": self.started_at,
                "updated_at": self.updated_at,
                "manifest_path": str(self.manifest_path) if self.manifest_path else "",
                "pause_requested": self._pause_requested.is_set(),
                "cancel_requested": self._cancel_requested.is_set(),
            }

    def _run(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.output_dir / "download_manifest.csv"
        executor = ThreadPoolExecutor(max_workers=max(1, self.workers))
        futures: dict[Future[dict[str, Any]], dict[str, Any]] = {}
        next_index = 0

        try:
            self._set_status("running", "Download started.")
            self._write_manifest()
            while True:
                if self._cancel_requested.is_set():
                    self._set_status("cancel_requested", "Cancel requested; stopping active downloads.")
                elif self._pause_requested.is_set():
                    self._set_status("paused", "Paused. Active downloads may finish before stopping completely.")
                else:
                    self._set_status("running", "Downloading.")
                    while (
                        next_index < self.total
                        and len(futures) < max(1, self.workers)
                        and not self._pause_requested.is_set()
                        and not self._cancel_requested.is_set()
                    ):
                        row = self.rows[next_index]
                        futures[executor.submit(self._download_row, row)] = row
                        next_index += 1
                        with self._lock:
                            self.submitted = next_index
                            self.updated_at = time.time()

                if futures:
                    done, _ = wait(set(futures), timeout=0.25, return_when=FIRST_COMPLETED)
                    for future in done:
                        futures.pop(future, None)
                        self._record_result(self._future_result(future))
                elif self._cancel_requested.is_set():
                    break
                elif next_index >= self.total:
                    break
                else:
                    time.sleep(0.2)

            if self._cancel_requested.is_set():
                self._set_status("canceled", "Download canceled. In-progress files may have completed.")
            elif self.completed >= self.total:
                self._set_status("completed", "Download completed.")
            else:
                self._set_status("completed", "No remaining downloads.")
        except Exception as exc:
            self._set_status("failed", f"Download job failed: {exc}")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            self._write_manifest()

    def _download_row(self, row: dict[str, Any]) -> dict[str, Any]:
        local_path = self.output_dir / str(row["local_filename"])
        try:
            downloaded, status = self.download_func(
                row,
                self.output_dir,
                self.timeout,
                self.retries,
                self.force,
                self.allow_insecure_ssl_fallback,
                self._cancel_requested,
            )
        except Exception as exc:
            downloaded, status = False, f"error: {exc}"
        return {
            "dac": row.get("dac", ""),
            "wmo": row.get("wmo", ""),
            "downloaded": downloaded,
            "status": status,
            "local_filename": row.get("local_filename", ""),
            "local_path": str(local_path),
        }

    def _future_result(self, future: Future[dict[str, Any]]) -> dict[str, Any]:
        try:
            return future.result()
        except Exception as exc:
            return {
                "dac": "",
                "wmo": "",
                "downloaded": False,
                "status": f"error: {exc}",
                "local_filename": "",
                "local_path": "",
            }

    def _record_result(self, result: dict[str, Any]) -> None:
        with self._lock:
            self.results.append(result)
            self.completed = len(self.results)
            line = f"[{self.completed}/{self.total}] {result.get('dac', '')} {result.get('wmo', '')}: {result.get('status', '')}"
            self.recent_lines.append(line)
            self.recent_lines = self.recent_lines[-12:]
            self.updated_at = time.time()
        self._write_manifest()

    def _set_status(self, status: str, message: str) -> None:
        with self._lock:
            if self.status not in TERMINAL_STATUSES:
                self.status = status
                self.message = message
                self.updated_at = time.time()

    def _write_manifest(self) -> None:
        if self.manifest_path is None:
            return
        rows = self._manifest_rows()
        fieldnames = ["dac", "wmo", "downloaded", "status", "category", "local_filename", "local_path"]
        with open(self.manifest_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _manifest_rows(self) -> list[dict[str, Any]]:
        with self._lock:
            result_map = {
                (str(row.get("dac", "")), str(row.get("wmo", ""))): dict(row)
                for row in self.results
            }
            source_rows = list(self.rows)

        rows: list[dict[str, Any]] = []
        for source in source_rows:
            key = (str(source.get("dac", "")), str(source.get("wmo", "")))
            result = result_map.get(key)
            if result is None:
                row = {
                    "dac": source.get("dac", ""),
                    "wmo": source.get("wmo", ""),
                    "downloaded": False,
                    "status": "pending",
                    "local_filename": source.get("local_filename", ""),
                    "local_path": str(self.output_dir / str(source.get("local_filename", ""))),
                }
            else:
                row = result
            row["category"] = core.classify_download_status(str(row.get("status", "")))
            rows.append(row)
        return rows


_JOBS: dict[str, DownloadJob] = {}
_JOBS_LOCK = threading.Lock()


def start_download_job(
    rows: list[dict[str, Any]],
    output_dir: Path,
    timeout: int,
    retries: int,
    workers: int,
    force: bool,
    allow_insecure_ssl_fallback: bool,
    download_func: DownloadFunc = default_download_func,
) -> DownloadJob:
    job = DownloadJob(
        rows=rows,
        output_dir=output_dir,
        timeout=timeout,
        retries=retries,
        workers=workers,
        force=force,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
        download_func=download_func,
    )
    with _JOBS_LOCK:
        _JOBS[job.job_id] = job
    job.start()
    return job


def get_job(job_id: str | None) -> DownloadJob | None:
    if not job_id:
        return None
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def forget_job(job_id: str | None) -> None:
    if not job_id:
        return
    with _JOBS_LOCK:
        _JOBS.pop(job_id, None)
