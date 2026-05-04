"""
telegram_bot.py — Telegram bridge for the manager assistant

Whitelist-gated: only TELEGRAM_ALLOWED_USER_ID can send messages.
Calls Ollama directly (no OpenCode dependency) using the same model and system prompt.
GitHub operations go via the REST API directly.

Start via: ./manager bot
"""
import json
import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv(Path(__file__).parent.parent / ".env")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_UID = int(os.environ["TELEGRAM_ALLOWED_USER_ID"])
GITHUB_PAT = os.environ.get("GITHUB_PAT", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("TELEGRAM_MODEL", "gemma4:e4b")
INDEX_PATH = os.environ.get("NOTES_INDEX_PATH", str(Path(__file__).parent.parent / ".cache/notes-index.json"))

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a personal project manager assistant replying via Telegram. "
    "Be concise — Telegram messages should be short and scannable. "
    "Use plain bullet points (•), not markdown headers. "
    "You have context from the user's notes and GitHub issues. "
    "Prioritize surfacing blocked work and upcoming deadlines."
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_notes_index() -> list[dict]:
    try:
        return json.loads(Path(INDEX_PATH).read_text())
    except Exception:
        return []


def github_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_issues(state: str = "open", limit: int = 20) -> list[dict]:
    if not GITHUB_PAT or not GITHUB_REPO:
        return []
    try:
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            params={"state": state, "per_page": limit},
            headers=github_headers(),
            timeout=10,
        )
        return r.json() if r.ok else []
    except Exception:
        return []


def ollama_chat(messages: list[dict], timeout: int = 90) -> str:
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": MODEL, "messages": messages, "stream": False},
            timeout=timeout,
        )
        return r.json()["message"]["content"] if r.ok else f"Ollama error: {r.status_code}"
    except Exception as e:
        return f"Could not reach Ollama: {e}"


def notes_context(limit: int = 15) -> str:
    notes = load_notes_index()
    if not notes:
        return ""
    recent = notes[:limit]
    lines = [f"- {n['title']} [{', '.join(n.get('tags', []))}] ({n['date']})" for n in recent]
    return "Recent notes:\n" + "\n".join(lines)


def truncate(text: str, max_len: int = 4000) -> str:
    return text[:max_len] + "…" if len(text) > max_len else text


# ── Auth guard ────────────────────────────────────────────────────────────────

async def guard(update: Update) -> bool:
    if update.effective_user.id != ALLOWED_UID:
        await update.message.reply_text("Unauthorized.")
        return False
    return True


# ── Commands ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(
        "Manager bot ready.\n\n"
        "Commands:\n"
        "/issues — open GitHub issues\n"
        "/briefing — daily summary\n"
        "\nOr just ask anything."
    )


async def cmd_issues(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    issues = get_issues("open")
    if not issues:
        await update.message.reply_text(
            "No open issues found (or GitHub not configured in .env)."
        )
        return
    lines = [f"Open issues — {GITHUB_REPO}:"]
    for i in issues[:15]:
        labels = " ".join(f"[{l['name']}]" for l in i.get("labels", []))
        lines.append(f"• #{i['number']} {i['title']} {labels}".strip())
    await update.message.reply_text("\n".join(lines))


async def cmd_briefing(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text("Generating briefing…")

    issues = get_issues("open", limit=25)
    issue_summary = json.dumps(
        [{"number": i["number"], "title": i["title"], "labels": [l["name"] for l in i.get("labels", [])]}
         for i in issues[:20]],
        indent=2,
    )
    ctx_str = notes_context(20)

    prompt = (
        f"Generate a concise daily briefing. Include:\n"
        f"1. Top 5 most urgent open issues (repo: {GITHUB_REPO})\n"
        f"2. Any deadlines or time-sensitive notes from calendar context\n"
        f"3. Suggested top 3 priorities for today\n\n"
        f"Open issues:\n{issue_summary}\n\n"
        f"{ctx_str}"
    )

    reply = ollama_chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ], timeout=120)
    await update.message.reply_text(truncate(reply))


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return

    user_msg = update.message.text
    ctx_str = notes_context()

    system = SYSTEM_PROMPT
    if ctx_str:
        system += f"\n\nContext (notes index):\n{ctx_str}"

    await update.message.reply_text("…")

    reply = ollama_chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg},
    ])
    await update.message.reply_text(truncate(reply))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info(f"Starting bot. Allowed user: {ALLOWED_UID}, model: {MODEL}")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("issues", cmd_issues))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
