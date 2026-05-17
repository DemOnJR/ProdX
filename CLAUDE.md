# Claude Code instructions for the ProdX repo

## TL;DR

- **Work on `dev`. Never commit to `main`.**
- `main` is updated **only via pull requests** (`dev → main`), squash-merged in the GitHub UI.
- The `sync-dev-with-main.yml` workflow auto-resets `dev` after every merge. Just `git pull` before starting new work — no manual reset recipe to remember.

## Branch model

This repo uses GitHub Flow with one long-lived working branch:

| Branch | Role | Updated by |
|---|---|---|
| `main` | Production source of truth. CI publishes images from here to GAR. | Squash-merging PRs from `dev`. Direct pushes blocked. |
| `dev` | Where all work happens. | Direct pushes are fine. Auto-synced to `main` after every PR merge. |

Argo CD reconciles the `main` branch of the **ProdXCD** repo into the GKE cluster — but this repo (ProdX) is application code only. CI on `main` publishes container images to Artifact Registry; Argo picks them up via the Helm chart in ProdXCD on its own ~3-minute poll loop.

## Workflow

```
git checkout dev && git pull              # start from the freshly-synced dev tip
…edit files, commit on dev…
git push origin dev                       # no CI fires on dev push (intentional)
# Open PR dev → main at https://github.com/DemOnJR/ProdX/compare/main...dev
# Wait for CI green, squash-merge in the UI
# sync-dev-with-main.yml fires automatically, resets origin/dev = origin/main
# Next `git pull` on your local dev brings you to the post-merge state
```

## What the PreToolUse hook enforces

`.claude/hooks/prevent-main-push.sh` blocks two operations server-side (i.e. before Claude can even attempt them):

1. Any `git push` whose target ref is `main` — including the `--force` / `HEAD:main` / `:main` variants.
2. Any `git commit` while the currently-checked-out branch is `main`.

If you hit the block: `git checkout dev` and do the work there. There's no legitimate reason to bypass the PR flow in this repo — branch protection on `main` would reject the push anyway; the hook just stops you from wasting a network round-trip.

## Why squash-merge + auto-sync

GitHub gives three merge styles. The trade-off:

| Style | Main history | Dev branch state after merge |
|---|---|---|
| **Squash** (this repo) | One clean commit per feature | Drifts ("N ahead, 1 behind") because squash creates a new SHA |
| Merge commit | Noisy ("WIP", "fix typo", merge commits) | Stays clean — original commits land verbatim |
| Rebase merge | Linear, all individual commits | Drifts because commits get rewritten with new SHAs |

We picked squash for clean `main` history, then automated the drift fix so you never have to deal with it. See `sync-dev-with-main.yml` for the 1-job auto-reset.
