from __future__ import annotations

import csv
import os
import shutil
import ssl
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, replace
from http.client import IncompleteRead
from importlib import metadata
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_INDEX_URL = "https://data-argo.ifremer.fr/argo_synthetic-profile_index.txt"
DEFAULT_BASE_URL = "https://data-argo.ifremer.fr/dac/"
USER_AGENT = "argo-sprof-manager/1.0.0"
SUCCESS_STATUSES = {"downloaded", "exists"}
INCOMPLETE_STATUSES = {"pending", "canceled", "too_small", "404"}


@dataclass(frozen=True)
class FloatRecord:
    dac: str
    wmo: str
    parameters: str = ""
    date: str = ""
    latitude: float | None = None
    longitude: float | None = None
    ocean: str = ""
    profiler_type: str = ""
    institution: str = ""
    date_update: str = ""
    parameter_data_mode: str = ""

    @property
    def filename(self) -> str:
        return f"{self.wmo}_Sprof.nc"

    @property
    def relpath(self) -> str:
        return f"{self.dac}/{self.wmo}/{self.filename}"


@dataclass(frozen=True)
class DownloadResult:
    dac: str
    wmo: str
    filename: str
    downloaded: bool
    status: str


@dataclass(frozen=True)
class RemoteSizeResult:
    dac: str
    wmo: str
    size_bytes: int | None
    status: str


def make_ssl_context(verify_ssl: bool = True) -> ssl.SSLContext | None:
    if not verify_ssl:
        return ssl._create_unverified_context()

    try:
        import certifi  # type: ignore
    except ImportError:
        return ssl.create_default_context()

    return ssl.create_default_context(cafile=certifi.where())


def is_certificate_verify_error(error: Exception) -> bool:
    reason = getattr(error, "reason", None)
    return (
        isinstance(error, ssl.SSLCertVerificationError)
        or isinstance(reason, ssl.SSLCertVerificationError)
        or "CERTIFICATE_VERIFY_FAILED" in str(error)
    )


def open_url(req: Request, timeout: int, ssl_context: ssl.SSLContext | None):
    return urlopen(req, timeout=timeout, context=ssl_context)


def read_response_bytes(response, chunk_size: int = 1024 * 1024) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)

    expected = response.headers.get("Content-Length")
    if expected:
        expected_bytes = int(expected)
        if total < expected_bytes:
            raise IncompleteRead(b"".join(chunks), expected_bytes - total)

    return b"".join(chunks)


def http_download_bytes(
    url: str,
    timeout: int = 120,
    retries: int = 3,
    ssl_context: ssl.SSLContext | None = None,
    allow_insecure_ssl_fallback: bool = True,
) -> bytes:
    last_error: Exception | None = None
    insecure_context: ssl.SSLContext | None = None
    use_insecure_context = False
    attempt = 0

    while attempt < retries:
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            context = insecure_context if use_insecure_context else ssl_context
            with open_url(req, timeout=timeout, ssl_context=context) as response:
                return read_response_bytes(response)
        except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead) as exc:
            last_error = exc
            if (
                allow_insecure_ssl_fallback
                and not use_insecure_context
                and is_certificate_verify_error(exc)
            ):
                insecure_context = make_ssl_context(verify_ssl=False)
                use_insecure_context = True
                continue

            attempt += 1
            time.sleep(min(30, 2 ** (attempt - 1)))

    raise RuntimeError(f"Could not download {url}: {last_error}")


def download_file_atomic(
    url: str,
    outfile: Path,
    timeout: int = 120,
    retries: int = 3,
    min_bytes: int = 1024,
    force: bool = False,
    ssl_context: ssl.SSLContext | None = None,
    allow_insecure_ssl_fallback: bool = True,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, str]:
    outfile.parent.mkdir(parents=True, exist_ok=True)

    if cancel_event is not None and cancel_event.is_set():
        return False, "canceled"

    if outfile.exists() and outfile.stat().st_size >= min_bytes and not force:
        return False, "exists"

    tmpfile = outfile.with_suffix(outfile.suffix + ".part")
    if tmpfile.exists():
        tmpfile.unlink()

    last_error: Exception | None = None
    insecure_context: ssl.SSLContext | None = None
    use_insecure_context = False
    attempt = 0

    while attempt < retries:
        if cancel_event is not None and cancel_event.is_set():
            tmpfile.unlink(missing_ok=True)
            return False, "canceled"

        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            context = insecure_context if use_insecure_context else ssl_context
            with open_url(req, timeout=timeout, ssl_context=context) as response, open(tmpfile, "wb") as handle:
                expected_length_text = response.headers.get("Content-Length")
                try:
                    expected_length = int(expected_length_text) if expected_length_text else None
                except ValueError:
                    expected_length = None
                bytes_written = 0
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        tmpfile.unlink(missing_ok=True)
                        return False, "canceled"
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    bytes_written += len(chunk)

            if expected_length is not None and bytes_written < expected_length:
                raise IncompleteRead(b"", expected_length - bytes_written)

            if cancel_event is not None and cancel_event.is_set():
                tmpfile.unlink(missing_ok=True)
                return False, "canceled"

            if tmpfile.stat().st_size < min_bytes:
                tmpfile.unlink(missing_ok=True)
                return False, "too_small"

            os.replace(tmpfile, outfile)
            return True, "downloaded"

        except HTTPError as exc:
            last_error = exc
            tmpfile.unlink(missing_ok=True)
            if exc.code == 404:
                return False, "404"
            attempt += 1
            time.sleep(min(60, 2 ** (attempt - 1)))

        except (URLError, TimeoutError, OSError, IncompleteRead) as exc:
            last_error = exc
            tmpfile.unlink(missing_ok=True)
            if (
                allow_insecure_ssl_fallback
                and not use_insecure_context
                and is_certificate_verify_error(exc)
            ):
                insecure_context = make_ssl_context(verify_ssl=False)
                use_insecure_context = True
                continue

            attempt += 1
            time.sleep(min(60, 2 ** (attempt - 1)))

    return False, f"failed: {last_error}"


def find_csv_header_line(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.lower().startswith("file,"):
            return index
    raise ValueError("Cannot find CSV header line starting with 'file,' in index file.")


def normalize_parameter_list(text: str) -> set[str]:
    if not text:
        return set()
    raw = text.replace(",", " ").replace(";", " ").split()
    return {item.strip().upper() for item in raw if item.strip()}


def split_variables(parameters: str) -> list[str]:
    return sorted(normalize_parameter_list(parameters))


def row_value(row: dict[str, str], *names: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None:
            return str(value).strip()
    return ""


def parse_float(value: str) -> float | None:
    try:
        if value == "":
            return None
        return float(value)
    except ValueError:
        return None


def record_from_index_row(row: dict[str, str]) -> FloatRecord | None:
    file_field = row_value(row, "file", "File")
    if not file_field:
        return None

    parts = file_field.split("/")
    if len(parts) < 2:
        return None

    dac, wmo = parts[0].strip(), parts[1].strip()
    if not wmo.isdigit():
        return None

    params = row_value(row, "parameters", "parameters list", "parameter")
    params_upper = normalize_parameter_list(params)

    return FloatRecord(
        dac=dac,
        wmo=wmo,
        parameters=" ".join(sorted(params_upper)),
        date=row_value(row, "date"),
        latitude=parse_float(row_value(row, "latitude")),
        longitude=parse_float(row_value(row, "longitude")),
        ocean=row_value(row, "ocean"),
        profiler_type=row_value(row, "profiler_type", "profiler type"),
        institution=row_value(row, "institution"),
        date_update=row_value(row, "date_update", "date update"),
        parameter_data_mode=row_value(row, "parameter_data_mode", "parameter data mode"),
    )


def merge_float_records(old: FloatRecord, new: FloatRecord) -> FloatRecord:
    merged_parameters = " ".join(sorted(normalize_parameter_list(old.parameters) | normalize_parameter_list(new.parameters)))
    newest = new if new.date_update >= old.date_update else old
    return replace(newest, parameters=merged_parameters)


def parse_synthetic_index(
    index_text: str,
    only_vars: set[str] | None = None,
) -> list[FloatRecord]:
    lines = index_text.splitlines()
    header_idx = find_csv_header_line(lines)
    reader = csv.DictReader(lines[header_idx:])
    unique: dict[tuple[str, str], FloatRecord] = {}

    for row in reader:
        record = record_from_index_row(row)
        if record is None:
            continue

        params_upper = normalize_parameter_list(record.parameters)
        if only_vars and not (params_upper & only_vars):
            continue

        key = (record.dac, record.wmo)
        unique[key] = record if key not in unique else merge_float_records(unique[key], record)

    return sorted(unique.values(), key=lambda item: (item.dac, item.wmo))


def fetch_latest_records(
    index_url: str = DEFAULT_INDEX_URL,
    timeout: int = 120,
    retries: int = 4,
    allow_insecure_ssl_fallback: bool = True,
) -> tuple[list[FloatRecord], str, int]:
    ssl_context = make_ssl_context(verify_ssl=True)
    index_bytes = http_download_bytes(
        index_url,
        timeout=timeout,
        retries=retries,
        ssl_context=ssl_context,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
    )
    index_text = index_bytes.decode("utf-8", errors="replace")
    records = parse_synthetic_index(index_text, only_vars=None)
    return records, index_text, len(index_bytes)


def record_to_row(record: FloatRecord, base_url: str = DEFAULT_BASE_URL) -> dict[str, str | int | float | None]:
    base_url = base_url.rstrip("/") + "/"
    variables = split_variables(record.parameters)
    return {
        "dac": record.dac,
        "wmo": record.wmo,
        "sprof_url": urljoin(base_url, record.relpath),
        "local_filename": record.filename,
        "parameters_from_index": record.parameters,
        "variables": ", ".join(variables),
        "n_variables": len(variables),
        "date": record.date,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "ocean": record.ocean,
        "profiler_type": record.profiler_type,
        "institution": record.institution,
        "date_update": record.date_update,
        "parameter_data_mode": record.parameter_data_mode,
    }


def records_to_rows(records: Iterable[FloatRecord], base_url: str = DEFAULT_BASE_URL) -> list[dict[str, str | int | float | None]]:
    return [record_to_row(record, base_url=base_url) for record in records]


def write_inventory(records: Iterable[FloatRecord], out_csv: Path, base_url: str = DEFAULT_BASE_URL) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = records_to_rows(records, base_url=base_url)
    fieldnames = [
        "dac",
        "wmo",
        "sprof_url",
        "local_filename",
        "parameters_from_index",
        "variables",
        "n_variables",
        "date",
        "latitude",
        "longitude",
        "ocean",
        "profiler_type",
        "institution",
        "date_update",
        "parameter_data_mode",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def download_record(
    record: FloatRecord,
    output_dir: Path,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 120,
    retries: int = 4,
    force: bool = False,
    allow_insecure_ssl_fallback: bool = True,
) -> DownloadResult:
    ssl_context = make_ssl_context(verify_ssl=True)
    url = urljoin(base_url.rstrip("/") + "/", record.relpath)
    downloaded, status = download_file_atomic(
        url=url,
        outfile=output_dir / record.filename,
        timeout=timeout,
        retries=retries,
        force=force,
        ssl_context=ssl_context,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
    )
    return DownloadResult(
        dac=record.dac,
        wmo=record.wmo,
        filename=record.filename,
        downloaded=downloaded,
        status=status,
    )


def remote_file_size(
    url: str,
    timeout: int = 120,
    allow_insecure_ssl_fallback: bool = True,
) -> tuple[int | None, str]:
    contexts = [make_ssl_context(verify_ssl=True)]
    if allow_insecure_ssl_fallback:
        contexts.append(make_ssl_context(verify_ssl=False))

    last_error: Exception | None = None
    req = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    for context in contexts:
        try:
            with urlopen(req, timeout=timeout, context=context) as response:
                length = response.headers.get("Content-Length")
                return (int(length), "ok") if length else (None, "no_content_length")
        except HTTPError as exc:
            if exc.code == 404:
                return None, "404"
            last_error = exc
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc

    return None, f"failed: {last_error}"


def probe_url(
    url: str,
    timeout: int = 30,
    allow_insecure_ssl_fallback: bool = True,
) -> dict[str, str | int | float | bool | None]:
    contexts: list[tuple[str, ssl.SSLContext | None]] = [("verified", make_ssl_context(verify_ssl=True))]
    if allow_insecure_ssl_fallback:
        contexts.append(("insecure", make_ssl_context(verify_ssl=False)))

    last_error: Exception | None = None
    for mode, context in contexts:
        start = time.perf_counter()
        try:
            req = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout, context=context) as response:
                elapsed = time.perf_counter() - start
                return {
                    "ok": True,
                    "mode": mode,
                    "status": response.status,
                    "elapsed_seconds": round(elapsed, 2),
                    "content_length": int(response.headers["Content-Length"]) if response.headers.get("Content-Length") else None,
                    "error": "",
                }
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if mode == "verified" and allow_insecure_ssl_fallback and is_certificate_verify_error(exc):
                continue
            break

    return {
        "ok": False,
        "mode": "",
        "status": None,
        "elapsed_seconds": None,
        "content_length": None,
        "error": str(last_error),
    }


def package_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not installed"


def runtime_report() -> list[dict[str, str]]:
    packages = ["argo-sprof-manager", "streamlit", "pandas", "numpy", "certifi"]
    rows = [
        {"item": "python", "value": sys.version.replace("\n", " ")},
        {"item": "executable", "value": sys.executable},
    ]
    rows.extend({"item": package, "value": package_version(package)} for package in packages)
    return rows


def inspect_netcdf_file(path: Path) -> dict[str, str | int | float | None]:
    if not path.exists():
        return {"ok": "false", "error": "file_not_found"}

    info: dict[str, str | int | float | None] = {
        "ok": "true",
        "file": str(path),
        "size_bytes": path.stat().st_size,
        "path_is_ascii": str(path_is_ascii(path)).lower(),
        "opened_via_temp_ascii_copy": "false",
    }

    try:
        import xarray as xr  # type: ignore
    except ImportError:
        info["ok"] = "false"
        info["error"] = "xarray_not_installed"
        return info

    def read_dataset(dataset_path: Path) -> dict[str, str | int]:
        with xr.open_dataset(dataset_path, decode_times=False) as dataset:
            return {
                "dimensions": ", ".join(f"{key}={value}" for key, value in dataset.sizes.items()),
                "variables": ", ".join(sorted(dataset.variables)),
                "n_variables": len(dataset.variables),
                "coordinates": ", ".join(sorted(dataset.coords)),
            }

    try:
        info.update(read_dataset(path))
    except Exception as exc:
        direct_error = str(exc)
        if path_is_ascii(path):
            info["ok"] = "false"
            info["error"] = direct_error
            return info

        temp_path = ascii_preview_copy_path(path)
        try:
            shutil.copy2(path, temp_path)
            info.update(read_dataset(temp_path))
            info["opened_via_temp_ascii_copy"] = "true"
            info["temp_ascii_copy"] = str(temp_path)
            info["direct_open_error"] = direct_error
        except Exception as fallback_exc:
            info["ok"] = "false"
            info["error"] = str(fallback_exc)
            info["direct_open_error"] = direct_error
            info["temp_ascii_copy"] = str(temp_path)

    return info


def path_is_ascii(path: Path) -> bool:
    try:
        str(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def ascii_preview_copy_path(path: Path) -> Path:
    preview_dir = Path(tempfile.gettempdir()) / "argo_sprof_manager_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    ascii_name = path.name.encode("ascii", errors="ignore").decode("ascii").strip("._ ")
    if not ascii_name:
        ascii_name = f"preview_{abs(hash(str(path)))}.nc"
    return preview_dir / ascii_name


def preview_cache_dir() -> Path:
    return Path(tempfile.gettempdir()) / "argo_sprof_manager_preview"


def classify_download_status(status: str) -> str:
    text = str(status).lower()
    if text in SUCCESS_STATUSES:
        return "success"
    if text == "pending":
        return "pending"
    if text == "canceled":
        return "canceled"
    if text == "404" or "not found" in text:
        return "not_found"
    if text == "too_small" or "too small" in text:
        return "too_small"
    if "certificate" in text or "ssl" in text:
        return "ssl"
    if "timed out" in text or "timeout" in text or "urlopen" in text or "connection" in text:
        return "network"
    if "permission" in text or "access is denied" in text:
        return "permission"
    if "no space" in text or "disk" in text:
        return "disk"
    if text.startswith("failed") or text.startswith("error"):
        return "error"
    return "other"


def directory_health(output_dir: Path | None, min_bytes: int = 1024) -> dict[str, str | int | bool | None]:
    if output_dir is None:
        return {
            "selected": False,
            "path": "",
            "exists": False,
            "writable": False,
            "path_is_ascii": None,
            "free_bytes": None,
            "part_files": 0,
            "small_sprof_files": 0,
            "preview_cache_files": 0,
            "warning": "no_output_dir",
        }

    writable = False
    warning = ""

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / ".argo_sprof_write_test.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        writable = True
    except OSError as exc:
        warning = f"not_writable: {exc}"

    exists = output_dir.exists()
    part_files = len(list(output_dir.glob("*.part"))) if output_dir.exists() else 0
    small_sprof_files = 0
    if output_dir.exists():
        small_sprof_files = sum(1 for path in output_dir.glob("*_Sprof.nc") if path.stat().st_size < min_bytes)

    preview_dir = preview_cache_dir()
    preview_cache_files = len(list(preview_dir.glob("*"))) if preview_dir.exists() else 0

    free_bytes: int | None = None
    try:
        free_bytes = shutil.disk_usage(output_dir).free
    except OSError:
        free_bytes = None

    if not warning and not path_is_ascii(output_dir):
        warning = "non_ascii_path"

    return {
        "selected": True,
        "path": str(output_dir),
        "exists": exists,
        "writable": writable,
        "path_is_ascii": path_is_ascii(output_dir),
        "free_bytes": free_bytes,
        "part_files": part_files,
        "small_sprof_files": small_sprof_files,
        "preview_cache_files": preview_cache_files,
        "warning": warning,
    }


def cleanup_part_files(output_dir: Path) -> dict[str, int]:
    removed = 0
    bytes_removed = 0
    for path in output_dir.glob("*.part"):
        if path.is_file():
            bytes_removed += path.stat().st_size
            path.unlink()
            removed += 1
    return {"removed": removed, "bytes_removed": bytes_removed}


def cleanup_small_sprof_files(output_dir: Path, min_bytes: int = 1024) -> dict[str, int]:
    removed = 0
    bytes_removed = 0
    for path in output_dir.glob("*_Sprof.nc"):
        if path.is_file() and path.stat().st_size < min_bytes:
            bytes_removed += path.stat().st_size
            path.unlink()
            removed += 1
    return {"removed": removed, "bytes_removed": bytes_removed}


def cleanup_preview_cache() -> dict[str, int]:
    cache_dir = preview_cache_dir()
    removed = 0
    bytes_removed = 0
    if not cache_dir.exists():
        return {"removed": 0, "bytes_removed": 0}
    for path in cache_dir.glob("*"):
        if path.is_file():
            bytes_removed += path.stat().st_size
            path.unlink()
            removed += 1
    return {"removed": removed, "bytes_removed": bytes_removed}


def read_download_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def unfinished_manifest_keys(rows: Iterable[dict[str, str]]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for row in rows:
        status = str(row.get("status", "")).strip()
        if classify_download_status(status) != "success":
            dac = str(row.get("dac", "")).strip()
            wmo = str(row.get("wmo", "")).strip()
            if dac and wmo:
                keys.add((dac, wmo))
    return keys
