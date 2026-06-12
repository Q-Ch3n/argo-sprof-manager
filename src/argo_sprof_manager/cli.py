from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path


def configure_stdio() -> None:
    """Keep CLI messages readable when launched from PowerShell or VS Code."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def port_in_use(address: str, port: int) -> bool:
    """Return True when a TCP port already has a local listener."""
    probe_host = "127.0.0.1" if address in {"", "0.0.0.0", "::"} else address
    try:
        with socket.create_connection((probe_host, port), timeout=0.3):
            return True
    except OSError:
        return False


def choose_port(address: str, requested_port: int, auto_port: bool) -> int:
    """Use the requested port, or find the next available one."""
    if not auto_port or not port_in_use(address, requested_port):
        return requested_port

    for candidate in range(requested_port + 1, requested_port + 100):
        if not port_in_use(address, candidate):
            print(
                f"端口 {requested_port} 已被占用，已自动改用 {candidate}。",
                file=sys.stderr,
            )
            return candidate

    raise RuntimeError(f"Cannot find an available port near {requested_port}.")


def main(argv: list[str] | None = None) -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(
        prog="argo-sprof-manager",
        description="Launch the Argo Sprof Streamlit download manager.",
    )
    parser.add_argument("--address", default="127.0.0.1", help="Streamlit server address.")
    parser.add_argument("--port", default=8501, type=int, help="Streamlit server port.")
    parser.add_argument("--headless", action="store_true", help="Run Streamlit in headless mode.")
    parser.add_argument(
        "--no-auto-port",
        action="store_true",
        help="Do not switch to the next free port when the requested port is busy.",
    )
    args, streamlit_args = parser.parse_known_args(argv)

    app_path = Path(__file__).with_name("argo_streamlit_app.py")
    port = choose_port(args.address, args.port, auto_port=not args.no_auto_port)

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    try:
        from streamlit.web import cli as streamlit_cli
    except ImportError as exc:
        print("Streamlit is not installed. Please run: pip install -e .", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        str(args.address),
        "--server.port",
        str(port),
        "--browser.gatherUsageStats",
        "false",
    ]
    if args.headless:
        sys.argv.extend(["--server.headless", "true"])
    if streamlit_args:
        sys.argv.extend(streamlit_args)

    try:
        streamlit_cli.main()
    except SystemExit as exc:
        return int(exc.code or 0) if isinstance(exc.code, int) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
