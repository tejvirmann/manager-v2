---
name: Cron Jobs
description: Scheduled reminders and automations
enabled: true
---

# Scheduled Jobs

This file is the human-readable register of all automated tasks.
Run `./manager crons` to sync these to macOS launchd.

## Active Jobs

| ID | Schedule | What | Command |
|---|---|---|---|
| daily-briefing | 09:00 every day | Send Telegram briefing | `./manager briefing` |

## Adding a job

1. Add a row to the table above with a unique ID, schedule, description, and command
2. Run `./manager crons` to install it

## Removing a job

1. Delete or comment out the row
2. Run `./manager crons` to uninstall it

---

## Schedule syntax reference

| When | Cron expression |
|---|---|
| Every day at 9am | `0 9 * * *` |
| Every weekday at 8am | `0 8 * * 1-5` |
| Every hour | `0 * * * *` |
| Every Monday at 9am | `0 9 * * 1` |
