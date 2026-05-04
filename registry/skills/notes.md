---
name: Notes and Calendar
description: Lazy-loaded note search via frontmatter index, and calendar file management
enabled: true
load: always
tags: [notes, calendar, pkm, search]
---

## Notes search — lazy loading

The notes index at `.cache/notes-index.json` is rebuilt every session. It contains title, tags, date, project, and a 300-character summary for every note — search this first.

1. **Search the index first** — never read full files just to find something
2. **Read the full file only** when you need its complete content
3. Check the index before asking the user for context they may have already written down

## Creating notes

Always write YAML frontmatter:
```
---
title: Note Title
date: YYYY-MM-DD
tags: [tag1, tag2]
project: project-name
---
```
Suggest relevant tags and a project name when creating notes.

## Calendar

- Events and deadlines live in `./calendar/` as markdown files
- Read those files when asked about schedule or upcoming deadlines
- Keep entries in chronological order with ISO dates (YYYY-MM-DD)
- For daily briefings: include upcoming events alongside open GitHub issues
