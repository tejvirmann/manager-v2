#!/usr/bin/env bash
# install.sh — one-liner installer for manager
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/tejvirmann/manager-v2/main/install.sh | bash
#
# Or clone and run directly:
#   git clone https://github.com/tejvirmann/manager-v2 ~/manager && ~/manager/install.sh

set -euo pipefail

REPO="https://github.com/tejvirmann/manager-v2"
DEST="${MANAGER_DIR:-$HOME/manager}"

# ── Colors ────────────────────────────────────────────────────────────────────
B='\033[1m'; G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; NC='\033[0m'
step()   { echo -e "${G}▶${NC} $1"; }
warn()   { echo -e "${Y}⚠${NC}  $1"; }
die()    { echo -e "${R}✗${NC}  $1" >&2; exit 1; }
header() { echo -e "\n${B}── $1 ──${NC}"; }

echo ""
echo -e "${B}Manager — Personal AI Assistant${NC}"
echo "=================================="
echo "  Installs to: $DEST"
echo ""

# ── OS detection ──────────────────────────────────────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="linux"
else
  die "Unsupported OS: $OSTYPE (macOS and Linux only)"
fi

# ── Homebrew (macOS) ──────────────────────────────────────────────────────────
if [[ "$OS" == "macos" ]] && ! command -v brew &>/dev/null; then
  step "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# ── Prerequisites ─────────────────────────────────────────────────────────────
header "Checking prerequisites"

check() {
  local cmd="$1" pkg="${2:-$1}" url="${3:-}"
  if command -v "$cmd" &>/dev/null; then
    step "$cmd ✓"
  elif command -v brew &>/dev/null; then
    step "Installing $cmd..."
    brew install "$pkg"
  elif [[ "$OS" == "linux" ]]; then
    step "Installing $cmd..."
    sudo apt-get install -y "$pkg" 2>/dev/null || \
      die "$cmd not found. ${url:+Install from: $url}"
  else
    die "$cmd not found. ${url:+Install from: $url}"
  fi
}

check git git
check python3 python3 "https://python.org"
check ollama ollama "https://ollama.com"
check opencode opencode "https://opencode.ai"
check node node "https://nodejs.org"

# ── Clone or update repo ──────────────────────────────────────────────────────
header "Repository"

if [[ -d "$DEST/.git" ]]; then
  step "Updating existing installation at $DEST..."
  git -C "$DEST" pull --ff-only
else
  step "Cloning to $DEST..."
  git clone "$REPO" "$DEST"
fi

chmod +x "$DEST/manager"

# ── Pull Ollama models ────────────────────────────────────────────────────────
header "Ollama models"
step "Pulling gemma4:e4b (primary — ~9.6GB)..."
ollama pull gemma4:e4b
step "Pulling qwen2.5-coder:7b (coding — ~5GB)..."
ollama pull qwen2.5-coder:7b

# ── Download GitHub MCP binary ────────────────────────────────────────────────
header "GitHub MCP Server"
ARCH=$(uname -m)
OS=$(uname -s)
[[ "$ARCH" == "arm64" ]] && BIN_ARCH="arm64" || BIN_ARCH="x86_64"
BIN_URL="https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server_${OS}_${BIN_ARCH}.tar.gz"
mkdir -p "$DEST/bin"
step "Downloading github-mcp-server..."
if curl -fsSL "$BIN_URL" | tar xz -C "$DEST/bin" github-mcp-server 2>/dev/null; then
  chmod +x "$DEST/bin/github-mcp-server"
  step "Binary ready at bin/github-mcp-server"
else
  warn "Download failed — run './manager setup' to retry after install."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${G}✓${NC} Installation complete!"
echo ""
echo "  Next — run the setup wizard to configure your tokens:"
echo ""
echo -e "    ${B}cd $DEST${NC}"
echo -e "    ${B}./manager setup${NC}"
echo ""
echo "  Then start the agent:"
echo ""
echo -e "    ${B}./manager${NC}"
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
