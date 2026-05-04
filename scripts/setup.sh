#!/usr/bin/env bash
# setup.sh — interactive config wizard
# Run via: ./manager setup

set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

G='\033[0;32m'; Y='\033[1;33m'; B='\033[1m'; NC='\033[0m'
step()   { echo -e "${G}▶${NC} $1"; }
ask()    { echo -e "${Y}?${NC}  $1"; }
header() { echo -e "\n${B}── $1 ──${NC}"; }

echo ""
echo -e "${B}Manager Setup Wizard${NC}"
echo "═══════════════════════"

# ── Existing .env ─────────────────────────────────────────────────────────────
CONFIGURE_ENV=true
if [[ -f "$DIR/.env" ]]; then
  echo ""
  read -r -p "⚠  .env already exists. Overwrite? [y/N] " yn
  [[ "$yn" == "y" || "$yn" == "Y" ]] || { step "Keeping existing .env."; CONFIGURE_ENV=false; }
fi

if [[ "$CONFIGURE_ENV" == "true" ]]; then
  cp "$DIR/.env.example" "$DIR/.env"

  # ── GitHub PAT ──────────────────────────────────────────────────────────────
  header "GitHub"
  echo "  1. Go to: https://github.com/settings/tokens"
  echo "  2. Create a Fine-grained or Classic token"
  echo "  3. Scopes needed: repo, read:org, project"
  echo ""
  ask "Paste your GitHub PAT (input hidden):"
  read -r -s GITHUB_PAT
  echo ""
  [[ -z "$GITHUB_PAT" ]] && { echo "PAT cannot be empty."; exit 1; }

  ask "GitHub repo to manage (format: owner/repo):"
  read -r GITHUB_REPO
  [[ -z "$GITHUB_REPO" ]] && { echo "Repo cannot be empty."; exit 1; }

  sed -i.bak "s|GITHUB_PAT=.*|GITHUB_PAT=$GITHUB_PAT|" "$DIR/.env"
  sed -i.bak "s|GITHUB_REPO=.*|GITHUB_REPO=$GITHUB_REPO|" "$DIR/.env"
  step "GitHub configured."

  # ── Telegram (optional) ─────────────────────────────────────────────────────
  header "Telegram Bot (optional)"
  echo "  Create a bot: open Telegram → search @BotFather → /newbot"
  echo "  Press Enter to skip."
  echo ""
  ask "Telegram bot token (or Enter to skip):"
  read -r -s TELEGRAM_TOKEN
  echo ""

  if [[ -n "$TELEGRAM_TOKEN" ]]; then
    sed -i.bak "s|TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN|" "$DIR/.env"
    echo "  Find your user ID: open Telegram → search @userinfobot → /start"
    ask "Your Telegram user ID (the number):"
    read -r TELEGRAM_UID
    [[ -n "$TELEGRAM_UID" ]] && sed -i.bak "s|TELEGRAM_ALLOWED_USER_ID=.*|TELEGRAM_ALLOWED_USER_ID=$TELEGRAM_UID|" "$DIR/.env"
    step "Telegram configured."
  else
    step "Skipped Telegram (add to .env later)."
  fi

  rm -f "$DIR/.env.bak"
fi

# ── Build notes index ─────────────────────────────────────────────────────────
header "Notes index"
mkdir -p "$DIR/.cache"
python3 "$DIR/tools/build_index.py" "$DIR" "$DIR/.cache/notes-index.json"
step "Index built at .cache/notes-index.json"

# ── Download GitHub MCP binary ────────────────────────────────────────────────
header "GitHub MCP Server"
ARCH=$(uname -m)
OS=$(uname -s)
[[ "$ARCH" == "arm64" ]] && BIN_ARCH="arm64" || BIN_ARCH="x86_64"
BIN_URL="https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server_${OS}_${BIN_ARCH}.tar.gz"
mkdir -p "$DIR/bin"

if [[ -f "$DIR/bin/github-mcp-server" ]]; then
  step "github-mcp-server already present — skipping download."
  step "To force update: rm bin/github-mcp-server && ./manager setup"
else
  step "Downloading github-mcp-server..."
  if curl -fsSL "$BIN_URL" | tar xz -C "$DIR/bin" github-mcp-server 2>/dev/null; then
    chmod +x "$DIR/bin/github-mcp-server"
    step "Downloaded to bin/github-mcp-server"
  else
    echo -e "${Y}⚠${NC}  Download failed. Check releases at:"
    echo "  https://github.com/github/github-mcp-server/releases"
    echo "  Place the binary at bin/github-mcp-server and chmod +x it."
  fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${G}✓${NC} Setup complete!"
echo ""
echo "  Start the agent:      ${B}./manager${NC}"
echo "  Start Telegram bot:   ${B}./manager bot${NC}"
echo ""
