# Argo Sprof Download Manager

A local Streamlit web app for browsing the latest Argo synthetic-profile index and downloading float-level `*_Sprof.nc` files.

This is an unofficial helper tool. Data are downloaded from the Argo GDAC index and DAC file tree.

## Screenshot

![Argo Sprof Download Manager interface](argoSprof.png)

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
      package-smoke-check.yml
  .gitignore
  CITATION.cff
  CHANGELOG.md
  environment.yml
  pyproject.toml
  requirements.txt
  argoSprof.png
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

## Repository

Source code and issue tracking are available at `https://github.com/cq20180725/argo-sprof-manager`.

The repository is intended to contain application source code, packaging metadata, documentation, and utility scripts. Downloaded Argo data files, logs, cache files, and output directories are ignored by Git.

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

## Validation

Run the package validation check:

```powershell
cd "C:\path\to\argo-sprof-manager"
python scripts\release_check.py
```

The release check compiles the package, builds a wheel, installs the wheel into a temporary virtual environment, runs `pip check`, checks the CLI entry point, starts the web app, and verifies that the local HTTP page responds.

Run a basic syntax check manually:

```powershell
python -m compileall -q src scripts
```

To reuse the active Python environment packages during validation:

```powershell
python scripts\release_check.py --use-system-site-packages
```

To verify live connectivity to the Argo GDAC service:

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

## Feature History

This section summarizes major capabilities.

See `CHANGELOG.md` for release notes.

### Downloader Core

- Fetches the latest `argo_synthetic-profile_index.txt` from Argo GDAC.
- Parses the synthetic-profile index into a float-level inventory.
- Downloads `*_Sprof.nc` files with retry logic and partial-file cleanup.
- Supports certificate fallback for proxy or local certificate environments when needed.

### Web Interface

- Provides a local Streamlit interface named `Argo Sprof Download Manager`.
- Refreshes the latest remote index from the app.
- Filters inventory rows by DAC, WMO list, variables, text query, and variable matching mode.
- Supports single-float, filtered-result, and full-inventory download actions.
- Shows a map preview when latitude and longitude are available in the index.
- Lets users choose the download directory explicitly.

### Packaging and Distribution

- Uses a standard Python `src/` package layout.
- Defines package metadata and dependencies in `pyproject.toml`.
- Provides CLI entry points: `argo-sprof-manager`, `argo-sprof-web`, and `python -m argo_sprof_manager`.
- Includes `requirements.txt`, `environment.yml`, `LICENSE`, `CHANGELOG.md`, and `CITATION.cff`.
- Includes GitHub Actions package smoke checks for Python 3.10 and 3.11.

### Download Task Management

- Runs long batch downloads through a background job manager.
- Provides pause, resume, and cancel controls for long downloads.
- Shows active job status, progress, submitted/completed counters, and recent log lines.
- Writes `download_manifest.csv` during the task.
- Supports retrying failed or incomplete items and resuming unfinished manifest entries.

### Diagnostics and Cleanup

- Shows runtime diagnostics for Python, package versions, and executable path.
- Tests network access to the index URL.
- Checks output directory health, including write access, free space, non-ASCII path warnings, partial files, and too-small Sprof files.
- Cleans `.part` files, too-small Sprof files, and NetCDF preview cache files.
- Classifies failure categories for easier troubleshooting.

### Background Remote-Size Estimation

- Runs remote total-size estimation in a background task.
- Keeps other tabs usable while estimation is running.
- Provides cancel and clear controls for remote-size estimates.
- Supports three estimate scopes: all filtered rows, first N rows, and random sample N rows.
- Projects full totals from successful random-sample responses.
- Keeps per-file failures in the result table instead of failing the whole estimate.

### Windows Path Stability

- Improves local NetCDF preview behavior on Windows paths containing Chinese or other non-ASCII characters.
- Copies files to a temporary ASCII-only preview path when the NetCDF backend cannot open the original path.
- Recommends ASCII-only output directories for large-scale work.

### Stability and Usability

- Shows progress feedback while estimating remote total size for the current filtered result.
- Continues remote-size estimation when individual file probes fail.
- Returns stable table columns for empty remote-size estimates.
- Handles old or malformed result tables when detecting retry candidates.
- Validates `Content-Length` during downloads, retries incomplete transfers, and removes partial files.
- Provides package smoke checks and live Argo GDAC connectivity checks.

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
