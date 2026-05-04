# Build Plan — Manager

> This document captures the original design decisions. For current architecture, see HOW_IT_WORKS.md.

---

## Goal

A local AI assistant that:
- Manages a GitHub issue board (board + roadmap views) via the official GitHub MCP
- Indexes and searches personal notes and a calendar folder
- Runs a local LLM (Ollama) — no cloud, no subscriptions
- Works from the terminal (TUI) and from a phone (Telegram)
- Is harness-agnostic — swap OpenCode for Claude Code, Cursor, etc. without changing the registry

---

## Architecture decisions

### Harness: OpenCode
TUI + CLI, native Ollama support, MCP server config, `instructions` field for context injection. Config in `opencode.jsonc` (JSONC supports comments, `{env:VAR}` interpolation for secrets).

### Model: gemma4:e4b (default)
4B parameters, 9.6GB, fits on 16GB M1. Benchmarks at 86% on agentic/tool-use tasks — strongest tool use per GB available in Ollama. Alternatives: `qwen2.5-coder:7b` for coding sessions, `qwen2.5:7b` for speed.

### GitHub MCP: official binary
`github/github-mcp-server` — GitHub's own MCP server, distributed as a Go binary. Downloaded by `./manager setup` to `bin/` (gitignored). Supports issues, project board (board + roadmap), comments, search. Requires a PAT with `repo`, `read:org`, `project` scopes.

No Docker required.

### Notes: frontmatter index + filesystem MCP
`tools/build_index.py` scans `notes/` and `calendar/` at startup, reads YAML frontmatter, and writes `.cache/notes-index.json` — title, tags, date, project, 300-char summary per file. The agent searches the index first, reads full files only on demand. The filesystem MCP handles actual read/write.

### Skills: frontmatter-gated lazy loading
Each file in `registry/skills/` and `registry/rules/` has `enabled: true/false` in its frontmatter. `scripts/generate.py` reads the frontmatter and only includes enabled files in the session config via `OPENCODE_CONFIG_CONTENT`.

### Harness-agnostic registry
`registry/mcp-servers.json` — canonical MCP list in the standard `mcpServers` format (shared by Claude Code, Cursor, VS Code, Continue). `scripts/generate.py` transforms it into each harness's expected format. OpenCode uses `OPENCODE_CONFIG_CONTENT`; others get written files.

### Mobile: Telegram bot
`bot/telegram_bot.py` — Python, calls Ollama directly, whitelisted by user ID. Runs via `./manager bot`. Supports `/issues`, `/briefing`, and free-text queries.

---

## Repos

| Repo | Purpose |
|---|---|
| `tejvirmann/manager-v2` | Tool source code |
| `Tejvir-PM-Stack/manager` | GitHub board the agent manages |

---

## Tracking repo setup

GitHub board at `Tejvir-PM-Stack/manager` needs:
- Issues enabled
- A Project (board) created with status field (Todo / In Progress / Done)
- Optional: date fields (Start date, Target date) for roadmap view
- PAT with `repo`, `read:org`, `project` scopes
