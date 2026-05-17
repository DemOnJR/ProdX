# Claude Code instructions for the ProdX repo

## TL;DR

- **Work on `dev`. Never commit to `main`.**
- `main` is updated **only via pull requests** (`dev → main`), squash-merged in the GitHub UI.
- After every merge, **reset `dev` to match `main`** (recipe below) so your branch doesn't drift.

## CI layout

```
.github/workflows/
├── ci-backend.yml    single-job pipeline: lint → test → audit → build → Trivy → publish
└── ci-frontend.yml   single-job pipeline: typecheck → vite → audit → build → Trivy → publish
```

Each `ci-*.yml`:
- **Push to main:** path-filtered. Only the changed service republishes its image to GAR.
- **Pull request to main:** always runs (no PR path filter). Slightly wasteful in CI minutes when a PR only touches one service, but means the required "🛡️ Scan image" status checks are always posted — no skip-stub workflow needed.

## Branch model

This repo uses GitHub Flow with one long-lived working branch:

| Branch | Role | Updated by |
|---|---|---|
| `main` | Production source of truth. CI publishes images from here to GAR. | Squash-merging PRs from `dev`. Direct pushes blocked. |
| `dev` | Where all work happens. | Direct pushes are fine. Reset to `main` after each PR merge (see below). |

Argo CD reconciles the `main` branch of the **ProdXCD** repo into the GKE cluster — but this repo (ProdX) is application code only. CI on `main` publishes container images to Artifact Registry; Argo picks them up via the Helm chart in ProdXCD on its own ~3-minute poll loop.

## Workflow

```bash
git checkout dev && git pull              # start from the latest dev
…edit files, commit on dev…
git push origin dev                       # no CI fires on dev push (intentional)
# Open PR dev → main at https://github.com/DemOnJR/ProdX/compare/main...dev
# Wait for CI green, squash-merge in the UI

# After merge: reset dev to match main (drops the now-redundant originals).
git fetch origin
git checkout dev
git reset --hard origin/main
git push --force-with-lease origin dev
```

## Why squash-merge causes "N ahead, 1 behind"

GitHub gives three merge styles. The trade-off:

| Style | Main history | Dev branch state after merge |
|---|---|---|
| **Squash** (this repo) | One clean commit per feature | Drifts ("N ahead, 1 behind") because squash creates a new SHA |
| Merge commit | Noisy ("WIP", "fix typo", merge commits) | Stays clean — original commits land verbatim |
| Rebase merge | Linear, all individual commits | Drifts because commits get rewritten with new SHAs |

We pick squash for clean `main` history and pay the price with the manual reset recipe above. Run it after every PR merges and `dev` stays aligned.

## What the PreToolUse hook (`.claude/`) enforces

`.claude/hooks/prevent-main-push.sh` blocks two operations *before* Claude can run them:

1. Any `git push` whose target ref is `main` — including `--force`, `HEAD:main`, `:main`, and `sha:main` variants.
2. Any `git commit` while the currently-checked-out branch is `main`.

If you hit the block: `git checkout dev` and do the work there. There's no legitimate reason to bypass the PR flow in this repo — branch protection on `main` would reject the push anyway; the hook just saves the network round-trip and gives a clearer error.
