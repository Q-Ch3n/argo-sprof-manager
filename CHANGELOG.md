# Changelog

## 1.0.0

Initial public release.

- Added a Streamlit web interface for browsing the latest Argo synthetic-profile index.
- Added filtering by DAC, WMO list, variables, text query, and variable match mode.
- Added single-float, filtered-batch, and full-inventory Sprof download workflows.
- Added background download jobs with pause, resume, cancel, retry, and manifest recovery.
- Added background remote-size estimation with all rows, first N rows, and random sample N rows.
- Added output directory diagnostics, cleanup tools, network diagnostics, and optional NetCDF preview.
- Added Windows non-ASCII path fallback for NetCDF preview.
- Added CLI entry points: `argo-sprof-manager`, `argo-sprof-web`, and `python -m argo_sprof_manager`.
- Added release checks, live Argo GDAC network checks, and local automated tests for release validation.
- Added Argo data acknowledgement and citation guidance.
