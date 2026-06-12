from __future__ import annotations

import argparse
import sys

from argo_sprof_manager import argo_sprof_core as core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run live network checks against Argo GDAC.")
    parser.add_argument("--index-url", default=core.DEFAULT_INDEX_URL)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--no-insecure-fallback", action="store_true")
    args = parser.parse_args(argv)

    allow_fallback = not args.no_insecure_fallback
    result = core.probe_url(
        args.index_url,
        timeout=args.timeout,
        allow_insecure_ssl_fallback=allow_fallback,
    )
    print(result)
    if not result.get("ok"):
        return 1

    size_bytes, status = core.remote_file_size(
        args.index_url,
        timeout=args.timeout,
        allow_insecure_ssl_fallback=allow_fallback,
    )
    print({"size_bytes": size_bytes, "status": status})
    return 0 if status in {"ok", "no_content_length"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
