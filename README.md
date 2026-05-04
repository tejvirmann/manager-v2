# Manager

A harness-agnostic personal AI assistant that runs locally. Connects a local LLM (via Ollama) to your GitHub project board, notes, and calendar. Accessible from your terminal or phone via Telegram.

---

## What it does

- **GitHub board** — create, update, close issues; move cards on the board; set timeline dates on the roadmap view
- **Notes** — search, create, and organize markdown notes with frontmatter indexing (lazy-loaded, fast even at scale)
- **Calendar** — read and update a local calendar folder
- **Telegram** — message your assistant from your phone, get daily briefings and issue summaries
- **Harness-agnostic** — works with OpenCode, Claude Code, Cursor, VS Code, or Continue. Switch with one command.

Everything runs locally. No cloud, no subscriptions, no data leaves your machine except GitHub API calls.

---

## Stack

| Layer | What |
|---|---|
| LLM | [Ollama](https://ollama.com) — local, private |
| Default model | `gemma4:e4b` (4B, 9.6GB, strong tool use) |
| Harness | [OpenCode](https://opencode.ai) — TUI + CLI |
| GitHub | `github-mcp-server` — official GitHub MCP binary |
| Filesystem | `@modelcontextprotocol/server-filesystem` |
| Mobile | Telegram bot (Python) |

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/tejvirmann/manager-v2/main/install.sh | bash
cd ~/manager
./manager setup
./manager
```

**Prerequisites** (installed automatically on macOS):
- [Ollama](https://ollama.com)
- [OpenCode](https://opencode.ai)
- Node.js
- Python 3

No Docker required.

---

## Commands

```bash
./manager              # start OpenCode TUI (default)
./manager claude       # start Claude Code instead
./manager bot          # start Telegram bot
./manager setup        # first-time config wizard
./manager index        # rebuild notes search index
./manager setup-cursor    # generate Cursor MCP config
./manager setup-vscode    # generate VS Code MCP config
./manager setup-continue  # generate Continue MCP config
./manager setup-all       # generate all harness configs
```

---

## Customizing

All agent behavior lives in `registry/` — edit these files, changes apply on next `./manager` run:

```
registry/
  context.md        ← base persona and instructions
  skills/
    github.md       ← GitHub board rules
    notes.md        ← notes search and calendar rules
  rules/            ← drop .md files here for formatting/behavior overrides
  mcp-servers.json  ← MCP server list (standard format, used by other harnesses)
  models.json       ← allowed Ollama models
```

**To add a skill** — drop a `.md` file in `registry/skills/` with this frontmatter:

```markdown
---
name: My Skill
description: What this skill does
enabled: true
---

Skill instructions here...
```

**To disable a skill** — set `enabled: false` in its frontmatter.

**To switch models** — edit `"model"` in `opencode.jsonc`.

---

## How it works

See [HOW_IT_WORKS.md](HOW_IT_WORKS.md) for a full breakdown of the architecture, lazy loading, harness-agnostic design, and security model.

---

## Security

- Secrets live in `.env` only — gitignored, never committed
- Filesystem MCP is scoped to `notes/`, `calendar/`, `.cache/` only
- Ollama runs on localhost — never exposed to the network
- Telegram bot rejects all senders except your whitelisted user ID
- GitHub PAT is scoped to the tracking repo only
