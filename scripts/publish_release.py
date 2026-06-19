#!/usr/bin/env python3
"""Prepare a RESTOCK release by updating versioned files."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "restock" / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def main() -> int:
    """Update manifest.json and prepend a changelog entry."""
    if len(sys.argv) < 3:
        print(
            "Usage: scripts/publish_release.py 0.1.1 \"Release note\"",
            file=sys.stderr,
        )
        return 2

    version = sys.argv[1].strip()
    notes = [note.strip() for note in sys.argv[2:] if note.strip()]
    if not SEMVER.match(version):
        print(f"Invalid version: {version}", file=sys.stderr)
        return 2
    if not notes:
        print("At least one release note is required", file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    old_version = manifest.get("version")
    manifest["version"] = version
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    changelog = CHANGELOG.read_text(encoding="utf-8")
    note_lines = "\n".join(f"- {note}" for note in notes)
    entry = f"## {version} - {date.today().isoformat()}\n\n{note_lines}\n\n"
    if changelog.startswith("# Changelog\n\n"):
        changelog = changelog.replace("# Changelog\n\n", f"# Changelog\n\n{entry}", 1)
    else:
        changelog = f"# Changelog\n\n{entry}{changelog}"
    CHANGELOG.write_text(changelog, encoding="utf-8")

    print(f"RESTOCK version: {old_version} -> {version}")
    print("Updated CHANGELOG.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
