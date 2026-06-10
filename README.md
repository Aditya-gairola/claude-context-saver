# claude-context-saver

Saves the full Claude Code conversation to a markdown file right before context
compaction, and tells the post-compact session where to find it.

## Problem

When a long Claude Code session fills its context window, it compacts: the
detailed conversation is replaced by a short lossy summary. File contents,
configs, and decisions from earlier in the session are lost, and Claude appears
unfamiliar with prior work. The raw transcript still exists on disk, but the
post-compact session is never told about it.

## How it works

Two hooks are registered in `~/.claude/settings.json`:

1. **PreCompact** — before any compaction (automatic or `/compact`), the full
   session transcript is converted to readable markdown and saved to
   `~/claude-context/<mon-dd-hh-mm>-context.md`.
2. **SessionStart (compact)** — immediately after compaction, a short note is
   injected into the fresh context with the path of the saved file, so Claude
   can read it to recover details instead of guessing.

The hooks are executed by the Claude Code harness itself, so this works in
every session on the machine with no per-chat setup.

## Install

```bash
git clone https://github.com/Aditya-gairola/claude-context-saver.git
cd claude-context-saver
./install.sh
```

Restart Claude Code afterwards, or run `/hooks` once in already-open sessions
to reload the configuration.

Requirements: Claude Code and python3.

## What install.sh does

- Copies `save-context.py` and `post-compact-notify.py` to `~/.claude/hooks/`
- Merges the hook entries into `~/.claude/settings.json`, preserving existing
  settings; re-running the installer does not create duplicates

Dumps are written to `~/claude-context/`. Existing files there are never
deleted or overwritten; name collisions get a numeric suffix.

## Configuration

- `MAX_TOOL_CHARS` in `hooks/save-context.py` controls truncation of large
  tool outputs in the dump (default 3000 characters)
- `OUT_DIR` in both scripts controls the dump folder

## Uninstall

Delete the two scripts from `~/.claude/hooks/` and remove their entries from
the `hooks` section of `~/.claude/settings.json`.
