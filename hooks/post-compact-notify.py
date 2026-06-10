#!/usr/bin/env python3
"""SessionStart(compact) hook: tell post-compact Claude where its full memory is.

Whatever this prints to stdout gets injected into the fresh context by the
Claude Code harness.
"""
import json
import os
import sys

OUT_DIR = os.path.expanduser("~/claude-context")


def newest_dump():
    if not os.path.isdir(OUT_DIR):
        return None
    dumps = [
        os.path.join(OUT_DIR, f)
        for f in os.listdir(OUT_DIR)
        if f.endswith("-context.md")
    ]
    return max(dumps, key=os.path.getmtime) if dumps else None


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    session_id = hook_input.get("session_id", "")
    pointer = os.path.join(OUT_DIR, f".latest-{session_id}")
    path = None
    if os.path.exists(pointer):
        with open(pointer) as f:
            path = f.read().strip()
    if not path or not os.path.exists(path):
        path = newest_dump()

    if path and os.path.exists(path):
        print(
            "NOTE: This conversation was just compacted, so your current context is "
            f"only a lossy summary. The COMPLETE pre-compact transcript was saved to:\n"
            f"  {path}\n"
            "If the user refers to anything you don't recognize (files, configs, "
            "decisions, earlier debugging), Read that file to recover the details "
            "instead of guessing or asking the user to repeat themselves."
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
