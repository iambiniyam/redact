#!/usr/bin/env python3
"""Download the YuNet face detector (RapidOCR models ship with the wheel)."""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

from redact.config import FACE_MODEL_URL, Paths, indra_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=FACE_MODEL_URL)
    parser.add_argument("--dest", type=Path, default=Paths.default().face_model)
    parser.add_argument("--with-indra", action="store_true", help="Also download the optional Indra OCR models.")
    args = parser.parse_args()

    args.dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.dest.with_suffix(".part")
    print(f"-> {args.url}")
    try:
        with urllib.request.urlopen(args.url, timeout=120) as response, tmp.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except Exception as exc:  # noqa: BLE001
        print(f"failed: {exc}", file=sys.stderr)
        return 1
    tmp.replace(args.dest)
    print(f"saved {args.dest} ({args.dest.stat().st_size / 1e3:.0f} KB)")

    if args.with_indra:
        folder = indra_dir()
        for name in INDRA_FILES:
            target = folder / name
            print(f"-> {INDRA_BASE}/{name}")
            try:
                fetch(f"{INDRA_BASE}/{name}", target)
            except Exception as exc:  # noqa: BLE001
                print(f"failed: {exc}", file=sys.stderr)
                return 1
            print(f"  saved {target} ({target.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
