#!/usr/bin/env python3
"""Bump the RESTOCK integration version."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "restock" / "manifest.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def main() -> int:
    """Update manifest.json with the requested version."""
    if len(sys.argv) != 2:
        print("Usage: scripts/bump_version.py 0.1.1", file=sys.stderr)
        return 2

    version = sys.argv[1].strip()
    if not SEMVER.match(version):
        print(f"Invalid version: {version}", file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    old_version = manifest.get("version")
    manifest["version"] = version
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"RESTOCK version: {old_version} -> {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
