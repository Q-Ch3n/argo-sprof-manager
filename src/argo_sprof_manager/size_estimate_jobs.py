from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Any, Callable

from argo_sprof_manager import argo_sprof_core as core


TERMINAL_STATUSES = {"completed", "canceled", "failed"}
ACTIVE_STATUSES = {"queued", "running", "cancel_requested"}

SizeProbeFunc = Callable[
    [dict[str, Any], int, bool, threading.Event | None],
    tuple[int | None, str],
]


def default_size_probe(
    row: dict[str, Any],
    timeout: int,
    allow_insecure_ssl_fallback: bool,
    cancel_event: threading.Event | None = None,
) -> tuple[int | None, str]:
    if cancel_event is not None and cancel_event.is_set():
        return None, "canceled"
    return core.remote_file_size(
        str(row["sprof_url"]),
        timeout=timeout,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
    )


@dataclass
class SizeEstimateJob:
    rows: list[dict[str, Any]]
    source_total: int
    mode: str
    timeout: int
    workers: int
    allow_insecure_ssl_fallback: bool
    size_probe: SizeProbeFunc = default_size_probe
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    status: str = "queued"
    submitted: int = 0
    completed: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    recent_lines: list[str] = field(default_factory=list)
    message: str = ""
    started_at: float | None = None
    updated_at: float | None = None

    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
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
        self._thread = threading.Thread(target=self._run, name=f"argo-sprof-size-{self.job_id}", daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._cancel_requested.set()
        with self._lock:
            if self.status not in TERMINAL_STATUSES:
                self.status = "cancel_requested"
                self.message = "Cancel requested; size probes already in progress may finish."
                self.updated_at = time.time()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            results = list(self.results)
            total_size = sum(
                int(row["size_bytes"])
                for row in results
                if isinstance(row.get("size_bytes"), int)
            )
            success_count = sum(1 for row in results if isinstance(row.get("size_bytes"), int))
            projected_total = None
            if self.mode == "sample_n" and success_count > 0 and self.source_total > 0:
                projected_total = int(total_size / success_count * self.source_total)
            return {
                "job_id": self.job_id,
                "status": self.status,
                "submitted": self.submitted,
                "completed": self.completed,
                "total": self.total,
                "source_total": self.source_total,
                "mode": self.mode,
                "progress": self.progress,
                "results": results,
                "recent_lines": list(self.recent_lines),
                "message": self.message,
                "started_at": self.started_at,
                "updated_at": self.updated_at,
                "cancel_requested": self._cancel_requested.is_set(),
                "total_size_bytes": total_size,
                "success_count": success_count,
                "projected_total_size_bytes": projected_total,
            }

    def _run(self) -> None:
        executor = ThreadPoolExecutor(max_workers=max(1, self.workers))
        futures: dict[Future[dict[str, Any]], dict[str, Any]] = {}
        next_index = 0

        try:
            self._set_status("running", "Remote size estimate started.")
            while True:
                if self._cancel_requested.is_set():
                    self._set_status("cancel_requested", "Cancel requested; stopping new size probes.")
                else:
                    self._set_status("running", "Estimating remote sizes.")
                    while (
                        next_index < self.total
                        and len(futures) < max(1, self.workers)
                        and not self._cancel_requested.is_set()
                    ):
                        row = self.rows[next_index]
                        futures[executor.submit(self._estimate_row, row)] = row
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
                self._set_status("canceled", "Remote size estimate canceled.")
            elif self.completed >= self.total:
                self._set_status("completed", "Remote size estimate completed.")
            else:
                self._set_status("completed", "No remaining size probes.")
        except Exception as exc:
            self._set_status("failed", f"Remote size estimate failed: {exc}")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _estimate_row(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            size_bytes, status = self.size_probe(
                row,
                self.timeout,
                self.allow_insecure_ssl_fallback,
                self._cancel_requested,
            )
        except Exception as exc:
            size_bytes, status = None, f"failed: {exc}"
        return {
            "dac": row.get("dac", ""),
            "wmo": row.get("wmo", ""),
            "size_bytes": size_bytes,
            "status": status,
            "sprof_url": row.get("sprof_url", ""),
        }

    def _future_result(self, future: Future[dict[str, Any]]) -> dict[str, Any]:
        try:
            return future.result()
        except Exception as exc:
            return {
                "dac": "",
                "wmo": "",
                "size_bytes": None,
                "status": f"failed: {exc}",
                "sprof_url": "",
            }

    def _record_result(self, result: dict[str, Any]) -> None:
        with self._lock:
            self.results.append(result)
            self.completed = len(self.results)
            size_text = result.get("size_bytes")
            status_text = result.get("status", "")
            line = f"[{self.completed}/{self.total}] {result.get('dac', '')} {result.get('wmo', '')}: {size_text if size_text is not None else status_text}"
            self.recent_lines.append(line)
            self.recent_lines = self.recent_lines[-12:]
            self.updated_at = time.time()

    def _set_status(self, status: str, message: str) -> None:
        with self._lock:
            if self.status not in TERMINAL_STATUSES:
                self.status = status
                self.message = message
                self.updated_at = time.time()


_JOBS: dict[str, SizeEstimateJob] = {}
_JOBS_LOCK = threading.Lock()


def start_size_estimate_job(
    rows: list[dict[str, Any]],
    source_total: int,
    mode: str,
    timeout: int,
    workers: int,
    allow_insecure_ssl_fallback: bool,
    size_probe: SizeProbeFunc = default_size_probe,
) -> SizeEstimateJob:
    job = SizeEstimateJob(
        rows=rows,
        source_total=source_total,
        mode=mode,
        timeout=timeout,
        workers=workers,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
        size_probe=size_probe,
    )
    with _JOBS_LOCK:
        _JOBS[job.job_id] = job
    job.start()
    return job


def get_job(job_id: str | None) -> SizeEstimateJob | None:
    if not job_id:
        return None
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def forget_job(job_id: str | None) -> None:
    if not job_id:
        return
    with _JOBS_LOCK:
        _JOBS.pop(job_id, None)
