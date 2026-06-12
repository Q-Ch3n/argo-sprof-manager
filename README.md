# Argo Sprof Download Manager

A local Streamlit web app for browsing the latest Argo synthetic-profile index and downloading float-level `*_Sprof.nc` files.

This is an unofficial helper tool. Data are downloaded from the Argo GDAC index and DAC file tree.

## Features

- Refresh the latest `argo_synthetic-profile_index.txt` from Argo GDAC
- Browse float-level Sprof inventory
- Filter by DAC, WMO list, variables, text query, and variable matching mode
- Preview available float positions on a map when latitude/longitude are present in the index
- Download one float, the current filtered result, or the full latest inventory
- Pause, resume, or cancel long batch downloads
- Save download manifests and retry failed / incomplete items
- Resume unfinished items from `download_manifest.csv`
- Check output directory health, including write access, free space, non-ASCII paths, partial files, and too-small files
- Clean `.part` files, too-small Sprof files, and NetCDF preview cache
- Classify download failures into success, pending, canceled, network, SSL, 404, permission, disk, and other categories
- Estimate remote file sizes in the background, with full, first-N, and random-sample modes
- Run environment and network diagnostics
- Optional local NetCDF preview for downloaded `*_Sprof.nc` files
- English / Chinese interface switch, with English as the default language

## 中文说明

这是一个本地运行的 Argo Sprof 图形化下载管理器。它可以刷新最新 Argo synthetic-profile index，查询浮标清单，按变量/WMO/DAC 筛选，并下载单个、筛选结果或全部浮标级 `*_Sprof.nc` 文件。

界面默认英文，可在左侧切换为中文。

## Project Layout

```text
argo-sprof-manager/
  .github/
    workflows/
      tests.yml
  .gitignore
  CITATION.cff
  CHANGELOG.md
  environment.yml
  pyproject.toml
  requirements.txt
  README.md
  scripts/
    live_network_check.py
    release_check.py
  src/
    argo_sprof_manager/
      __init__.py
      __main__.py
      cli.py
      argo_sprof_core.py
      argo_streamlit_app.py
      download_jobs.py
      size_estimate_jobs.py
```

Current version: `1.0.0`.

## Recommended Conda Install

On a new computer, create a clean environment instead of copying old `site-packages` folders.

```powershell
cd "C:\path\to\argo-sprof-manager"
conda env create -f environment.yml
conda activate argo_sprof
```

Start the app:

```powershell
argo-sprof-manager
```

## Editable Pip Install

```powershell
cd "C:\path\to\argo-sprof-manager"
pip install -e .
```

Start with either command:

```powershell
argo-sprof-manager
argo-sprof-web
python -m argo_sprof_manager
```

Use a custom port:

```powershell
argo-sprof-manager --port 8502
```

If the requested port is already busy, the CLI automatically switches to the next available port.

## GitHub Repository Setup

Use this directory as the repository root. Do not publish a parent research workspace that contains raw data, downloaded NetCDF files, logs, or unrelated scripts.

Repository metadata is set for `https://github.com/cq20180725/argo-sprof-manager`.

## Dependencies

Core dependencies:

```text
streamlit>=1.58
pandas>=2.0
certifi
```

Optional NetCDF preview dependencies:

```powershell
pip install -e ".[preview]"
```

## Tests

The public repository does not include the local test-program folder. Before publishing, validate the project from a working copy that still contains the local tests.

Run the full release check before publishing or moving the package to another computer:

```powershell
cd "C:\path\to\argo-sprof-manager"
python scripts\release_check.py
```

When a local `tests/` directory exists, `release_check.py` also runs the pytest suite. When `tests/` is absent, it skips pytest and still compiles the package, builds a wheel, installs the wheel into a temporary virtual environment, runs `pip check` in that clean environment, checks the CLI entry point, starts the web app, and verifies the local HTTP page responds.

Run a basic syntax check manually:

```powershell
python -m compileall -q src scripts
```

The local validation suite covers:

- synthetic-profile index parsing and inventory generation
- mocked network and HTTP boundary behavior, including SSL fallback, 404, missing content length, incomplete reads, and partial-file cleanup
- Windows non-ASCII path handling for local NetCDF preview
- output directory health checks and cleanup helpers
- manifest reading and unfinished-download detection
- pause, resume, cancel, and manifest writing for background downloads
- background remote-size estimates, cancellation, sample projection, and per-file failures
- CLI port handling
- WMO parsing, inventory filtering, retry/resume candidate selection
- remote-size estimate mode selection: all rows, first N rows, and random sample N rows
- Streamlit page initialization, language switching, size-estimate controls, and completed estimate result panel rendering
- large synthetic inventory filtering and estimate-row selection

For a faster local-only release check that reuses the current environment packages:

```powershell
python scripts\release_check.py --use-system-site-packages
```

Live network checks against the real Argo GDAC service should be run manually before an important release, because they depend on proxy settings, network state, and remote server availability:

```powershell
python scripts\live_network_check.py
```

This checks the real synthetic-profile index URL with verified SSL first and reports the remote `Content-Length` when available.

## Data Acknowledgement

This project is not an official Argo product. It is only a local helper for browsing the Argo synthetic-profile index and downloading Argo Sprof files from GDAC mirrors.

If you use Argo data in publications, products, or reports, acknowledge Argo according to the official guidance: https://argo.ucsd.edu/data/acknowledging-argo/

Suggested acknowledgement:

```text
These data were collected and made freely available by the International Argo Program and the national programs that contribute to it. (https://argo.ucsd.edu, https://www.ocean-ops.org). The Argo Program is part of the Global Ocean Observing System.
```

General Argo dataset citation:

```text
Argo (2000). Argo float data and metadata from Global Data Assembly Centre (Argo GDAC). SEANOE. https://doi.org/10.17882/42182
```

For reproducible publications, use the specific monthly Argo snapshot DOI when appropriate, as described by the official Argo acknowledgement page.

## Version Iteration History

This section records the functional evolution of the tool. It is organized by iteration stage.

See `CHANGELOG.md` for release notes.

### Script Prototype

- Started from a command-line Python downloader for global Argo Sprof files.
- Downloaded the latest `argo_synthetic-profile_index.txt` from Argo GDAC.
- Parsed the synthetic-profile index and generated a float-level inventory.
- Downloaded `*_Sprof.nc` files into a local output directory.
- Added retry logic and SSL certificate fallback for proxy or local certificate environments.

### Streamlit Web Prototype

- Added a local Streamlit interface for browsing Argo Sprof inventory data.
- Added filters for DAC, WMO, variables, text search, and variable match mode.
- Added single-float download, filtered-result download, and full-inventory download actions.
- Added map preview when latitude and longitude are available in the index.
- Changed the app to refresh the latest remote index instead of relying on old local inventory files.

### All-Variable Download Manager

- Renamed the interface to `Argo Sprof Download Manager`.
- Changed the app from BGC-only thinking to all available Sprof variables.
- Added variable selection based on the latest index contents.
- Kept the output directory empty on app startup so users explicitly choose where files are saved.
- Added a refresh hint so users know loading the full remote index can take time.

### Package Structure

- Converted `web_code` into a standard Python package with a `src/` layout.
- Added `pyproject.toml` with package metadata and dependencies.
- Added CLI entry points: `argo-sprof-manager` and `argo-sprof-web`.
- Added `python -m argo_sprof_manager` support.
- Added `requirements.txt`, `environment.yml`, and `LICENSE`.
- Removed low-value compatibility wrapper files from the project root.

### Download Task Management

- Moved long batch downloads into a background job manager.
- Added pause, resume, and cancel controls for long downloads.
- Added active job status, progress, submitted/completed counters, and recent log lines.
- Added `download_manifest.csv` writing during the task, not only after completion.
- Added retry failed / incomplete items.
- Added resume unfinished items from an existing manifest.

### Diagnostics and Cleanup

- Added runtime diagnostics for Python, package versions, and executable path.
- Added network connection testing for the index URL.
- Added output directory health checks: write access, free space, non-ASCII path warning, partial files, and too-small Sprof files.
- Added cleanup actions for `.part` files, too-small Sprof files, and NetCDF preview cache.
- Added failure category classification for easier troubleshooting.

### Background Remote-Size Estimation

- Moved remote total-size estimation out of the synchronous Streamlit page run and into a background task.
- Added a local-refresh estimate panel using Streamlit fragments, so other tabs remain usable while estimation is running.
- Added cancel and clear controls for remote-size estimates.
- Added three estimate scopes: all filtered rows, first N rows, and random sample N rows.
- Added sample-based projected full total using successful sample responses.
- Kept per-file failures in the result table instead of failing the whole estimate.

### Windows Path Stability

- Improved local NetCDF preview behavior on Windows paths containing Chinese or other non-ASCII characters.
- Added a fallback that copies files to a temporary ASCII-only preview path when the NetCDF backend cannot open the original path.
- Added README troubleshooting guidance recommending ASCII-only output directories for large-scale work.

### Stability and Usability Hardening

- Added progress feedback while estimating remote total size for the current filtered result.
- Made remote-size estimation continue even if one file probe fails.
- Made empty remote-size estimation return stable table columns.
- Made retry-candidate detection tolerant of old or malformed result tables.
- Added `Content-Length` validation to file downloads, so incomplete network transfers are retried and partial files are removed.
- Expanded local tests for app helper functions, filtering, manifest resume logic, background download jobs, background size-estimate jobs, mocked network failures, large synthetic inventories, and Streamlit rendering.
- Added a release-check script that builds a wheel, installs it into a temporary virtual environment, verifies CLI entry points, and starts the web app for an HTTP smoke test.
- Added a live-network check script for manual Argo GDAC connectivity checks before important releases.
- Verified package entry points, editable package metadata, wheel build, isolated wheel install, Streamlit page initialization, and real local HTTP startup.

## Troubleshooting

### `ImportError: numpy.core.multiarray failed to import`

This usually means NumPy and pandas binary packages are incompatible in the current environment. Create a clean Conda environment with `environment.yml`, or reinstall NumPy/pandas in the active environment.

### Network or SSL errors

Open the app, go to the `Diagnostics` tab, and run `Test index connection`. If a proxy or local certificate tool is used, keep `Allow insecure SSL fallback after certificate failure` enabled only when necessary.

### Windows paths with Chinese characters

Some NetCDF backends on Windows have trouble opening files from non-ASCII paths. The local NetCDF preview tool first tries the original path. If that fails and the path contains non-ASCII characters, it copies the file to a temporary ASCII-only path and tries again.

For large-scale work, an ASCII-only download directory is still recommended, for example:

```text
E:\Argo_Sprof
```

### Large downloads

Full global Sprof downloads can be large and slow. Use filters, estimate remote size first, and rely on the generated `download_manifest.csv` to retry failed items.
