#!/usr/bin/env python3
"""
build_index.py — scan notes/ and calendar/, parse frontmatter, write .cache/notes-index.json

The index lets the agent search notes by title/tags/summary without loading every file.
Full file content is only loaded on demand via the filesystem MCP.

Usage:
    python3 tools/build_index.py [base_dir] [output_path]
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown. Returns (metadata, body)."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip().strip('"').strip("'")
        # Parse lists like [tag1, tag2] or - tag1
        if val.startswith("[") and val.endswith("]"):
            fm[key.strip()] = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
        else:
            fm[key.strip()] = val

    return fm, parts[2]


def build_index(base_dir: str, output_path: str) -> None:
    base = Path(base_dir)
    index = []

    for folder in ["notes", "calendar"]:
        folder_path = base / folder
        if not folder_path.exists():
            continue

        for md_file in sorted(folder_path.rglob("*.md")):
            if md_file.name.startswith("."):
                continue

            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            fm, body = parse_frontmatter(content)
            summary = re.sub(r"\s+", " ", body.strip())[:300]

            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            index.append({
                "path": str(md_file.relative_to(base)),
                "folder": folder,
                "title": fm.get("title", md_file.stem.replace("-", " ").replace("_", " ").title()),
                "date": str(fm.get("date", "")),
                "tags": tags,
                "project": fm.get("project", ""),
                "summary": summary,
                "modified": datetime.fromtimestamp(md_file.stat().st_mtime).strftime("%Y-%m-%d"),
            })

    # Sort by modified date, newest first
    index.sort(key=lambda x: x["modified"], reverse=True)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, indent=2, ensure_ascii=False))

    print(f"Index: {len(index)} files → {output_path}")


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    output = sys.argv[2] if len(sys.argv) > 2 else ".cache/notes-index.json"
    build_index(base, output)
