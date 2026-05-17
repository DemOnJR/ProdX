#!/usr/bin/env bash
# PreToolUse hook for Bash commands in the ProdX repo.
#
# Blocks any operation that would mutate the `main` branch directly:
#   - `git push` with `main` as the target ref (any form, including
#     `origin main`, `HEAD:main`, `:main`, and `--force` variants)
#   - `git commit` while the current checked-out branch is `main`
#
# Allows everything else. The intent is to push Claude toward the
# documented PR-only flow: work on dev, push dev, open PR, merge in UI.
#
# Exit codes (per Claude Code hook spec):
#   0  → allow the tool call to proceed
#   2  → block the tool call; stderr is shown back to Claude as the reason
#
# See CLAUDE.md at the repo root for the full workflow rationale.

set -euo pipefail

# Claude pipes the tool call as JSON on stdin. Extract the `command` field.
# Done with a sed regex so we don't depend on jq / python3 (Windows ships
# a python3 shim that opens the Microsoft Store rather than running Python,
# so the obvious approach is portable-hostile).
#
# The regex pulls out the FIRST "command": "<value>" pair. Limitation: it
# doesn't handle escaped quotes inside the command. In practice nobody runs
# `bash -c "echo \"foo\""` through Claude, so this is fine.
input=$(cat)
cmd=$(printf '%s' "$input" \
  | sed -nE 's/.*"command"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/p' \
  | head -n1)

# Fail open if we couldn't parse — the hook is a safety net, not a security
# boundary (branch protection on main is the actual server-side gate).
[ -z "${cmd:-}" ] && exit 0

block() {
  {
    echo ""
    echo "❌ BLOCKED by .claude/hooks/prevent-main-push.sh"
    echo ""
    echo "   Reason: $1"
    echo ""
    echo "   This repo updates 'main' only via pull requests from 'dev'."
    echo "   The correct flow:"
    echo "     1. git checkout dev && git pull"
    echo "     2. make changes, commit on dev, git push origin dev"
    echo "     3. open PR dev → main at"
    echo "        https://github.com/DemOnJR/ProdX/compare/main...dev"
    echo "     4. squash-merge in the UI after CI is green"
    echo "     5. sync-dev-with-main.yml auto-resets dev (no manual reset)"
    echo ""
    echo "   See CLAUDE.md at the repo root for the full rationale."
  } >&2
  exit 2
}

# ─── Rule 1: block any `git push` targeting main ─────────────────────────
# Matches the common forms:
#   git push origin main
#   git push origin HEAD:main
#   git push origin :main           (branch delete)
#   git push --force origin main
#   git push -f origin main
#   git push origin <sha>:main
#   git push origin main:main
# Does NOT match `git push origin dev` or `git push origin feature/x:dev`.
if printf '%s' "$cmd" | grep -qE '(^|[^a-zA-Z0-9_-])git[[:space:]]+push\b'; then
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]:])main([[:space:]]|$|:)'; then
    block "git push targeting 'main' branch"
  fi
fi

# ─── Rule 2: block `git commit` while on main ────────────────────────────
# A `git commit` outside a git repo is harmless; if `git branch --show-current`
# errors out, fail open.
if printf '%s' "$cmd" | grep -qE '(^|[^a-zA-Z0-9_-])git[[:space:]]+commit\b'; then
  current_branch=$(git branch --show-current 2>/dev/null || echo "")
  if [ "$current_branch" = "main" ]; then
    block "git commit while the current branch is 'main'"
  fi
fi

exit 0
