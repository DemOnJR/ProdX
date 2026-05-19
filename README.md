# ProdX

ITSchool DevOps capstone. End-to-end pipeline: code in this repo → GitHub Actions builds container images → Docker Hub → Argo CD reconciles a Helm chart from a separate manifests repo → GKE cluster serves the app behind a Cloudflare Tunnel.

> **📖 Full setup tutorial** at [`docs/index.html`](docs/index.html) — fifteen sections from zero (no GCP account) to a fully running cluster with three public URLs. Open the file in a browser or publish via GitHub Pages.

## Live (when the cluster is up)

- **App:** [prodx.pbcv.dev](https://prodx.pbcv.dev)
- **API:** [prodxapi.pbcv.dev/api/metrics](https://prodxapi.pbcv.dev/api/metrics)
- **Argo CD:** [argocd.pbcv.dev](https://argocd.pbcv.dev)

## The three-repo split

| Repo | Holds | Consumed by |
|------|-------|-------------|
| **ProdX** (here) | App source + Dockerfiles + CI workflow + local compose | Anyone running locally; GitHub Actions building images |
| [**ProdXTF**](https://github.com/DemOnJR/ProdXTF) | Terraform: GCP project bootstrap + VPC + GKE + Argo CD (Helm) + cloudflared deployment + root Argo Application | `terraform apply` from your machine; state in HCP Terraform |
| [**ProdXCD**](https://github.com/DemOnJR/ProdXCD) | Helm chart Argo CD reconciles (Postgres + Redis StatefulSets, prodx-api + prodx-web Deployments, Services) | Argo CD, automatically |

## Local run

```bash
cp .env.example .env       # optional; defaults work for local
docker compose up --build
```

- Frontend: <http://localhost:8080>
- API direct: <http://localhost:8000/health> · <http://localhost:8000/api/metrics>
- API via the web container's nginx proxy: <http://localhost:8080/api/metrics>

Postgres data persists in the `pg_data` named volume — `docker compose down` keeps it, `docker compose down -v` wipes it.

## API endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | liveness |
| GET | `/api/metrics` | postgres / redis status, uptime, pool stats, graph count |
| GET | `/api/graphs/{id}` | Redis-cached read; seeds `prodx` on boot |
| PUT | `/api/graphs/{id}` | upsert + cache invalidation |

The `prodx` graph rendered at the frontend is defined in [`backend/app/seed.py`](backend/app/seed.py). To ship a graph change after editing that file: push to `main`, wait for CI to rebuild, then flip `api.forceSeed` to `true` in ProdXCD's `values.yaml` for a one-shot reseed (revert it back to `false` afterward — see ProdXCD's README).

## CI

Three workflows in [`.github/workflows/`](.github/workflows/):

- [`ci-backend.yml`](.github/workflows/ci-backend.yml) — lint / test / pip-audit (PRs), Docker build + Trivy CRITICAL gate (PR + main), publish to Artifact Registry + GKE rollout (main only)
- [`ci-frontend.yml`](.github/workflows/ci-frontend.yml) — same shape for the React + Vite frontend (tsc / vite build / npm audit on PRs)
- [`pr-review.yml`](.github/workflows/pr-review.yml) — Cursor agent posts a markdown code review as a PR comment (best-effort, not a required check; same-repo PRs only)

**Registry auth — no long-lived secret.** Both `ci-*` workflows mint a short-lived GCP token via Workload Identity Federation and push to Google Artifact Registry:
- `europe-west3-docker.pkg.dev/prodx-dev2/prodx/prodx-api`
- `europe-west3-docker.pkg.dev/prodx-dev2/prodx/prodx-web`

Then `kubectl rollout restart` the matching deployment so GKE pulls the new `:latest`. The WIF trust binding is configured in [ProdXTF/modules/registry](https://github.com/DemOnJR/ProdXTF/tree/main/modules/registry) — see [`docs/index.html`](docs/index.html) § 06 for the full walkthrough.

**Required GitHub secret:** `CURSOR` — Cursor API key, only used by `pr-review.yml`. Optional; remove the workflow if you don't want AI PR reviews.

**Branch protection on `main`** (configure via Settings → Branches): require status check `🚀 Pipeline` — one entry covers both `ci-*` workflows since they share the job name.

PRs build but don't push. Pushes to `main` push `:latest` + branch / sha / semver tags, then trigger a rolling restart.

The web image deliberately does *not* bake `VITE_API_BASE_URL` at build time. Its nginx config proxies `/api/*` to `http://prodx-api:8000`, which resolves via Docker Compose service-name DNS locally and via Kubernetes Service DNS in the cluster — so the same image works in both environments and behind any reverse proxy (e.g. Cloudflare Tunnel) without rebuilds.

## Layout

```
ProdX/
├── backend/                    FastAPI
│   ├── app/
│   │   ├── main.py             routes + lifespan + seed
│   │   ├── seed.py             the prodx React Flow graph
│   │   ├── config.py · db.py · models.py · schemas.py · cache.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   React 18 + Vite + @xyflow/react
│   ├── src/                    App.tsx · api.ts · main.tsx · index.css
│   ├── Dockerfile              builds, copies dist into nginx:alpine
│   ├── nginx.conf              SPA fallback + /api/ proxy to prodx-api
│   └── package.json
├── docker-compose.yml          postgres + redis + prodx-api + prodx-web
├── .env.example
├── docs/index.html             full setup tutorial (self-contained, no CDN)
└── .github/workflows/        ci-backend.yml · ci-frontend.yml · pr-review.yml
```
