# Changelog

All notable changes to ProdX, kept in reverse chronological order. Versions
mirror the `version` field returned by `GET /api/metrics`.

## [0.2.0] — 2026-05-17

### Added
- `version` field in `MetricsResponse` so deploys can be verified by
  `curl https://prodxapi.pbcv.dev/api/metrics | jq .version`.
- `dev` branch + GitHub Flow promotion model. CI runs on push to `dev`
  but no `:latest` Docker Hub tag is published from it (Argo CD only
  syncs from `:latest`, which is gated to `main`).
- CHANGELOG.md (this file).

### Changed
- `vite` 5 → 8, `@vitejs/plugin-react` 4 → 6 (peer-compatible bump
  to absorb published vite CVEs).
- `fastapi` 0.115.5 → 0.136.1 + explicit `starlette>=0.49.1` pin
  (fixes CVE-2025-54121, CVE-2025-62727).

### Security
- pip-audit + npm audit as CI gates (block image build on known CVEs
  in `requirements.txt` / `package.json`).
- Trivy image scan on every build (block Docker Hub push on CRITICAL
  CVEs with known fixes).
- Dependabot configured with 7-day cooldown for routine version
  updates + security-update bypass for CVEs.

## [0.1.0] — 2026-05-16

- Initial scaffold: FastAPI backend + React (Vite + React Flow)
  frontend + PostgreSQL + Redis, wired via Docker Compose.
- GitHub Actions workflow building both images and publishing to
  Docker Hub.
- Terraform (ProdXTF) provisioning GKE + Argo CD + cloudflared.
- Argo CD reconciling a Helm chart (ProdXCD) into the cluster.
- Cloudflare Tunnel exposing `prodx.pbcv.dev`, `prodxapi.pbcv.dev`,
  and `argocd.pbcv.dev`.
