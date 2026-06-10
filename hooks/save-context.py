#!/usr/bin/env python3
"""PreCompact hook: dump the full session transcript to a readable markdown file.

Claude Code pipes hook input JSON on stdin, e.g.:
  {"session_id": "...", "transcript_path": "...jsonl", "trigger": "auto", ...}
Output: ~/claude-context-dumps/<mon-dd-hh-mmam/pm>-context.md
Also writes a pointer file .latest-<session_id> so the SessionStart hook
can tell post-compact Claude where the dump is.
"""
import datetime
import json
import os
import sys

OUT_DIR = os.path.expanduser("~/claude-context")
MAX_TOOL_CHARS = 3000  # truncate giant tool outputs so the dump stays readable


def render_block(block, lines):
    btype = block.get("type")
    if btype == "text":
        lines.append(block.get("text", ""))
        lines.append("")
    elif btype == "tool_use":
        lines.append(f"**Tool call:** `{block.get('name', '?')}`")
        lines.append("```json")
        lines.append(json.dumps(block.get("input", {}), indent=2)[:MAX_TOOL_CHARS])
        lines.append("```")
        lines.append("")
    elif btype == "tool_result":
        content = block.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                c.get("text", "")
                for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            )
        text = str(content)
        if len(text) > MAX_TOOL_CHARS:
            text = text[:MAX_TOOL_CHARS] + f"\n... [truncated {len(text) - MAX_TOOL_CHARS} chars]"
        lines.append("**Tool result:**")
        lines.append("```")
        lines.append(text)
        lines.append("```")
        lines.append("")
    # thinking blocks and unknown types are skipped on purpose


def find_last_boundary(path):
    """Line index and timestamp of the last compaction boundary, if any.

    Long-lived sessions keep one transcript across many compactions; everything
    before the last boundary was already handled by earlier dumps, so saving it
    again produces multi-MB files.
    """
    last, ts = -1, ""
    with open(path, "r", errors="replace") as f:
        for i, raw in enumerate(f):
            if '"compact_boundary"' not in raw:
                continue
            try:
                e = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
                last, ts = i, e.get("timestamp", "")
    return last, ts


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never block compaction on a parse error

    transcript_path = hook_input.get("transcript_path", "")
    session_id = hook_input.get("session_id", "unknown")
    if not transcript_path or not os.path.exists(transcript_path):
        sys.exit(0)

    os.makedirs(OUT_DIR, exist_ok=True)
    now = datetime.datetime.now()
    stamp = now.strftime("%b-%d-%I-%M%p").lower()
    out_path = os.path.join(OUT_DIR, f"{stamp}-context.md")
    n = 2
    while os.path.exists(out_path):  # two compactions in the same minute
        out_path = os.path.join(OUT_DIR, f"{stamp}-{n}-context.md")
        n += 1

    boundary_line, boundary_ts = find_last_boundary(transcript_path)
    covers = (
        f"conversation since the previous compaction ({boundary_ts})"
        if boundary_line >= 0 else "entire session"
    )

    lines = [
        "# Claude session context dump",
        f"- Session: {session_id}",
        f"- Saved: {now.isoformat(timespec='seconds')}",
        f"- Trigger: {hook_input.get('trigger', 'unknown')} compact",
        f"- Covers: {covers}",
        f"- Source transcript: {transcript_path}",
        "",
    ]

    with open(transcript_path, "r", errors="replace") as f:
        for i, raw in enumerate(f):
            if i <= boundary_line:
                continue
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if entry.get("isMeta"):
                continue
            etype = entry.get("type")
            if etype not in ("user", "assistant"):
                continue
            message = entry.get("message", {})
            content = message.get("content")
            header = "## 👤 User" if etype == "user" else "## 🤖 Claude"
            body = []
            if isinstance(content, str):
                if content.strip():
                    body.append(content)
                    body.append("")
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        render_block(block, body)
            if body:
                ts = entry.get("timestamp", "")
                lines.append(f"{header}  <sub>{ts}</sub>")
                lines.append("")
                lines.extend(body)

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    # pointer so the SessionStart(compact) hook knows the newest dump for this session
    with open(os.path.join(OUT_DIR, f".latest-{session_id}"), "w") as f:
        f.write(out_path)

    print(f"Context saved to {out_path}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
