#!/usr/bin/env python3
"""
crons_ui.py — terminal UI for viewing and managing manager cron jobs

Shows all jobs registered in registry/crons.md alongside their launchd status,
last run time, and recent log output.

Usage (via manager script):
    ./manager crons          show status table
    ./manager crons logs <id>  tail logs for a job
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
CRONS_FILE = ROOT / "registry" / "crons.md"
AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
CACHE_DIR = ROOT / ".cache"
PREFIX = "manager"

# ── Terminal colors (no dependencies) ────────────────────────────────────────

BOLD  = "\033[1m"
DIM   = "\033[2m"
GREEN = "\033[32m"
YELLOW= "\033[33m"
RED   = "\033[31m"
CYAN  = "\033[36m"
RESET = "\033[0m"

def bold(s):   return f"{BOLD}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"
def green(s):  return f"{GREEN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"


# ── Parse crons.md ────────────────────────────────────────────────────────────

def parse_crons() -> list[dict]:
    """Read the Active Jobs table from registry/crons.md."""
    jobs = []
    in_table = False
    for line in CRONS_FILE.read_text().splitlines():
        if "| ID |" in line or "| id |" in line.lower():
            in_table = True
            continue
        if not in_table:
            continue
        if re.match(r"^\s*\|[-| ]+\|\s*$", line):
            continue
        if not line.strip().startswith("|"):
            in_table = False
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 4:
            continue
        job_id, schedule, what, command = parts[0], parts[1], parts[2], parts[3]
        if not job_id or job_id.lower() == "id":
            continue
        jobs.append({"id": job_id, "schedule": schedule, "what": what, "command": command})
    return jobs


# ── Query launchd status ──────────────────────────────────────────────────────

def launchd_status(job_id: str) -> dict:
    """Return launchd info for a job label."""
    label = f"{PREFIX}.{job_id}"
    try:
        out = subprocess.check_output(
            ["launchctl", "list", label],
            stderr=subprocess.DEVNULL, text=True
        )
        pid_match = re.search(r'"PID"\s*=\s*(\d+)', out)
        exit_match = re.search(r'"LastExitStatus"\s*=\s*(\d+)', out)
        return {
            "loaded": True,
            "pid": pid_match.group(1) if pid_match else None,
            "last_exit": int(exit_match.group(1)) if exit_match else None,
        }
    except subprocess.CalledProcessError:
        return {"loaded": False, "pid": None, "last_exit": None}


def plist_exists(job_id: str) -> bool:
    return (AGENTS_DIR / f"{PREFIX}.{job_id}.plist").exists()


def last_log_line(job_id: str) -> str:
    log = CACHE_DIR / f"cron-{job_id}.log"
    if not log.exists():
        return dim("no logs yet")
    lines = log.read_text().strip().splitlines()
    last = lines[-1] if lines else ""
    return dim(last[:60] + "…" if len(last) > 60 else last)


def log_mtime(job_id: str) -> str:
    log = CACHE_DIR / f"cron-{job_id}.log"
    if not log.exists():
        return dim("—")
    ts = datetime.fromtimestamp(log.stat().st_mtime)
    return dim(ts.strftime("%Y-%m-%d %H:%M"))


# ── Status table ──────────────────────────────────────────────────────────────

def status_table():
    jobs = parse_crons()

    if not jobs:
        print(f"\n  {yellow('No jobs found in registry/crons.md')}")
        print(f"  Edit that file to add scheduled tasks.\n")
        return

    # Column widths
    col = {"id": 18, "schedule": 18, "what": 26, "status": 10, "last_run": 17, "log": 40}

    def row(*cells, header=False):
        fmt = bold if header else lambda x: x
        parts = list(cells)
        widths = list(col.values())
        line = "  "
        for part, w in zip(parts, widths):
            # Strip ANSI for length calculation
            clean = re.sub(r"\033\[[0-9;]*m", "", str(part))
            pad = max(0, w - len(clean))
            line += str(part) + " " * pad + "  "
        print(fmt(line) if header else line)

    term_width = os.get_terminal_size().columns if sys.stdout.isatty() else 100
    print()
    print(f"  {bold('Manager — Cron Jobs')}")
    print(f"  {dim('registry/crons.md  →  macOS launchd')}")
    print(f"  {dim('─' * min(term_width - 4, 110))}")

    row("JOB", "SCHEDULE", "DESCRIPTION", "STATUS", "LAST RUN", "LAST LOG LINE", header=True)
    print(f"  {dim('─' * min(term_width - 4, 110))}")

    for job in jobs:
        st = launchd_status(job["id"])
        installed = plist_exists(job["id"])

        if not installed:
            status = yellow("not synced")
        elif st["loaded"] and st["pid"]:
            status = green("running")
        elif st["loaded"] and st["last_exit"] == 0:
            status = green("idle ✓")
        elif st["loaded"] and st["last_exit"] is not None and st["last_exit"] != 0:
            status = red(f"error ({st['last_exit']})")
        elif st["loaded"]:
            status = green("loaded")
        else:
            status = yellow("unloaded")

        row(
            cyan(job["id"]),
            job["schedule"],
            job["what"],
            status,
            log_mtime(job["id"]),
            last_log_line(job["id"]),
        )

    print(f"  {dim('─' * min(term_width - 4, 110))}")
    print()
    print(f"  {dim('Commands:')}")
    print(f"  {dim('./manager crons sync')}      {dim('— install/update jobs from crons.md')}")
    print(f"  {dim('./manager crons logs <id>')} {dim('— tail logs for a job')}")
    print(f"  {dim('./manager briefing')}         {dim('— send Telegram briefing now')}")
    print()


# ── Log tail ──────────────────────────────────────────────────────────────────

def tail_logs(job_id: str, lines: int = 40):
    log = CACHE_DIR / f"cron-{job_id}.log"
    err = CACHE_DIR / f"cron-{job_id}.err"

    print(f"\n  {bold(f'Logs — {job_id}')}")
    print(f"  {dim(str(log))}\n")

    if log.exists():
        content = log.read_text().strip().splitlines()
        for line in content[-lines:]:
            print(f"  {line}")
    else:
        print(f"  {dim('No log file yet. Has the job run?')}")

    if err.exists() and err.stat().st_size > 0:
        print(f"\n  {bold(red('Stderr:'))}")
        for line in err.read_text().strip().splitlines()[-20:]:
            print(f"  {red(line)}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "status":
        status_table()
    elif args[0] == "logs" and len(args) > 1:
        tail_logs(args[1])
    elif args[0] == "logs":
        print("Usage: ./manager crons logs <job-id>")
        sys.exit(1)
    else:
        status_table()
