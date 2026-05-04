# How Manager Works

A harness-agnostic personal AI assistant. A local LLM (via Ollama) with live access to your GitHub board, notes, and calendar. Accessible from your terminal or phone.

---

## Getting Started

### 1. Install prerequisites

```bash
# Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Ollama — runs the LLM locally
brew install ollama

# OpenCode — the TUI/CLI harness
brew install opencode   # or check https://opencode.ai for latest install

# Node.js — needed for the filesystem MCP (npx)
brew install node
```

No Docker needed. The GitHub MCP server is a standalone binary downloaded by setup.

### 2. Pull Ollama models

```bash
ollama pull gemma4:e4b        # primary model (~9.6GB, fits on 16GB M1)
ollama pull qwen2.5-coder:7b  # coding sessions (optional, ~5GB)
```

### 3. Configure tokens

```bash
cd ~/Documents/manager-v2

cp .env.example .env
```

Open `.env` and fill in:
```
GITHUB_PAT=ghp_your_token_here          # github.com/settings/tokens
GITHUB_REPO=Tejvir-PM-Stack/manager     # already set
```

PAT scopes needed: `repo`, `read:org`, `project`

### 4. Run the setup wizard (optional — does steps 2-3 interactively)

```bash
./manager setup
```

### 5. Start the agent

```bash
./manager
```

That opens the OpenCode TUI. You're live.

---

## All commands

```bash
./manager                  # start OpenCode TUI (default)
./manager opencode         # same
./manager claude           # start Claude Code CLI instead
./manager setup            # interactive config wizard
./manager index            # manually rebuild notes search index
./manager bot              # start Telegram bot
./manager setup-cursor     # write .cursor/mcp.json for Cursor
./manager setup-vscode     # write .vscode/mcp.json for VS Code
./manager setup-continue   # write .continue/mcpServers/ for Continue
./manager setup-all        # write all file-based harness configs
```

---

## How it works

### What happens when you run `./manager`

```
./manager
  │
  ├─ 1. Load .env (tokens)
  ├─ 2. Rebuild notes index  →  .cache/notes-index.json
  ├─ 3. Read registry/skills/*.md frontmatter → filter enabled: true
  ├─ 4. Build OPENCODE_CONFIG_CONTENT (dynamic config with only enabled skills)
  └─ 5. Start OpenCode TUI
              │
              ├─ GitHub MCP  (Docker container)  →  GitHub API
              └─ Filesystem MCP  (npx process)   →  notes/, calendar/, .cache/
```

### The registry — what you edit

```
registry/
  context.md          ← base persona, always loaded
  skills/
    github.md         ← GitHub board rules  (enabled: true/false in frontmatter)
    notes.md          ← notes search + calendar rules
  rules/              ← formatting, behavior overrides (empty — add files here)
  mcp-servers.json    ← canonical MCP list in standard format (for other harnesses)
  models.json         ← model config reference
```

**To change agent behavior** → edit `registry/context.md` or any skill file. Changes apply next `./manager` run. No restart.

**To add a skill** → drop a `.md` file with frontmatter into `registry/skills/`. It's injected automatically.

**To disable a skill** → set `enabled: false` in its frontmatter. The file stays, the skill is excluded.

**To add an MCP server** → add it to `registry/mcp-servers.json` AND `opencode.jsonc`.

### Skill frontmatter

Every file in `registry/skills/` and `registry/rules/` uses YAML frontmatter to declare its state:

```markdown
---
name: GitHub Project Management
description: Issue tracking and board management
enabled: true
---

Skill content here...
```

`scripts/generate.py` reads the frontmatter of every skill file and only includes the ones where `enabled: true` in the session config. This is injected via `OPENCODE_CONFIG_CONTENT` which takes priority over `opencode.jsonc`.

`opencode.jsonc` has a glob fallback (`registry/skills/*.md`) for if you run `opencode` directly — but `./manager` always uses the frontmatter-gated dynamic version.

### Two layers of lazy loading

| Layer | What | How |
|---|---|---|
| Notes | Full file content | Index has title/tags/summary per file. Full content only read on demand by the agent. |
| Skills | Which skills are injected | `generate.py` reads frontmatter, filters `enabled: true`, only those files become context. |

### MCP servers

MCP (Model Context Protocol) — how the LLM calls external tools. Two servers launch as subprocesses when OpenCode starts:

**GitHub MCP** — Docker container:
- List, create, update, close issues
- Move items on the project board (board view + roadmap/timeline)
- Search issues by label, assignee, milestone
- Talks to `Tejvir-PM-Stack/manager`

**Filesystem MCP** — npx process:
- Read and write files inside `notes/`, `calendar/`, `.cache/` only
- Nothing outside those folders is reachable

### Notes index

`tools/build_index.py` runs before every session. It scans `notes/` and `calendar/`, reads the YAML frontmatter of each `.md` file, and writes `.cache/notes-index.json` — a compact list of title, tags, date, project, and a 300-char summary per file.

The agent searches this index first. It only reads the full file when it actually needs the content.

Notes the agent creates:
```markdown
---
title: Meeting with Buck
date: 2026-05-05
tags: [meetings, land]
project: land-deal
---

Content here...
```

### Telegram bot

```bash
./manager bot
```

A Python process that bridges your phone to the agent. It:
- Rejects all messages except from your whitelisted Telegram user ID
- Calls Ollama directly (same model, no OpenCode dependency)
- Loads the notes index for context on every message

Phone commands: `/issues`, `/briefing`, or any free-text message.

---

## Harness-agnostic design

The registry is defined once. `scripts/generate.py` translates it into each harness's format:

| Harness | Config generated | Format |
|---|---|---|
| **OpenCode** | `OPENCODE_CONFIG_CONTENT` (env var) | OpenCode schema |
| **Claude Code** | `.mcp.json` + `CLAUDE.md` | Standard `mcpServers` |
| **Cursor** | `.cursor/mcp.json` | Standard `mcpServers` |
| **VS Code** | `.vscode/mcp.json` | Standard `mcpServers` |
| **Continue** | `.continue/mcpServers/manager.json` | Standard `mcpServers` |

To add a new harness: add a writer function in `scripts/generate.py` and a case in the `manager` script.

---

## Security

| What | Protection |
|---|---|
| GitHub token | `.env` only, gitignored, never committed |
| Filesystem access | MCP locked to `notes/`, `calendar/`, `.cache/` |
| GitHub access | Scoped PAT — only `Tejvir-PM-Stack/manager` |
| Ollama | Localhost only, never exposed to network |
| Telegram bot | Whitelist — rejects all user IDs except yours |

---

## Sharing

The repo at `github.com/tejvirmann/manager-v2` is code only — no tokens, no notes, no calendar data. Anyone installs with:

```bash
curl -fsSL https://raw.githubusercontent.com/tejvirmann/manager-v2/main/install.sh | bash
cd ~/manager
./manager setup   # enter their own tokens
./manager         # start
```
