from __future__ import annotations

import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from argo_sprof_manager import argo_sprof_core as core
from argo_sprof_manager import download_jobs
from argo_sprof_manager import size_estimate_jobs


TEXT = {
    "en": {
        "page_title": "Argo Sprof Download Manager",
        "caption": "Browse the latest Argo synthetic-profile index and manage float-level Sprof downloads locally.",
        "language": "Language / 语言",
        "data_source": "Data source",
        "index_url": "Synthetic-profile index URL",
        "base_url": "GDAC DAC base URL",
        "output_dir": "Download output directory",
        "output_placeholder": r"Example: E:\Argo_Sprof",
        "network_download": "Network and download",
        "timeout": "Timeout seconds",
        "retries": "Retries",
        "workers": "Parallel workers",
        "force": "Force re-download existing files",
        "ssl_fallback": "Allow insecure SSL fallback after certificate failure",
        "save_latest": "Save latest index and full inventory after refresh",
        "refresh_hint": "Refreshing the full index usually takes about 1 minute. Please wait for the progress message.",
        "refresh": "Refresh latest Argo index",
        "refreshing": "Downloading and parsing the latest Argo GDAC index...",
        "refresh_ok": "Latest index loaded.",
        "refresh_fail": "Refresh failed: {error}",
        "need_output": "Please set a download output directory, or disable saving the full index.",
        "tabs_inventory": "Inventory",
        "tabs_download": "Downloads",
        "tabs_diagnostics": "Diagnostics",
        "empty_inventory": "Click \"Refresh latest Argo index\" in the sidebar to load the latest inventory.",
        "filters": "Filters",
        "dac": "DAC",
        "variables": "Variables",
        "match": "Variable match",
        "match_any": "Any selected variable",
        "match_all": "All selected variables",
        "search": "Search WMO / DAC / variables",
        "wmo_batch": "WMO batch filter",
        "wmo_batch_help": "Paste WMO IDs separated by spaces, commas, or new lines.",
        "wmo_upload": "Upload WMO list",
        "wmo_only": "Apply WMO batch filter",
        "index_floats": "Index floats",
        "filtered": "Filtered",
        "downloaded": "Downloaded",
        "local_size": "Local size",
        "index_size": "Index size",
        "last_refresh": "Last refresh: {time}",
        "map": "Map preview",
        "map_empty": "No latitude/longitude information is available for the current selection.",
        "inventory_table": "Inventory table",
        "export_csv": "Export filtered CSV",
        "download_actions": "Download actions",
        "output_required": "Set the download output directory in the sidebar first.",
        "empty_filter": "The current filter result is empty.",
        "single": "Single float",
        "select_float": "Select from filtered results",
        "download_selected": "Download selected float",
        "downloading_one": "Downloading {dac} / {wmo}...",
        "batch": "Filtered batch",
        "max_items": "Maximum items, 0 means all filtered rows",
        "confirm_batch": "Confirm filtered batch download",
        "start_batch": "Start filtered download",
        "all": "All latest inventory",
        "all_hint": "This will try to download all {count} float-level Sprof files.",
        "confirm_all": "I confirm downloading the full latest inventory",
        "start_all": "Download all",
        "active_job": "Active download task",
        "job_status": "Status",
        "job_progress": "Progress",
        "job_submitted": "Submitted",
        "job_completed": "Completed",
        "pause_download": "Pause",
        "resume_download": "Resume",
        "cancel_download": "Cancel",
        "clear_job": "Clear completed task",
        "pause_note": "Pause and cancel stop new downloads. Files already in progress may finish.",
        "job_started": "Download task started.",
        "job_paused": "Download task paused.",
        "job_resumed": "Download task resumed.",
        "job_canceled": "Cancel requested.",
        "status_queued": "Queued",
        "status_running": "Running",
        "status_paused": "Paused",
        "status_cancel_requested": "Cancel requested",
        "status_canceled": "Canceled",
        "status_completed": "Completed",
        "status_failed": "Failed",
        "retry_failed": "Retry failed items",
        "retry_failed_button": "Retry failed / incomplete items",
        "no_failed": "No failed items are available from the last result.",
        "prepare_download": "Preparing download...",
        "download_progress": "Download progress {done}/{total}",
        "download_done": "Download task completed.",
        "manifest_saved": "Download manifest saved: {path}",
        "tools": "Tools",
        "estimate_size": "Estimate remote total size",
        "estimate_scope": "Estimate scope",
        "estimate_mode_full": "All filtered rows",
        "estimate_mode_first_n": "First N rows",
        "estimate_mode_sample_n": "Random sample N rows",
        "estimate_item_count": "N for limited / sample estimate",
        "estimate_selected_hint": "This estimate will probe {selected} of {total} filtered rows.",
        "estimate_full_warning": "Full remote-size estimates for {count} rows can take a long time. Limited or sample mode is often better for a quick check.",
        "start_estimate": "Start size estimate",
        "active_estimate": "Active size estimate task",
        "estimate_active_note": "Remote-size estimates run in the background. Other tabs remain usable while this task is running.",
        "cancel_estimate": "Cancel estimate",
        "clear_estimate": "Clear estimate task",
        "estimate_started": "Size estimate task started.",
        "estimate_canceled": "Cancel requested.",
        "estimate_measured_total": "Measured total",
        "estimate_projected_total": "Projected full total",
        "estimate_source_rows": "Filtered rows",
        "estimate_selected_rows": "Estimated rows",
        "last_estimate_results": "Size estimate results",
        "sample_projection_note": "Sample projection uses the average size from successful sample responses.",
        "estimate_progress": "Estimating remote sizes {done}/{total}",
        "estimate_done": "Remote size estimate completed.",
        "remote_total": "Remote total size",
        "size_success": "Files with size response",
        "save_filtered": "Save filtered inventory to output directory",
        "saved": "Saved: {path}",
        "last_results": "Last download results",
        "status_counts": "Status counts",
        "diagnostics": "Environment diagnostics",
        "runtime": "Runtime",
        "network_test": "Network test",
        "run_network_test": "Test index connection",
        "network_ok": "Connection OK",
        "network_fail": "Connection failed",
        "netcdf_preview": "Local NetCDF preview",
        "select_netcdf": "Select a downloaded NetCDF file",
        "inspect_file": "Inspect file",
        "no_netcdf": "No .nc files found in the output directory.",
        "xarray_missing": "Install optional dependencies to preview NetCDF content: pip install \"argo-sprof-manager[preview]\"",
        "no_output_for_preview": "Set an output directory to preview downloaded NetCDF files.",
        "non_ascii_path_hint": "This file path contains non-ASCII characters. If direct NetCDF opening fails on Windows, the app will try a temporary ASCII-only copy.",
        "temp_ascii_opened": "Direct opening failed, but the file was opened successfully from a temporary ASCII-only copy.",
        "output_health": "Output directory health",
        "health_selected": "Directory selected",
        "health_exists": "Directory exists",
        "health_writable": "Writable",
        "health_ascii_path": "ASCII-only path",
        "health_free_space": "Free space",
        "health_part_files": ".part files",
        "health_small_files": "Too-small Sprof files",
        "health_preview_cache": "Preview cache files",
        "health_warning": "Warning",
        "warning_ok": "OK",
        "warning_no_output_dir": "No output directory selected.",
        "warning_non_ascii_path": "Non-ASCII path. The app can handle many cases, but ASCII-only paths are more stable on Windows.",
        "warning_not_writable": "The selected directory is not writable.",
        "cleanup_tools": "Cleanup tools",
        "cleanup_part": "Delete .part files",
        "cleanup_small": "Delete too-small Sprof files",
        "cleanup_preview": "Clear NetCDF preview cache",
        "cleanup_result": "Removed {count} files, freed {size}.",
        "resume_manifest": "Resume from manifest",
        "resume_hint": "Use download_manifest.csv in the output directory to continue pending, canceled, or failed items.",
        "resume_unfinished": "Resume unfinished manifest items",
        "no_manifest": "No download_manifest.csv was found in the output directory.",
        "no_unfinished": "No unfinished manifest items match the current inventory.",
        "unfinished_count": "Unfinished items found: {count}",
        "failure_category": "Failure category",
        "no_data": "No data",
        "local_missing": "Missing",
        "local_downloaded": "Downloaded",
        "local_too_small": "Too small",
        "local_no_dir": "No output dir",
    },
    "zh": {
        "page_title": "Argo Sprof 下载管理器",
        "caption": "从 Argo GDAC 获取最新 synthetic-profile index，并在本地管理浮标级 Sprof 文件下载。",
        "language": "Language / 语言",
        "data_source": "数据源",
        "index_url": "Synthetic-profile index URL",
        "base_url": "GDAC DAC base URL",
        "output_dir": "下载输出目录",
        "output_placeholder": r"例如 E:\Argo_Sprof",
        "network_download": "网络与下载",
        "timeout": "超时秒数",
        "retries": "重试次数",
        "workers": "并发下载数",
        "force": "强制重新下载已存在文件",
        "ssl_fallback": "证书失败时允许自动降级",
        "save_latest": "刷新后保存最新索引和完整清单",
        "refresh_hint": "刷新完整索引通常需要约 1 分钟；索引文件较大，请等待进度提示。",
        "refresh": "刷新最新 Argo 索引",
        "refreshing": "正在从 Argo GDAC 下载并解析最新索引...",
        "refresh_ok": "最新索引已加载。",
        "refresh_fail": "刷新失败：{error}",
        "need_output": "请先填写下载输出目录，或取消保存完整索引。",
        "tabs_inventory": "清单",
        "tabs_download": "下载",
        "tabs_diagnostics": "诊断",
        "empty_inventory": "请先点击左侧“刷新最新 Argo 索引”加载最新清单。",
        "filters": "筛选",
        "dac": "DAC",
        "variables": "变量",
        "match": "变量匹配",
        "match_any": "包含任一变量",
        "match_all": "同时包含全部变量",
        "search": "搜索 WMO / DAC / 变量",
        "wmo_batch": "WMO 批量筛选",
        "wmo_batch_help": "可粘贴 WMO 编号，用空格、逗号或换行分隔。",
        "wmo_upload": "上传 WMO 列表",
        "wmo_only": "应用 WMO 批量筛选",
        "index_floats": "索引浮标数",
        "filtered": "当前筛选数",
        "downloaded": "已下载",
        "local_size": "本地大小",
        "index_size": "索引大小",
        "last_refresh": "最近刷新时间：{time}",
        "map": "地图预览",
        "map_empty": "当前筛选结果没有可用经纬度信息。",
        "inventory_table": "清单表",
        "export_csv": "导出当前筛选表 CSV",
        "download_actions": "下载操作",
        "output_required": "请先在左侧填写下载输出目录。",
        "empty_filter": "当前筛选结果为空。",
        "single": "单个浮标",
        "select_float": "从当前筛选结果中选择",
        "download_selected": "下载选中浮标",
        "downloading_one": "正在下载 {dac} / {wmo}...",
        "batch": "当前筛选结果",
        "max_items": "最多下载数量，0 表示全部筛选结果",
        "confirm_batch": "确认下载当前筛选结果",
        "start_batch": "开始下载筛选结果",
        "all": "全部最新清单",
        "all_hint": "将尝试下载全部 {count} 个浮标级 Sprof 文件。",
        "confirm_all": "我确认下载全部最新清单",
        "start_all": "一键下载全部",
        "active_job": "当前下载任务",
        "job_status": "状态",
        "job_progress": "进度",
        "job_submitted": "已提交",
        "job_completed": "已完成",
        "pause_download": "暂停",
        "resume_download": "继续",
        "cancel_download": "取消",
        "clear_job": "清除已结束任务",
        "pause_note": "暂停和取消会阻止新的下载；已经开始下载的文件可能会完成。",
        "job_started": "下载任务已启动。",
        "job_paused": "下载任务已暂停。",
        "job_resumed": "下载任务已继续。",
        "job_canceled": "已请求取消任务。",
        "status_queued": "排队中",
        "status_running": "运行中",
        "status_paused": "已暂停",
        "status_cancel_requested": "请求取消",
        "status_canceled": "已取消",
        "status_completed": "已完成",
        "status_failed": "失败",
        "retry_failed": "失败项重试",
        "retry_failed_button": "重试失败 / 未完成项目",
        "no_failed": "最近一次结果中没有可重试的失败项目。",
        "prepare_download": "准备下载...",
        "download_progress": "下载进度 {done}/{total}",
        "download_done": "下载任务完成。",
        "manifest_saved": "下载清单已保存：{path}",
        "tools": "辅助工具",
        "estimate_size": "估算当前筛选结果远程总大小",
        "estimate_scope": "估算范围",
        "estimate_mode_full": "全部筛选结果",
        "estimate_mode_first_n": "前 N 个文件",
        "estimate_mode_sample_n": "随机抽样 N 个文件",
        "estimate_item_count": "限制 / 抽样估算的 N",
        "estimate_selected_hint": "本次将探测当前 {total} 条筛选结果中的 {selected} 条。",
        "estimate_full_warning": "对 {count} 条记录做全量远程大小估算可能耗时较长。快速判断时建议使用前 N 个或随机抽样模式。",
        "start_estimate": "开始估算",
        "active_estimate": "当前大小估算任务",
        "estimate_active_note": "远程大小估算会在后台运行；任务进行时，其他选项卡仍可使用。",
        "cancel_estimate": "取消估算",
        "clear_estimate": "清除估算任务",
        "estimate_started": "大小估算任务已启动。",
        "estimate_canceled": "已请求取消估算。",
        "estimate_measured_total": "已测文件总大小",
        "estimate_projected_total": "抽样推算全量大小",
        "estimate_source_rows": "当前筛选数",
        "estimate_selected_rows": "本次估算数",
        "last_estimate_results": "大小估算结果",
        "sample_projection_note": "抽样推算使用成功返回大小的样本均值计算。",
        "estimate_progress": "正在估算远程大小 {done}/{total}",
        "estimate_done": "远程大小估算完成。",
        "remote_total": "远程总大小",
        "size_success": "成功获取大小的文件数",
        "save_filtered": "把当前筛选清单保存到输出目录",
        "saved": "已保存：{path}",
        "last_results": "最近一次下载结果",
        "status_counts": "状态统计",
        "diagnostics": "环境诊断",
        "runtime": "运行环境",
        "network_test": "网络测试",
        "run_network_test": "测试索引连接",
        "network_ok": "连接正常",
        "network_fail": "连接失败",
        "netcdf_preview": "本地 NetCDF 预览",
        "select_netcdf": "选择已下载的 NetCDF 文件",
        "inspect_file": "检查文件",
        "no_netcdf": "输出目录中没有找到 .nc 文件。",
        "xarray_missing": "如需预览 NetCDF 内容，请安装可选依赖：pip install \"argo-sprof-manager[preview]\"",
        "no_output_for_preview": "请先设置输出目录，再预览已下载的 NetCDF 文件。",
        "non_ascii_path_hint": "该文件路径包含非 ASCII 字符。若 Windows 下 NetCDF 底层库直接打开失败，程序会尝试复制到临时英文路径后再预览。",
        "temp_ascii_opened": "直接打开失败，但已通过临时英文路径副本成功预览该文件。",
        "output_health": "下载目录健康检查",
        "health_selected": "已选择目录",
        "health_exists": "目录存在",
        "health_writable": "可写入",
        "health_ascii_path": "纯英文路径",
        "health_free_space": "剩余空间",
        "health_part_files": ".part 临时文件",
        "health_small_files": "过小 Sprof 文件",
        "health_preview_cache": "预览缓存文件",
        "health_warning": "提醒",
        "warning_ok": "正常",
        "warning_no_output_dir": "尚未选择下载目录。",
        "warning_non_ascii_path": "路径包含非 ASCII 字符。工具会尽量兼容，但 Windows 上纯英文路径更稳定。",
        "warning_not_writable": "所选目录不可写入。",
        "cleanup_tools": "清理工具",
        "cleanup_part": "删除 .part 临时文件",
        "cleanup_small": "删除过小 Sprof 文件",
        "cleanup_preview": "清理 NetCDF 预览缓存",
        "cleanup_result": "已删除 {count} 个文件，释放 {size}。",
        "resume_manifest": "从 manifest 恢复",
        "resume_hint": "使用输出目录中的 download_manifest.csv，继续 pending、canceled 或 failed 项。",
        "resume_unfinished": "继续 manifest 未完成项目",
        "no_manifest": "输出目录中未找到 download_manifest.csv。",
        "no_unfinished": "manifest 中没有与当前索引匹配的未完成项目。",
        "unfinished_count": "发现未完成项目：{count}",
        "failure_category": "失败分类",
        "no_data": "无数据",
        "local_missing": "未下载",
        "local_downloaded": "已下载",
        "local_too_small": "文件过小",
        "local_no_dir": "未选择目录",
    },
}


LOCAL_STATUS_KEYS = {
    "downloaded": "local_downloaded",
    "too_small": "local_too_small",
    "missing": "local_missing",
    "no_output_dir": "local_no_dir",
}


def get_language() -> str:
    label = st.sidebar.selectbox(TEXT["en"]["language"], ["English", "中文"], index=0)
    return "zh" if label == "中文" else "en"


def t(lang: str, key: str, **kwargs: Any) -> str:
    text = TEXT[lang].get(key, TEXT["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def split_variables(parameters: str) -> list[str]:
    return core.split_variables(parameters)


def human_size(num_bytes: int | float | None) -> str:
    if num_bytes is None:
        return "-"
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def parse_output_dir(output_dir_text: str) -> Path | None:
    text = output_dir_text.strip()
    if not text:
        return None
    return Path(text).expanduser().resolve()


def records_to_dataframe(records: list[Any], base_url: str) -> pd.DataFrame:
    return pd.DataFrame(core.records_to_rows(records, base_url=base_url))


def fetch_latest_inventory(
    index_url: str,
    base_url: str,
    timeout: int,
    retries: int,
    allow_insecure_ssl_fallback: bool,
    save_to_disk: bool,
    output_dir: Path | None,
    lang: str,
) -> pd.DataFrame:
    records, index_text, index_size = core.fetch_latest_records(
        index_url=index_url,
        timeout=timeout,
        retries=retries,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
    )
    df = records_to_dataframe(records, base_url=base_url)

    if save_to_disk:
        if output_dir is None:
            raise ValueError(t(lang, "need_output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "argo_synthetic-profile_index.txt").write_text(index_text, encoding="utf-8")
        core.write_inventory(records, output_dir / "sprof_inventory.csv", base_url=base_url)

    st.session_state["latest_index_bytes"] = index_size
    st.session_state["latest_refresh_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return df


def add_local_status(df: pd.DataFrame, output_dir: Path | None, lang: str, min_bytes: int = 1024) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    rows = []
    for _, row in df.iterrows():
        if output_dir is None:
            code = "no_output_dir"
            rows.append(("", False, 0, "-", code, t(lang, LOCAL_STATUS_KEYS[code])))
            continue
        local_path = output_dir / str(row["local_filename"])
        exists = local_path.exists()
        size = local_path.stat().st_size if exists else 0
        if exists and size >= min_bytes:
            code = "downloaded"
        elif exists:
            code = "too_small"
        else:
            code = "missing"
        rows.append((str(local_path), exists, size, human_size(size), code, t(lang, LOCAL_STATUS_KEYS[code])))

    out = df.copy()
    out[["local_path", "local_exists", "local_size_bytes", "local_size", "local_status_code", "local_status"]] = rows
    return out


def parse_wmo_text(text: str) -> set[str]:
    cleaned = text.replace(",", " ").replace(";", " ").replace("\n", " ")
    return {item.strip() for item in cleaned.split() if item.strip().isdigit()}


def read_uploaded_wmos(uploaded_file: Any) -> set[str]:
    if uploaded_file is None:
        return set()
    text = uploaded_file.getvalue().decode("utf-8", errors="replace")
    return parse_wmo_text(text)


def filter_inventory(
    df: pd.DataFrame,
    dac_filter: list[str],
    variable_filter: list[str],
    variable_match_mode: str,
    text_query: str,
    wmo_filter: set[str],
) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()

    if dac_filter:
        filtered = filtered[filtered["dac"].isin(dac_filter)]

    if variable_filter:
        wanted = {item.upper() for item in variable_filter}

        def has_variables(parameters: str) -> bool:
            available = set(split_variables(parameters))
            return wanted.issubset(available) if variable_match_mode == "all" else bool(available & wanted)

        filtered = filtered[filtered["parameters_from_index"].fillna("").apply(has_variables)]

    if wmo_filter:
        filtered = filtered[filtered["wmo"].astype(str).isin(wmo_filter)]

    query = text_query.strip().lower()
    if query:
        mask = (
            filtered["wmo"].astype(str).str.lower().str.contains(query, regex=False)
            | filtered["dac"].astype(str).str.lower().str.contains(query, regex=False)
            | filtered["parameters_from_index"].astype(str).str.lower().str.contains(query, regex=False)
        )
        filtered = filtered[mask]

    return filtered.reset_index(drop=True)


def download_one(
    row: pd.Series,
    output_dir: Path,
    timeout: int,
    retries: int,
    force: bool,
    allow_insecure_ssl_fallback: bool,
) -> tuple[bool, str]:
    ssl_context = core.make_ssl_context(verify_ssl=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return core.download_file_atomic(
        url=str(row["sprof_url"]),
        outfile=output_dir / str(row["local_filename"]),
        timeout=timeout,
        retries=retries,
        force=force,
        ssl_context=ssl_context,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
    )


def download_many(
    df: pd.DataFrame,
    output_dir: Path,
    timeout: int,
    retries: int,
    workers: int,
    force: bool,
    allow_insecure_ssl_fallback: bool,
    lang: str,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["dac", "wmo", "downloaded", "status", "local_filename", "local_path"])

    output_dir.mkdir(parents=True, exist_ok=True)
    ssl_context = core.make_ssl_context(verify_ssl=True)
    progress = st.progress(0, text=t(lang, "prepare_download"))
    status_box = st.empty()
    log_box = st.empty()

    results: list[dict[str, Any]] = []
    recent_lines: list[str] = []

    def task(row_dict: dict[str, Any]) -> dict[str, Any]:
        local_path = output_dir / str(row_dict["local_filename"])
        try:
            downloaded, status = core.download_file_atomic(
                url=str(row_dict["sprof_url"]),
                outfile=local_path,
                timeout=timeout,
                retries=retries,
                force=force,
                ssl_context=ssl_context,
                allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
            )
        except Exception as exc:
            downloaded, status = False, f"error: {exc}"
        return {
            "dac": row_dict["dac"],
            "wmo": row_dict["wmo"],
            "downloaded": downloaded,
            "status": status,
            "local_filename": row_dict["local_filename"],
            "local_path": str(local_path),
        }

    rows = df.to_dict("records")
    total = len(rows)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(task, row) for row in rows]
        for finished, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            line = f"[{finished}/{total}] {result['dac']} {result['wmo']}: {result['status']}"
            recent_lines.append(line)
            recent_lines = recent_lines[-12:]
            progress.progress(finished / total, text=t(lang, "download_progress", done=finished, total=total))
            status_box.info(line)
            log_box.code("\n".join(recent_lines), language="text")

    progress.progress(1.0, text=t(lang, "download_done"))
    result_df = pd.DataFrame(results)
    manifest_path = write_download_manifest(result_df, output_dir)
    st.success(t(lang, "manifest_saved", path=manifest_path))
    return result_df


def estimate_remote_sizes(
    df: pd.DataFrame,
    timeout: int,
    workers: int,
    allow_insecure_ssl_fallback: bool,
    lang: str,
) -> pd.DataFrame:
    columns = ["dac", "wmo", "size_bytes", "status"]

    def head_size(row_dict: dict[str, Any]) -> dict[str, Any]:
        try:
            size_bytes, status = core.remote_file_size(
                str(row_dict["sprof_url"]),
                timeout=timeout,
                allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
            )
        except Exception as exc:
            size_bytes, status = None, f"failed: {exc}"
        return {
            "dac": row_dict["dac"],
            "wmo": row_dict["wmo"],
            "size_bytes": size_bytes,
            "status": status,
        }

    rows = df.to_dict("records")
    results: list[dict[str, Any]] = []
    total = len(rows)
    if total == 0:
        return pd.DataFrame(columns=columns)

    progress = st.progress(0.0, text=t(lang, "estimate_progress", done=0, total=total))
    update_interval = max(1, total // 200)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(head_size, row) for row in rows]
        for finished, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if finished == total or finished % update_interval == 0:
                progress.progress(
                    finished / total,
                    text=t(lang, "estimate_progress", done=finished, total=total),
                )
    progress.progress(1.0, text=t(lang, "estimate_done"))
    return pd.DataFrame(results, columns=columns)


def write_inventory_csv(df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = output_dir / "filtered_sprof_inventory.csv"
    columns = [
        "dac",
        "wmo",
        "sprof_url",
        "local_filename",
        "parameters_from_index",
        "variables",
        "date",
        "latitude",
        "longitude",
        "ocean",
        "profiler_type",
        "institution",
        "date_update",
    ]
    available = [column for column in columns if column in df.columns]
    df[available].to_csv(out_csv, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    return out_csv


def write_download_manifest(result_df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "download_manifest.csv"
    result_df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    return path


def retry_candidates(inventory_df: pd.DataFrame, result_df: pd.DataFrame) -> pd.DataFrame:
    if inventory_df.empty or result_df.empty:
        return pd.DataFrame()
    required_columns = {"dac", "wmo", "status"}
    if not required_columns.issubset(result_df.columns) or not {"dac", "wmo"}.issubset(inventory_df.columns):
        return pd.DataFrame()
    failed = result_df[~result_df["status"].isin(core.SUCCESS_STATUSES)]
    if failed.empty:
        return pd.DataFrame()
    keys = set(zip(failed["dac"].astype(str), failed["wmo"].astype(str)))
    mask = inventory_df.apply(lambda row: (str(row["dac"]), str(row["wmo"])) in keys, axis=1)
    return inventory_df[mask].reset_index(drop=True)


def status_label(lang: str, status: str) -> str:
    return t(lang, f"status_{status}") if f"status_{status}" in TEXT[lang] else status


def warning_label(lang: str, warning: str) -> str:
    if not warning:
        return t(lang, "warning_ok")
    if warning.startswith("not_writable"):
        return t(lang, "warning_not_writable")
    key = f"warning_{warning}"
    return t(lang, key) if key in TEXT[lang] else warning


def add_failure_categories(result_df: pd.DataFrame) -> pd.DataFrame:
    if result_df.empty or "status" not in result_df.columns:
        return result_df
    out = result_df.copy()
    out["category"] = out["status"].apply(core.classify_download_status)
    return out


def manifest_resume_candidates(inventory_df: pd.DataFrame, output_dir: Path | None) -> pd.DataFrame:
    if output_dir is None or inventory_df.empty:
        return pd.DataFrame()
    manifest_path = output_dir / "download_manifest.csv"
    manifest_rows = core.read_download_manifest(manifest_path)
    unfinished = core.unfinished_manifest_keys(manifest_rows)
    if not unfinished:
        return pd.DataFrame()
    mask = inventory_df.apply(lambda row: (str(row["dac"]), str(row["wmo"])) in unfinished, axis=1)
    return inventory_df[mask].reset_index(drop=True)


def select_size_estimate_rows(df: pd.DataFrame, mode: str, count: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if mode == "full":
        return df.reset_index(drop=True)

    limit = max(1, min(int(count), len(df)))
    if mode == "sample_n":
        return df.sample(n=limit, random_state=42).sort_index().reset_index(drop=True)
    return df.head(limit).reset_index(drop=True)


def start_background_download(
    df: pd.DataFrame,
    output_dir: Path,
    timeout: int,
    retries: int,
    workers: int,
    force: bool,
    allow_insecure_ssl_fallback: bool,
) -> None:
    job = download_jobs.start_download_job(
        rows=df.to_dict("records"),
        output_dir=output_dir,
        timeout=timeout,
        retries=retries,
        workers=workers,
        force=force,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
    )
    st.session_state["active_job_id"] = job.job_id


def active_download_job() -> download_jobs.DownloadJob | None:
    return download_jobs.get_job(st.session_state.get("active_job_id"))


def start_background_size_estimate(
    df: pd.DataFrame,
    source_total: int,
    mode: str,
    timeout: int,
    workers: int,
    allow_insecure_ssl_fallback: bool,
) -> None:
    job = size_estimate_jobs.start_size_estimate_job(
        rows=df.to_dict("records"),
        source_total=source_total,
        mode=mode,
        timeout=timeout,
        workers=workers,
        allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
    )
    st.session_state["active_size_estimate_job_id"] = job.job_id


def active_size_estimate_job() -> size_estimate_jobs.SizeEstimateJob | None:
    return size_estimate_jobs.get_job(st.session_state.get("active_size_estimate_job_id"))


def size_estimate_result_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    columns = ["dac", "wmo", "size_bytes", "status", "sprof_url"]
    return pd.DataFrame(results, columns=columns)


def show_download_job_panel(lang: str) -> None:
    job = active_download_job()
    if job is None:
        return

    snapshot = job.snapshot()
    result_df = add_failure_categories(pd.DataFrame(snapshot["results"]))
    if not result_df.empty:
        st.session_state["last_results"] = result_df

    st.subheader(t(lang, "active_job"))
    st.info(t(lang, "pause_note"))
    progress_text = f"{snapshot['completed']}/{snapshot['total']} - {status_label(lang, snapshot['status'])}"
    st.progress(float(snapshot["progress"]), text=progress_text)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric(t(lang, "job_status"), status_label(lang, snapshot["status"]))
    metric_col2.metric(t(lang, "job_completed"), f"{snapshot['completed']:,} / {snapshot['total']:,}")
    metric_col3.metric(t(lang, "job_submitted"), f"{snapshot['submitted']:,}")

    if snapshot.get("message"):
        st.caption(str(snapshot["message"]))

    control_col1, control_col2, control_col3 = st.columns(3)
    with control_col1:
        if snapshot["status"] == "paused":
            if st.button(t(lang, "resume_download"), width="stretch"):
                job.resume()
                st.success(t(lang, "job_resumed"))
                st.rerun()
        else:
            if st.button(
                t(lang, "pause_download"),
                width="stretch",
                disabled=snapshot["status"] not in {"queued", "running"},
            ):
                job.pause()
                st.warning(t(lang, "job_paused"))
                st.rerun()
    with control_col2:
        if st.button(
            t(lang, "cancel_download"),
            width="stretch",
            disabled=snapshot["status"] in download_jobs.TERMINAL_STATUSES,
        ):
            job.cancel()
            st.warning(t(lang, "job_canceled"))
            st.rerun()
    with control_col3:
        if st.button(
            t(lang, "clear_job"),
            width="stretch",
            disabled=snapshot["status"] not in download_jobs.TERMINAL_STATUSES,
        ):
            download_jobs.forget_job(snapshot["job_id"])
            st.session_state.pop("active_job_id", None)
            st.rerun()

    if snapshot["recent_lines"]:
        st.code("\n".join(snapshot["recent_lines"]), language="text")

    if snapshot["manifest_path"]:
        st.caption(t(lang, "manifest_saved", path=snapshot["manifest_path"]))

    if snapshot["status"] in {"queued", "running", "cancel_requested"}:
        time.sleep(1.0)
        st.rerun()


@st.fragment(run_every=1.0)
def show_size_estimate_job_panel(lang: str) -> None:
    job = active_size_estimate_job()
    if job is None:
        return

    snapshot = job.snapshot()
    result_df = size_estimate_result_dataframe(snapshot["results"])
    if not result_df.empty:
        st.session_state["last_size_estimate_results"] = result_df
        st.session_state["last_size_estimate_snapshot"] = snapshot

    st.subheader(t(lang, "active_estimate"))
    st.info(t(lang, "estimate_active_note"))
    progress_text = f"{snapshot['completed']}/{snapshot['total']} - {status_label(lang, snapshot['status'])}"
    st.progress(float(snapshot["progress"]), text=progress_text)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric(t(lang, "job_status"), status_label(lang, snapshot["status"]))
    metric_col2.metric(t(lang, "estimate_selected_rows"), f"{snapshot['completed']:,} / {snapshot['total']:,}")
    metric_col3.metric(t(lang, "estimate_source_rows"), f"{snapshot['source_total']:,}")

    metric_col4, metric_col5, metric_col6 = st.columns(3)
    metric_col4.metric(t(lang, "estimate_measured_total"), human_size(snapshot["total_size_bytes"]))
    metric_col5.metric(t(lang, "size_success"), f"{snapshot['success_count']:,} / {snapshot['completed']:,}")
    projected_total = snapshot.get("projected_total_size_bytes")
    metric_col6.metric(t(lang, "estimate_projected_total"), human_size(projected_total) if projected_total is not None else "-")
    if projected_total is not None:
        st.caption(t(lang, "sample_projection_note"))

    if snapshot.get("message"):
        st.caption(str(snapshot["message"]))

    control_col1, control_col2 = st.columns(2)
    with control_col1:
        if st.button(
            t(lang, "cancel_estimate"),
            width="stretch",
            disabled=snapshot["status"] in size_estimate_jobs.TERMINAL_STATUSES,
        ):
            job.cancel()
            st.warning(t(lang, "estimate_canceled"))
            st.rerun(scope="fragment")
    with control_col2:
        if st.button(
            t(lang, "clear_estimate"),
            width="stretch",
            disabled=snapshot["status"] not in size_estimate_jobs.TERMINAL_STATUSES,
        ):
            size_estimate_jobs.forget_job(snapshot["job_id"])
            st.session_state.pop("active_size_estimate_job_id", None)
            st.rerun()

    if snapshot["recent_lines"]:
        st.code("\n".join(snapshot["recent_lines"]), language="text")

    if not result_df.empty:
        display_df = result_df.copy()
        display_df["size"] = display_df["size_bytes"].apply(human_size)
        st.dataframe(display_df, width="stretch", hide_index=True)


def show_runtime_diagnostics(lang: str) -> None:
    st.subheader(t(lang, "runtime"))
    st.dataframe(pd.DataFrame(core.runtime_report()), width="stretch", hide_index=True)


def show_network_test(index_url: str, timeout: int, allow_insecure_ssl_fallback: bool, lang: str) -> None:
    st.subheader(t(lang, "network_test"))
    if st.button(t(lang, "run_network_test"), width="stretch"):
        with st.spinner(t(lang, "network_test")):
            st.session_state["connection_result"] = core.probe_url(
                index_url,
                timeout=timeout,
                allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
            )
    result = st.session_state.get("connection_result")
    if result:
        if result.get("ok"):
            st.success(t(lang, "network_ok"))
        else:
            st.error(t(lang, "network_fail"))
        st.json(result)


def show_output_directory_health(output_dir: Path | None, lang: str) -> None:
    st.subheader(t(lang, "output_health"))
    health = core.directory_health(output_dir)
    rows = [
        {"item": t(lang, "health_selected"), "value": str(health["selected"])},
        {"item": t(lang, "health_exists"), "value": str(health["exists"])},
        {"item": t(lang, "health_writable"), "value": str(health["writable"])},
        {"item": t(lang, "health_ascii_path"), "value": str(health["path_is_ascii"])},
        {"item": t(lang, "health_free_space"), "value": human_size(health["free_bytes"]) if health["free_bytes"] is not None else "-"},
        {"item": t(lang, "health_part_files"), "value": str(health["part_files"])},
        {"item": t(lang, "health_small_files"), "value": str(health["small_sprof_files"])},
        {"item": t(lang, "health_preview_cache"), "value": str(health["preview_cache_files"])},
        {"item": t(lang, "health_warning"), "value": warning_label(lang, str(health["warning"]))},
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def show_cleanup_tools(output_dir: Path | None, lang: str) -> None:
    st.subheader(t(lang, "cleanup_tools"))
    if output_dir is None:
        st.info(t(lang, "no_output_for_preview"))
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(t(lang, "cleanup_part"), width="stretch"):
            result = core.cleanup_part_files(output_dir)
            st.success(t(lang, "cleanup_result", count=result["removed"], size=human_size(result["bytes_removed"])))
    with col2:
        if st.button(t(lang, "cleanup_small"), width="stretch"):
            result = core.cleanup_small_sprof_files(output_dir)
            st.success(t(lang, "cleanup_result", count=result["removed"], size=human_size(result["bytes_removed"])))
    with col3:
        if st.button(t(lang, "cleanup_preview"), width="stretch"):
            result = core.cleanup_preview_cache()
            st.success(t(lang, "cleanup_result", count=result["removed"], size=human_size(result["bytes_removed"])))


def show_netcdf_preview(output_dir: Path | None, lang: str) -> None:
    st.subheader(t(lang, "netcdf_preview"))
    if output_dir is None:
        st.info(t(lang, "no_output_for_preview"))
        return
    files = sorted(output_dir.glob("*_Sprof.nc"))
    if not files:
        st.info(t(lang, "no_netcdf"))
        return
    selected = st.selectbox(t(lang, "select_netcdf"), files, format_func=lambda path: path.name)
    if not core.path_is_ascii(selected):
        st.warning(t(lang, "non_ascii_path_hint"))
    if st.button(t(lang, "inspect_file")):
        info = core.inspect_netcdf_file(selected)
        if info.get("error") == "xarray_not_installed":
            st.warning(t(lang, "xarray_missing"))
        if info.get("opened_via_temp_ascii_copy") == "true":
            st.info(t(lang, "temp_ascii_opened"))
        st.json(info)


st.set_page_config(
    page_title=TEXT["en"]["page_title"],
    page_icon="🌊",
    layout="wide",
)

lang = get_language()
st.title(t(lang, "page_title"))
st.caption(t(lang, "caption"))

if "inventory_df" not in st.session_state:
    st.session_state["inventory_df"] = pd.DataFrame()

with st.sidebar:
    st.header(t(lang, "data_source"))
    index_url = st.text_input(t(lang, "index_url"), value=core.DEFAULT_INDEX_URL)
    base_url = st.text_input(t(lang, "base_url"), value=core.DEFAULT_BASE_URL)
    output_dir_text = st.text_input(
        t(lang, "output_dir"),
        value="",
        placeholder=t(lang, "output_placeholder"),
    )
    output_dir = parse_output_dir(output_dir_text)

    st.divider()
    st.header(t(lang, "network_download"))
    timeout = st.number_input(t(lang, "timeout"), min_value=10, max_value=3600, value=120, step=10)
    retries = st.number_input(t(lang, "retries"), min_value=1, max_value=20, value=4, step=1)
    workers = st.number_input(t(lang, "workers"), min_value=1, max_value=64, value=8, step=1)
    force = st.checkbox(t(lang, "force"), value=False)
    allow_insecure_ssl_fallback = st.checkbox(t(lang, "ssl_fallback"), value=True)
    save_latest_files = st.checkbox(t(lang, "save_latest"), value=False)

    st.divider()
    st.caption(t(lang, "refresh_hint"))
    if st.button(t(lang, "refresh"), type="primary", width="stretch"):
        with st.spinner(t(lang, "refreshing")):
            try:
                st.session_state["inventory_df"] = fetch_latest_inventory(
                    index_url=index_url,
                    base_url=base_url,
                    timeout=int(timeout),
                    retries=int(retries),
                    allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
                    save_to_disk=save_latest_files,
                    output_dir=output_dir,
                    lang=lang,
                )
                st.session_state.pop("last_results", None)
                st.success(t(lang, "refresh_ok"))
            except Exception as exc:
                st.error(t(lang, "refresh_fail", error=exc))

df = st.session_state["inventory_df"]
df_with_status = add_local_status(df, output_dir, lang) if not df.empty else df.copy()

inventory_tab, download_tab, diagnostics_tab = st.tabs(
    [t(lang, "tabs_inventory"), t(lang, "tabs_download"), t(lang, "tabs_diagnostics")]
)

with inventory_tab:
    if df.empty:
        st.info(t(lang, "empty_inventory"))
    else:
        all_dacs = sorted(df_with_status["dac"].dropna().unique().tolist())
        all_variables = sorted(
            {
                variable
                for parameters in df_with_status["parameters_from_index"].fillna("")
                for variable in split_variables(parameters)
            }
        )

        st.subheader(t(lang, "filters"))
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.0, 1.4, 1.2, 1.4])
        with filter_col1:
            dac_filter = st.multiselect(t(lang, "dac"), options=all_dacs)
        with filter_col2:
            variable_filter = st.multiselect(t(lang, "variables"), options=all_variables)
        with filter_col3:
            variable_match_mode = st.radio(
                t(lang, "match"),
                ["any", "all"],
                format_func=lambda item: t(lang, "match_all" if item == "all" else "match_any"),
            )
        with filter_col4:
            text_query = st.text_input(t(lang, "search"), placeholder="5905137 / DOXY")

        wmo_col1, wmo_col2, wmo_col3 = st.columns([1.6, 1.0, 0.8])
        with wmo_col1:
            wmo_text = st.text_area(t(lang, "wmo_batch"), help=t(lang, "wmo_batch_help"), height=90)
        with wmo_col2:
            wmo_file = st.file_uploader(t(lang, "wmo_upload"), type=["txt", "csv"])
        with wmo_col3:
            apply_wmo = st.checkbox(t(lang, "wmo_only"), value=False)

        wmo_filter = (parse_wmo_text(wmo_text) | read_uploaded_wmos(wmo_file)) if apply_wmo else set()
        filtered_df = filter_inventory(
            df_with_status,
            dac_filter=dac_filter,
            variable_filter=variable_filter,
            variable_match_mode=variable_match_mode,
            text_query=text_query,
            wmo_filter=wmo_filter,
        )
        st.session_state["filtered_df"] = filtered_df
        st.session_state["df_with_status"] = df_with_status

        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        metric_col1.metric(t(lang, "index_floats"), f"{len(df_with_status):,}")
        metric_col2.metric(t(lang, "filtered"), f"{len(filtered_df):,}")
        metric_col3.metric(t(lang, "downloaded"), f"{int((df_with_status['local_status_code'] == 'downloaded').sum()):,}")
        metric_col4.metric(t(lang, "local_size"), human_size(int(df_with_status["local_size_bytes"].sum())))
        metric_col5.metric(t(lang, "index_size"), human_size(st.session_state.get("latest_index_bytes")))

        if st.session_state.get("latest_refresh_time"):
            st.caption(t(lang, "last_refresh", time=st.session_state["latest_refresh_time"]))

        st.subheader(t(lang, "map"))
        map_df = filtered_df.dropna(subset=["latitude", "longitude"]).rename(columns={"latitude": "lat", "longitude": "lon"})
        if map_df.empty:
            st.info(t(lang, "map_empty"))
        else:
            st.map(map_df[["lat", "lon"]])

        st.subheader(t(lang, "inventory_table"))
        display_columns = [
            "dac",
            "wmo",
            "variables",
            "date",
            "latitude",
            "longitude",
            "ocean",
            "institution",
            "local_status",
            "local_size",
            "sprof_url",
        ]
        st.dataframe(filtered_df[[column for column in display_columns if column in filtered_df.columns]], width="stretch", height=420, hide_index=True)

        csv_bytes = filtered_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            t(lang, "export_csv"),
            data=csv_bytes,
            file_name="filtered_sprof_inventory.csv",
            mime="text/csv",
        )

with download_tab:
    st.subheader(t(lang, "download_actions"))
    if df.empty:
        st.info(t(lang, "empty_inventory"))
    else:
        filtered_df = st.session_state.get("filtered_df", df_with_status)
        output_ready = output_dir is not None
        current_job = active_download_job()
        current_snapshot = current_job.snapshot() if current_job else None
        job_is_active = bool(current_snapshot and current_snapshot["status"] not in download_jobs.TERMINAL_STATUSES)
        current_size_job = active_size_estimate_job()
        current_size_snapshot = current_size_job.snapshot() if current_size_job else None
        size_job_is_active = bool(
            current_size_snapshot
            and current_size_snapshot["status"] not in size_estimate_jobs.TERMINAL_STATUSES
        )

        show_download_job_panel(lang)

        single_col, batch_col, all_col = st.columns(3)

        with single_col:
            st.markdown(f"**{t(lang, 'single')}**")
            if not output_ready:
                st.warning(t(lang, "output_required"))
            if filtered_df.empty:
                st.warning(t(lang, "empty_filter"))
            else:
                labels = [
                    f"{row.dac} / {row.wmo} / {row.variables or '-'}"
                    for row in filtered_df.itertuples(index=False)
                ]
                selected_label = st.selectbox(t(lang, "select_float"), labels)
                selected_index = labels.index(selected_label)
                if st.button(t(lang, "download_selected"), width="stretch", disabled=not output_ready or job_is_active):
                    row = filtered_df.iloc[selected_index]
                    with st.spinner(t(lang, "downloading_one", dac=row["dac"], wmo=row["wmo"])):
                        downloaded, status = download_one(
                            row=row,
                            output_dir=output_dir,
                            timeout=int(timeout),
                            retries=int(retries),
                            force=force,
                            allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
                        )
                    st.session_state["last_results"] = pd.DataFrame(
                        [{
                            "dac": row["dac"],
                            "wmo": row["wmo"],
                            "downloaded": downloaded,
                            "status": status,
                            "local_filename": row["local_filename"],
                            "local_path": str(output_dir / str(row["local_filename"])),
                        }]
                    )
                    write_download_manifest(st.session_state["last_results"], output_dir)
                    st.success(f"{row['dac']} / {row['wmo']}: {status}")

        with batch_col:
            st.markdown(f"**{t(lang, 'batch')}**")
            max_items = st.number_input(t(lang, "max_items"), min_value=0, value=0, step=10)
            confirm_filtered = st.checkbox(t(lang, "confirm_batch"))
            if st.button(
                t(lang, "start_batch"),
                width="stretch",
                disabled=not output_ready or not confirm_filtered or filtered_df.empty or job_is_active,
            ):
                batch_df = filtered_df if max_items == 0 else filtered_df.head(int(max_items))
                start_background_download(
                    df=batch_df,
                    output_dir=output_dir,
                    timeout=int(timeout),
                    retries=int(retries),
                    workers=int(workers),
                    force=force,
                    allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
                )
                st.success(t(lang, "job_started"))
                st.rerun()

        with all_col:
            st.markdown(f"**{t(lang, 'all')}**")
            st.write(t(lang, "all_hint", count=f"{len(df_with_status):,}"))
            confirm_all = st.checkbox(t(lang, "confirm_all"))
            if st.button(t(lang, "start_all"), type="primary", width="stretch", disabled=not output_ready or not confirm_all or job_is_active):
                start_background_download(
                    df=df_with_status,
                    output_dir=output_dir,
                    timeout=int(timeout),
                    retries=int(retries),
                    workers=int(workers),
                    force=force,
                    allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
                )
                st.success(t(lang, "job_started"))
                st.rerun()

        st.divider()
        st.subheader(t(lang, "resume_manifest"))
        st.caption(t(lang, "resume_hint"))
        if not output_ready:
            st.info(t(lang, "output_required"))
        else:
            manifest_path = output_dir / "download_manifest.csv"
            if not manifest_path.exists():
                st.info(t(lang, "no_manifest"))
            else:
                resume_df = manifest_resume_candidates(df_with_status, output_dir)
                if resume_df.empty:
                    st.info(t(lang, "no_unfinished"))
                else:
                    st.write(t(lang, "unfinished_count", count=f"{len(resume_df):,}"))
                    if st.button(t(lang, "resume_unfinished"), width="stretch", disabled=job_is_active):
                        start_background_download(
                            df=resume_df,
                            output_dir=output_dir,
                            timeout=int(timeout),
                            retries=int(retries),
                            workers=int(workers),
                            force=force,
                            allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
                        )
                        st.success(t(lang, "job_started"))
                        st.rerun()

        st.divider()
        st.subheader(t(lang, "retry_failed"))
        result_df = st.session_state.get("last_results", pd.DataFrame())
        retry_df = retry_candidates(df_with_status, result_df)
        if retry_df.empty:
            st.info(t(lang, "no_failed"))
        elif st.button(t(lang, "retry_failed_button"), width="stretch", disabled=not output_ready or job_is_active):
            start_background_download(
                df=retry_df,
                output_dir=output_dir,
                timeout=int(timeout),
                retries=int(retries),
                workers=int(workers),
                force=True,
                allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
            )
            st.success(t(lang, "job_started"))
            st.rerun()

        st.divider()
        st.subheader(t(lang, "tools"))
        tool_col1, tool_col2 = st.columns(2)
        with tool_col1:
            if active_size_estimate_job() is not None:
                show_size_estimate_job_panel(lang)
            estimate_modes = ["full", "first_n", "sample_n"]
            estimate_mode = st.radio(
                t(lang, "estimate_scope"),
                estimate_modes,
                horizontal=True,
                format_func=lambda item: t(lang, f"estimate_mode_{item}"),
                disabled=filtered_df.empty or size_job_is_active,
            )
            max_estimate_count = max(1, len(filtered_df))
            estimate_count = st.number_input(
                t(lang, "estimate_item_count"),
                min_value=1,
                max_value=max_estimate_count,
                value=min(100, max_estimate_count),
                step=10,
                disabled=filtered_df.empty or estimate_mode == "full" or size_job_is_active,
            )
            estimate_df = select_size_estimate_rows(filtered_df, estimate_mode, int(estimate_count))
            st.caption(t(lang, "estimate_selected_hint", selected=f"{len(estimate_df):,}", total=f"{len(filtered_df):,}"))
            if estimate_mode == "full" and len(filtered_df) > 1000:
                st.warning(t(lang, "estimate_full_warning", count=f"{len(filtered_df):,}"))
            if st.button(
                t(lang, "start_estimate"),
                disabled=filtered_df.empty or size_job_is_active,
                width="stretch",
            ):
                start_background_size_estimate(
                    df=estimate_df,
                    source_total=len(filtered_df),
                    mode=estimate_mode,
                    timeout=int(timeout),
                    workers=int(workers),
                    allow_insecure_ssl_fallback=allow_insecure_ssl_fallback,
                )
                st.success(t(lang, "estimate_started"))
                st.rerun()

        with tool_col2:
            if st.button(t(lang, "save_filtered"), disabled=not output_ready or filtered_df.empty):
                saved_csv = write_inventory_csv(filtered_df, output_dir)
                st.success(t(lang, "saved", path=saved_csv))

        if "last_results" in st.session_state:
            st.divider()
            st.subheader(t(lang, "last_results"))
            result_df = add_failure_categories(st.session_state["last_results"])
            status_counts = result_df["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            st.markdown(f"**{t(lang, 'status_counts')}**")
            st.dataframe(status_counts, width="stretch", hide_index=True)
            if "category" in result_df.columns:
                category_counts = result_df["category"].value_counts().reset_index()
                category_counts.columns = [t(lang, "failure_category"), "count"]
                st.dataframe(category_counts, width="stretch", hide_index=True)
            st.dataframe(result_df, width="stretch", hide_index=True)

with diagnostics_tab:
    st.subheader(t(lang, "diagnostics"))
    diag_col1, diag_col2 = st.columns(2)
    with diag_col1:
        show_runtime_diagnostics(lang)
    with diag_col2:
        show_network_test(index_url, int(timeout), allow_insecure_ssl_fallback, lang)
    st.divider()
    show_output_directory_health(output_dir, lang)
    st.divider()
    show_cleanup_tools(output_dir, lang)
    st.divider()
    show_netcdf_preview(output_dir, lang)
