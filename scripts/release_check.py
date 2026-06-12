from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path = ROOT, timeout: int | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True, timeout=timeout)


def script_path(venv_dir: Path, name: str) -> Path:
    scripts_dir = "Scripts" if sys.platform.startswith("win") else "bin"
    suffix = ".exe" if sys.platform.startswith("win") else ""
    return venv_dir / scripts_dir / f"{name}{suffix}"


def python_path(venv_dir: Path) -> Path:
    scripts_dir = "Scripts" if sys.platform.startswith("win") else "bin"
    suffix = ".exe" if sys.platform.startswith("win") else ""
    return venv_dir / scripts_dir / f"python{suffix}"


def wait_for_http(url: str, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"HTTP smoke test failed for {url}: {last_error}")


def build_wheel(wheel_dir: Path) -> Path:
    run([sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps", "-w", str(wheel_dir)], timeout=180)
    wheels = sorted(wheel_dir.glob("argo_sprof_manager-*.whl"))
    if not wheels:
        raise RuntimeError(f"No wheel was built in {wheel_dir}")
    return wheels[-1]


def compile_project() -> None:
    targets = [ROOT / "src", ROOT / "scripts"]
    tests_dir = ROOT / "tests"
    if tests_dir.exists():
        targets.append(tests_dir)
    run([sys.executable, "-m", "compileall", "-q", *[str(path) for path in targets]], timeout=60)


def run_local_tests_if_available() -> None:
    tests_dir = ROOT / "tests"
    if not tests_dir.exists():
        print("No tests directory found; skipping local pytest suite.", flush=True)
        return
    test_files = list(tests_dir.rglob("test_*.py"))
    if not test_files:
        print("No pytest files found in tests directory; skipping local pytest suite.", flush=True)
        return
    run([sys.executable, "-m", "pytest", str(tests_dir), "-q"], timeout=180)


def isolated_install_check(wheel_path: Path, use_system_site_packages: bool, port: int) -> None:
    with tempfile.TemporaryDirectory(prefix="argo_sprof_install_check_") as temp_text:
        venv_dir = Path(temp_text) / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=use_system_site_packages).create(venv_dir)
        py = python_path(venv_dir)
        exe = script_path(venv_dir, "argo-sprof-manager")

        run([str(py), "-m", "pip", "install", "--upgrade", "pip"], timeout=180)
        run([str(py), "-m", "pip", "install", str(wheel_path)], timeout=300)
        if not use_system_site_packages:
            run([str(py), "-m", "pip", "check"], timeout=60)
        run([str(exe), "--help"], timeout=30)

        process = subprocess.Popen(
            [
                str(exe),
                "--port",
                str(port),
                "--headless",
                "--browser.gatherUsageStats",
                "false",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_for_http(f"http://127.0.0.1:{port}", timeout_seconds=45)
            print(f"HTTP smoke test passed on port {port}.", flush=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run release checks for argo-sprof-manager.")
    parser.add_argument("--port", type=int, default=8591, help="Local port for the HTTP smoke test.")
    parser.add_argument(
        "--use-system-site-packages",
        action="store_true",
        help="Create the temporary venv with access to the current environment packages.",
    )
    parser.add_argument(
        "--skip-isolated-install",
        action="store_true",
        help="Skip installing the wheel into a temporary venv.",
    )
    args = parser.parse_args(argv)

    compile_project()
    run_local_tests_if_available()

    with tempfile.TemporaryDirectory(prefix="argo_sprof_wheel_") as wheel_text:
        wheel_path = build_wheel(Path(wheel_text))
        if not args.skip_isolated_install:
            isolated_install_check(
                wheel_path,
                use_system_site_packages=args.use_system_site_packages,
                port=args.port,
            )

    cache_dirs = [
        path
        for path in ROOT.rglob("*")
        if path.is_dir()
        and (path.name in {"__pycache__", ".pytest_cache", "build", "dist"} or path.name.endswith(".egg-info"))
    ]
    for path in cache_dirs:
        shutil.rmtree(path, ignore_errors=True)

    print("Release checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
