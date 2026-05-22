# ProdX

A small full-stack app (FastAPI + React Flow) that ships through a real GitOps pipeline:

```
  push code (this repo)
        │
        ▼
  GitHub Actions builds Docker images
        │
        ▼
  pushes to Google Artifact Registry
        │
        ▼
  Argo CD (running in the cluster) sees the new manifest in ProdXCD
        │
        ▼
  GKE rolls out new pods
        │
        ▼
  Cloudflare Tunnel serves the app at https://prodx.pbcv.dev
```

This is the **app repo**. There are two more, each with its own README:

| Repo | What it holds | When you touch it |
|---|---|---|
| **ProdX** (here) | App source code, Dockerfiles, GitHub Actions CI, local docker-compose | Day-to-day development |
| [**ProdXTF**](https://github.com/DemOnJR/ProdXTF) | Terraform for GCP project + GKE + Argo CD + Cloudflare tunnel | Once, to build the infrastructure |
| [**ProdXCD**](https://github.com/DemOnJR/ProdXCD) | Helm chart (what runs in the cluster) | When you tune replicas, resources, or env vars |

> **First time here?** Start with [the prerequisites and account setup](#first-time-setup-accounts-you-will-need), then go to [ProdXTF's README](https://github.com/DemOnJR/ProdXTF) to build the cluster. After that come back here.

---

## Live URLs (when the cluster is up)

- App: <https://prodx.pbcv.dev>
- API: <https://prodxapi.pbcv.dev/api/metrics>
- Argo CD: <https://argocd.pbcv.dev>

---

## Run it locally (no cloud account needed)

You only need Docker Desktop installed.

```bash
cp .env.example .env       # optional — the defaults work
docker compose up --build
```

Then open:

- Frontend → <http://localhost:8080>
- API direct → <http://localhost:8000/api/metrics>
- API through the web container's nginx → <http://localhost:8080/api/metrics>

Postgres data persists in the `pg_data` Docker volume. `docker compose down` keeps it; `docker compose down -v` wipes it.

---

## First-time setup: accounts you will need

To deploy this to the cloud you need four free accounts. **Set them up in this order** — each step gives you something the next step needs.

### 1. GitHub account (5 minutes, free)

Used to host the code and run CI.

1. Create an account at <https://github.com/signup> if you don't have one.
2. Fork these three repos into your GitHub account:
   - <https://github.com/DemOnJR/ProdX>
   - <https://github.com/DemOnJR/ProdXTF>
   - <https://github.com/DemOnJR/ProdXCD>
3. Clone all three to your machine.

### 2. Google Cloud account (15 minutes, free trial)

Used for the GKE cluster, the Artifact Registry, and IAM.

1. Sign up at <https://cloud.google.com/free>. You get **$300 in credit valid for 90 days**.
2. Google asks for a credit/debit card to verify you're a real person. **They typically place a small temporary hold (around $1) which is refunded** — this hold can show up as a charge on some cards for a few days. If your bank requires it, treat it like a verification of up to ~$10 that you'll get back.
3. **You will not be charged for normal use during the trial** — the $300 credit covers everything. Just remember to `terraform destroy` the cluster when you're not working on it (see ProdXTF README).
4. Install the Google Cloud SDK on your machine: <https://cloud.google.com/sdk/docs/install>
5. Log in from your terminal:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

### 3. Cloudflare account + a domain (10 minutes, mostly free)

Used to publish the app on a real HTTPS URL without paying for a load balancer or wrestling with certificates.

1. Sign up at <https://dash.cloudflare.com/sign-up>. Free plan is enough.
2. **You need to own a domain.** If you don't:
   - Buy one from any registrar (Namecheap, Porkbun, Cloudflare Registrar are common cheap options — around $10/year for `.dev`, `.xyz`, etc).
3. In Cloudflare, click **Add a site**, enter your domain, pick the **Free** plan. Cloudflare will give you two nameservers — go to your registrar and replace the existing nameservers with these. DNS propagation usually takes 5–60 minutes.
4. Create the tunnel itself in the Cloudflare Zero Trust dashboard. The full step-by-step is in [ProdXTF's README](https://github.com/DemOnJR/ProdXTF#3-cloudflare-tunnel) — you'll do it as part of setting up the infrastructure.

### 4. HCP Terraform account (5 minutes, free)

This is **only used to store Terraform's state file** safely in the cloud, so multiple people (or multiple machines) don't trample on each other's state. **Terraform itself runs on your laptop**, against your local `gcloud` credentials.

1. Sign up at <https://app.terraform.io/public/signup/account>. Free tier is enough.
2. You will create two workspaces (`prodx-bootstrap`, `prodx-dev`) when you reach the ProdXTF steps. Both will be set to **Execution Mode: Local** — see the explainer below.

### What "Local execution mode" actually means

HCP Terraform has two execution modes:

- **Remote** (the default) — HCP's servers run `terraform apply` for you, in their cloud.
- **Local** — `terraform apply` runs on **your laptop**, using **your** `gcloud` login and **your** kubeconfig. Only the **state file** (`terraform.tfstate`) is uploaded to HCP after each run.

We use **Local** mode because:
- HCP's remote runners don't have your `gcloud` Application Default Credentials.
- It keeps the setup simple — no service-account keys to upload to HCP.
- You still get the safety of remote state (locked, versioned, recoverable) without giving HCP access to your cloud.

So: **the only thing in the cloud is the Terraform state.** All real work happens locally.

---

## Architecture overview

What runs where, once everything is deployed:

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│                          Cloudflare edge (free)                        │
│                                                                        │
│   prodx.pbcv.dev   prodxapi.pbcv.dev   argocd.pbcv.dev                 │
│       │                  │                  │                          │
│       │  TLS terminates here, then HTTP into the cluster               │
│       │                                                                │
└───────┼────────────────────┼─────────────────┼────────────────────────┘
        │                    │                 │
        ▼                    ▼                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       GKE cluster (Google Cloud)                       │
│                                                                        │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│   │  cloudflared │    │  prodx-web   │    │   argocd     │             │
│   │  (tunnel)    │───▶│  (nginx)     │    │   server     │             │
│   └──────────────┘    │              │    └──────────────┘             │
│                       │   /api/* ─┐  │            │                    │
│                       └───────────┼──┘            │                    │
│                                   ▼               │ syncs every ~3 min │
│                          ┌──────────────┐         │                    │
│                          │  prodx-api   │         ▼                    │
│                          │  (FastAPI)   │   reads ProdXCD on GitHub    │
│                          └──────────────┘                              │
│                            │       │                                   │
│                            ▼       ▼                                   │
│                       ┌──────┐ ┌───────┐                               │
│                       │  pg  │ │ redis │                               │
│                       └──────┘ └───────┘                               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                                ▲
                                │ pulls images on rollout
                                │
                       ┌────────┴────────────┐
                       │ Artifact Registry   │
                       │ (private, in GCP)   │
                       └─────────────────────┘
                                ▲
                                │ pushes images on every push to main
                                │
                       ┌────────┴────────────┐
                       │  GitHub Actions     │
                       │  (this repo's CI)   │
                       └─────────────────────┘
```

**Components:**

- **GitHub Actions** — builds Docker images for backend & frontend, scans them with Trivy, pushes them to GCP.
- **Artifact Registry** — private Docker registry inside your GCP project. CI pushes here, GKE pulls from here.
- **Workload Identity Federation (WIF)** — lets GitHub Actions get a short-lived GCP token without storing a service account JSON key as a GitHub secret. The trust binding is set up by Terraform.
- **GKE (Google Kubernetes Engine)** — runs the app pods.
- **Argo CD** — runs in the cluster, watches the ProdXCD repo, and applies changes automatically.
- **cloudflared** — runs in the cluster, opens an outbound connection to Cloudflare's edge so users can reach the app without us opening any public ports.

---

## How to ship a code change

1. Make changes here (backend or frontend code).
2. Open a PR. CI runs lint, tests, builds the images, scans them with Trivy.
3. Merge to `main`. CI rebuilds the images, pushes them as `:latest` to Artifact Registry, then does `kubectl rollout restart` on the matching deployment.
4. New pods come up pulling the fresh `:latest`. Argo CD doesn't need to do anything because the manifest didn't change — only the image content under the same tag.

If you want to change cluster config (replicas, env vars, resource limits) — that's in [ProdXCD](https://github.com/DemOnJR/ProdXCD), not here.

---

## CI workflows (this repo)

Three files in [`.github/workflows/`](.github/workflows/):

| File | What it does |
|---|---|
| `ci-backend.yml` | PR: lint, tests, pip-audit, Docker build + Trivy CRITICAL scan. Main: also push to Artifact Registry + rollout restart. |
| `ci-frontend.yml` | Same shape for the React + Vite frontend. |
| `pr-review.yml` | Optional — uses the Cursor agent to post an AI code review on PRs. Delete it if you don't want it. |

**Required GitHub secret:**

- `CURSOR` — only for `pr-review.yml`. Get it from <https://cursor.com/settings>. Skip if you delete that workflow.

**Branch protection (recommended):** Settings → Branches → require the status check named `🚀 Pipeline` on `main`. One entry covers both backend & frontend CI because they share the job name.

> **No long-lived secrets for image pushes.** CI authenticates to GCP via Workload Identity Federation — GitHub mints a short-lived OIDC token, GCP exchanges it for a 1-hour access token. The trust binding is in `ProdXTF/modules/registry`. The values that wire CI to your project (`GCP_WIF_PROVIDER`, `GCP_WIF_SA`, `IMAGE`, the cluster) are **not** hardcoded — `ProdXTF/envs/dev` publishes them to this repo as **GitHub Actions variables** on every `terraform apply`, and the workflows read them as `${{ vars.* }}`. Nothing to edit by hand, even after a destroy/recreate. While the environment is down the variables are absent and the publish/deploy steps skip cleanly, so CI on `main` still passes (build + Trivy scan only).

---

## API endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/api/metrics` | Postgres / Redis status, uptime, pool stats, graph count |
| GET | `/api/graphs/{id}` | Redis-cached read; seeds `prodx` graph on first boot |
| PUT | `/api/graphs/{id}` | Upsert + cache invalidation |

The default `prodx` graph (the one you see at <https://prodx.pbcv.dev>) is defined in [`backend/app/seed.py`](backend/app/seed.py). To ship a graph change to production: push to `main`, wait for CI, then flip `api.forceSeed` to `true` in ProdXCD's `values.yaml` for a one-shot reseed (revert it to `false` afterward — see ProdXCD's README).

---

## Layout

```
ProdX/
├── backend/                     FastAPI
│   ├── app/
│   │   ├── main.py              routes + lifespan + seed
│   │   ├── seed.py              the default "prodx" React Flow graph
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── cache.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                    React 18 + Vite + @xyflow/react
│   ├── src/                     App.tsx · api.ts · main.tsx · index.css
│   ├── Dockerfile               builds, copies dist into nginx:alpine
│   ├── nginx.conf               SPA fallback + /api/ proxy to prodx-api
│   └── package.json
├── docker-compose.yml           postgres + redis + prodx-api + prodx-web
├── .env.example
├── docs/index.html              complete setup guide (self-contained, no CDN)
└── .github/workflows/
    ├── ci-backend.yml
    ├── ci-frontend.yml
    └── pr-review.yml
```

> The web image deliberately does **not** bake `VITE_API_BASE_URL` at build time. Its nginx config proxies `/api/*` to `http://prodx-api:8000`, which resolves via Docker Compose service-name DNS locally and via Kubernetes Service DNS in the cluster — same image works in both environments.

---

## Want the long version?

A full, beginner-friendly setup guide is at [`docs/index.html`](docs/index.html) — open it in a browser. Fourteen sections covering account setup, installing the tools, the Terraform build, verification, Argo CD, pausing/destroying, and troubleshooting.
