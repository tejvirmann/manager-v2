#!/usr/bin/env bash
# crons.sh — sync registry/crons.md to macOS launchd
# Run via: ./manager crons
#
# Reads the Active Jobs table in registry/crons.md and installs/removes
# launchd plist files in ~/Library/LaunchAgents/manager.<id>.plist

set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
CRONS_FILE="$DIR/registry/crons.md"
AGENTS_DIR="$HOME/Library/LaunchAgents"
PREFIX="manager"

G='\033[0;32m'; Y='\033[1;33m'; B='\033[1m'; NC='\033[0m'
step()   { echo -e "${G}▶${NC} $1"; }
warn()   { echo -e "${Y}⚠${NC}  $1"; }
header() { echo -e "\n${B}── $1 ──${NC}"; }

[[ -f "$DIR/.env" ]] && { set -a; source "$DIR/.env"; set +a; }

header "Syncing cron jobs from registry/crons.md"

# ── Parse active jobs from the markdown table ─────────────────────────────────
# Expects rows like: | id | schedule | description | command |
declare -A ACTIVE_IDS

while IFS='|' read -r _ id schedule what command _; do
  id=$(echo "$id" | xargs)
  schedule=$(echo "$schedule" | xargs)
  command=$(echo "$command" | xargs)

  # Skip header rows, empty rows, separator rows
  [[ -z "$id" || "$id" == "ID" || "$id" =~ ^-+$ ]] && continue
  [[ -z "$schedule" || -z "$command" ]] && continue

  ACTIVE_IDS["$id"]=1
  PLIST="$AGENTS_DIR/${PREFIX}.${id}.plist"

  # Parse cron schedule into launchd StartCalendarInterval
  HOUR=$(echo "$schedule" | awk '{print $2}')
  MINUTE=$(echo "$schedule" | awk '{print $1}')

  step "Installing: $id ($schedule)"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PREFIX}.${id}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>cd ${DIR} &amp;&amp; ${command}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>${HOUR}</integer>
    <key>Minute</key>
    <integer>${MINUTE}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${DIR}/.cache/cron-${id}.log</string>
  <key>StandardErrorPath</key>
  <string>${DIR}/.cache/cron-${id}.err</string>
</dict>
</plist>
EOF

  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  step "Loaded $id"

done < <(grep '|' "$CRONS_FILE")

# ── Remove plists for jobs no longer in the file ──────────────────────────────
for plist in "$AGENTS_DIR"/${PREFIX}.*.plist; do
  [[ -f "$plist" ]] || continue
  id=$(basename "$plist" | sed "s/^${PREFIX}\\.//;s/\\.plist$//")
  if [[ -z "${ACTIVE_IDS[$id]+_}" ]]; then
    warn "Removing deleted job: $id"
    launchctl unload "$plist" 2>/dev/null || true
    rm "$plist"
  fi
done

echo ""
echo -e "${G}✓${NC} Cron jobs synced."
echo "  Logs: .cache/cron-<id>.log"
echo "  List installed: launchctl list | grep manager"
