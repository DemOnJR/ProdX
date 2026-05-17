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

[`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) builds both images and pushes to:
- [`pbdaemon/prodx-api`](https://hub.docker.com/r/pbdaemon/prodx-api)
- [`pbdaemon/prodx-web`](https://hub.docker.com/r/pbdaemon/prodx-web)

Required GitHub secrets:
- `DOCKERHUB_USERNAME` — your Docker Hub username
- `DOCKERHUB_TOKEN` — Docker Hub access token (Account Settings → Security → New Access Token, Read+Write+Delete)

PRs build but don't push. Pushes to `main` push `:latest` + `:sha-xxxxxxx`. Tags `v1.2.3` push semver tags too.

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
└── .github/workflows/docker-publish.yml
```
