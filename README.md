# ProdX

ITSchool DevOps capstone. This repo holds the app: FastAPI backend + React (Vite + React Flow) frontend + PostgreSQL + Redis, wired together with Docker Compose. CI builds and pushes images to Docker Hub.

Companion repos:
- **ProdXTF** — Terraform for cluster + Argo CD bootstrap (added later)
- **ProdXCD** — Argo CD `Application` manifests for ProdX (added later)

## Local run

```bash
cp .env.example .env       # optional; defaults work for local
docker compose up --build
```

- Frontend: http://localhost:8080
- API: http://localhost:8000 (`/health`, `/api/metrics`, `/api/graphs/prodx`)

Postgres data persists in the `pg_data` named volume — `docker compose down` keeps it, `docker compose down -v` wipes it.

## API endpoints

| Method | Path                       | Notes                                     |
|--------|----------------------------|-------------------------------------------|
| GET    | `/health`                  | liveness                                  |
| GET    | `/api/metrics`             | postgres/redis status, uptime, graph count |
| GET    | `/api/graphs/{id}`         | Redis-cached read; seeds `prodx` on boot   |
| PUT    | `/api/graphs/{id}`         | upsert + cache invalidation                |

## CI

`.github/workflows/docker-publish.yml` builds both images and pushes to:
- `pbdaemon/prodx-api`
- `pbdaemon/prodx-web`

Required GitHub secrets in the repo:
- `DOCKERHUB_USERNAME` = `pbdaemon`
- `DOCKERHUB_TOKEN` = a Docker Hub access token (Account Settings → Security → New Access Token)

PRs build but don't push. Pushes to `main` push `:latest` + `:sha-xxxxxxx`. Tags `v1.2.3` push semver tags.

## Layout

```
ProdX/
├── backend/                 FastAPI
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                React + Vite + @xyflow/react
│   ├── src/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── .env.example
└── .github/workflows/docker-publish.yml
```
