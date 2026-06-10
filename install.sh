#!/usr/bin/env bash
# Installs the Claude Code context-saver hooks on this machine.
# - Copies the two hook scripts to ~/.claude/hooks/
# - Merges the PreCompact + SessionStart hook entries into ~/.claude/settings.json
#   (preserves everything already in the file)
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.claude/hooks"
cp "$REPO_DIR/hooks/save-context.py" "$REPO_DIR/hooks/post-compact-notify.py" "$HOME/.claude/hooks/"
chmod +x "$HOME/.claude/hooks/save-context.py" "$HOME/.claude/hooks/post-compact-notify.py"

python3 - <<'EOF'
import json, os

path = os.path.expanduser("~/.claude/settings.json")
settings = {}
if os.path.exists(path):
    with open(path) as f:
        settings = json.load(f)

hooks = settings.setdefault("hooks", {})
save_cmd = "python3 " + os.path.expanduser("~/.claude/hooks/save-context.py")
notify_cmd = "python3 " + os.path.expanduser("~/.claude/hooks/post-compact-notify.py")

def ensure(event, matcher, command, timeout, status=None):
    entries = hooks.setdefault(event, [])
    for entry in entries:
        if entry.get("matcher") == matcher:
            existing = [h.get("command") for h in entry.get("hooks", [])]
            if command not in existing:
                hook = {"type": "command", "command": command, "timeout": timeout}
                if status:
                    hook["statusMessage"] = status
                entry.setdefault("hooks", []).append(hook)
            return
    hook = {"type": "command", "command": command, "timeout": timeout}
    if status:
        hook["statusMessage"] = status
    entries.append({"matcher": matcher, "hooks": [hook]})

ensure("PreCompact", "auto", save_cmd, 120, "Saving full context to markdown before compact...")
ensure("PreCompact", "manual", save_cmd, 120, "Saving full context to markdown before compact...")
ensure("SessionStart", "compact", notify_cmd, 30)

with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
print("Hooks merged into " + path)
EOF

echo ""
echo "Installed. Context dumps will be saved to ~/claude-context/"
echo "Restart Claude Code (or run /hooks once in open sessions) to activate."
