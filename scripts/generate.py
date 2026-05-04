#!/usr/bin/env python3
"""
generate.py — build harness configs from registry/, with frontmatter-gated skill loading

Skill/rule files use YAML frontmatter to declare metadata and enabled state:
    ---
    name: My Skill
    description: What this skill does
    enabled: true      # set to false to disable without deleting the file
    load: always       # always | on-demand (on-demand = excluded from auto-load)
    ---

Usage:
    python3 scripts/generate.py opencode        print OPENCODE_CONFIG_CONTENT to stdout
    python3 scripts/generate.py claude          write .mcp.json + CLAUDE.md
    python3 scripts/generate.py cursor          write .cursor/mcp.json
    python3 scripts/generate.py vscode          write .vscode/mcp.json
    python3 scripts/generate.py continue        write .continue/mcpServers/manager.json
    python3 scripts/generate.py all             write all file-based harness configs

To add a new harness: add a writer function and entry in COMMANDS below.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
REGISTRY = ROOT / "registry"


# ── Frontmatter parsing ───────────────────────────────────────────────────────

def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Return (metadata dict, body string) from a markdown file with YAML frontmatter."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    meta: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        # Parse booleans
        if val.lower() == "true":
            meta[key.strip()] = True
        elif val.lower() == "false":
            meta[key.strip()] = False
        # Parse lists [a, b, c]
        elif val.startswith("[") and val.endswith("]"):
            meta[key.strip()] = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = val.strip('"').strip("'")

    return meta, parts[2].strip()


def load_enabled_files(folder: Path) -> list[Path]:
    """Return paths of .md files where frontmatter has enabled: true (or no frontmatter)."""
    if not folder.exists():
        return []
    enabled = []
    for path in sorted(folder.glob("*.md")):
        meta, _ = parse_frontmatter(path)
        # Default to enabled if no frontmatter or no enabled key
        if meta.get("enabled", True):
            enabled.append(path)
    return enabled


def load_registry() -> tuple[dict, dict]:
    mcp = json.loads((REGISTRY / "mcp-servers.json").read_text())
    models = json.loads((REGISTRY / "models.json").read_text())
    return mcp, models


def build_instructions_list() -> list[str]:
    """
    Collect enabled instruction files from registry/ in load order:
      1. context.md (base persona)
      2. skills/*.md  (enabled only)
      3. rules/*.md   (enabled only)
    Returns paths relative to ROOT.
    """
    files: list[Path] = []

    base = REGISTRY / "context.md"
    if base.exists():
        meta, _ = parse_frontmatter(base)
        if meta.get("enabled", True):
            files.append(base)

    files.extend(load_enabled_files(REGISTRY / "skills"))
    files.extend(load_enabled_files(REGISTRY / "rules"))

    return [str(f.relative_to(ROOT)) for f in files]


def concatenate_instructions() -> str:
    """Return the full concatenated content of all enabled instruction files."""
    parts = []
    for rel in build_instructions_list():
        path = ROOT / rel
        _, body = parse_frontmatter(path)
        parts.append(body)
    return "\n\n---\n\n".join(parts)


# ── Transformers ──────────────────────────────────────────────────────────────

def to_opencode(mcp: dict, models: dict, instructions: list[str]) -> dict:
    """Standard mcpServers format → OpenCode mcp format."""
    mcp_block = {}
    for name, server in mcp["mcpServers"].items():
        cmd = [server["command"]] + server.get("args", [])
        entry: dict = {"type": "local", "command": cmd, "enabled": True}
        if "env" in server:
            entry["environment"] = server["env"]
        mcp_block[name] = entry

    ollama_models = {m.split("/")[-1]: {"name": m.split("/")[-1]} for m in models.get("allowed", [])}

    return {
        "$schema": "https://opencode.ai/config.json",
        "model": models["default"],
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "options": {"baseURL": models["ollama"]["baseURL"]},
                "models": ollama_models,
            }
        },
        "mcp": mcp_block,
        "instructions": instructions,
    }


# ── Writers ───────────────────────────────────────────────────────────────────

def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"  wrote {path.relative_to(ROOT)}", file=sys.stderr)


def cmd_opencode() -> None:
    """Print OPENCODE_CONFIG_CONTENT JSON to stdout (captured by manager script)."""
    mcp, models = load_registry()
    instructions = build_instructions_list()
    config = to_opencode(mcp, models, instructions)
    # Print skill names being loaded so manager can show them
    print(f"  skills loaded: {[Path(p).stem for p in instructions]}", file=sys.stderr)
    print(json.dumps(config))


def cmd_claude() -> None:
    """Write .mcp.json and CLAUDE.md for Claude Code."""
    mcp, _ = load_registry()
    write(ROOT / ".mcp.json", mcp)
    # Claude Code reads CLAUDE.md as system prompt
    (ROOT / "CLAUDE.md").write_text(concatenate_instructions())
    print(f"  wrote CLAUDE.md ({len(build_instructions_list())} skill files)", file=sys.stderr)


def cmd_cursor() -> None:
    mcp, _ = load_registry()
    write(ROOT / ".cursor" / "mcp.json", mcp)


def cmd_vscode() -> None:
    mcp, _ = load_registry()
    write(ROOT / ".vscode" / "mcp.json", mcp)


def cmd_continue() -> None:
    mcp, _ = load_registry()
    write(ROOT / ".continue" / "mcpServers" / "manager.json", mcp)


def cmd_all() -> None:
    print("Generating harness configs from registry...", file=sys.stderr)
    cmd_claude()
    cmd_cursor()
    cmd_vscode()
    cmd_continue()


COMMANDS = {
    "opencode": cmd_opencode,
    "claude":   cmd_claude,
    "cursor":   cmd_cursor,
    "vscode":   cmd_vscode,
    "continue": cmd_continue,
    "all":      cmd_all,
}

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "opencode"
    if target not in COMMANDS:
        print(f"Unknown target: {target}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[target]()
