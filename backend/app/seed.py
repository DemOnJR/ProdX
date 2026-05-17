"""The initial React Flow graph rendered at prodx.pbcv.dev.

Tells the project's whole story on one canvas: source → CI → registry →
GitOps → cluster → Cloudflare → user. Edit this file, push, let CI build,
then set FORCE_SEED=true on the api pod for the new graph to replace
the existing one (see main.seed()).
"""


def _style(bg: str, border: str, *, fg: str = "#ffffff") -> dict:
    return {
        "background": bg,
        "color": fg,
        "border": f"2px solid {border}",
        "borderRadius": 8,
        "fontWeight": 600,
        "padding": 8,
        "width": 170,
        "textAlign": "center",
    }


# Source / CI lane (top row)
_SRC      = _style("#0f766e", "#115e59")   # teal — code repos
_CI       = _style("#f59e0b", "#b45309")   # amber — GitHub Actions
_REGISTRY = _style("#0ea5e9", "#0369a1")   # sky    — Docker Hub
# Provisioning
_IAC      = _style("#7c3aed", "#5b21b6")   # violet — Terraform
# GitOps
_ARGO     = _style("#ea580c", "#c2410c")   # orange — Argo CD
# Workloads
_WEB      = _style("#7c3aed", "#5b21b6")   # violet — nginx/SPA
_API      = _style("#059669", "#047857")   # green  — FastAPI
_DB       = _style("#1d4ed8", "#1e3a8a")   # blue   — Postgres
_CACHE    = _style("#dc2626", "#991b1b")   # red    — Redis
# Edge
_TUNNEL   = _style("#f97316", "#c2410c")   # tangerine — cloudflared
_USER     = _style("#0ea5e9", "#0369a1")   # sky — end user


PRODX_GRAPH: dict = {
    "nodes": [
        # ── Source & CI lane (y=0) ────────────────────────────────────────
        {"id": "gh-prodx",     "type": "input",  "position": {"x":   0, "y":   0},
         "data": {"label": "GitHub\nDemOnJR/ProdX"},   "style": _SRC},
        {"id": "ci",                              "position": {"x": 220, "y":   0},
         "data": {"label": "GitHub Actions\n(build & publish)"}, "style": _CI},
        {"id": "dockerhub",                       "position": {"x": 460, "y":   0},
         "data": {"label": "Docker Hub\npbdaemon/prodx-{api,web}"}, "style": _REGISTRY},
        {"id": "gh-prodxcd",   "type": "input",  "position": {"x": 700, "y":   0},
         "data": {"label": "GitHub\nDemOnJR/ProdXCD"},  "style": _SRC},

        # ── Provisioning + GitOps lane (y=160) ───────────────────────────
        {"id": "hcp-tf",       "type": "input",  "position": {"x":   0, "y": 160},
         "data": {"label": "HCP Terraform\nGKE + Argo + cloudflared"}, "style": _IAC},
        {"id": "argocd",                          "position": {"x": 700, "y": 160},
         "data": {"label": "Argo CD\nargocd.pbcv.dev"}, "style": _ARGO},

        # ── Workloads lane (y=320) ──────────────────────────────────────
        {"id": "cloudflared",                     "position": {"x": 220, "y": 320},
         "data": {"label": "cloudflared\n(2 pods)"}, "style": _TUNNEL},
        {"id": "prodx-web",                       "position": {"x": 460, "y": 320},
         "data": {"label": "prodx-web\nnginx + React SPA"}, "style": _WEB},
        {"id": "prodx-api",                       "position": {"x": 700, "y": 320},
         "data": {"label": "prodx-api\nFastAPI"}, "style": _API},

        # ── Data lane (y=480, right side) ─────────────────────────────
        {"id": "postgres",     "type": "output", "position": {"x": 700, "y": 480},
         "data": {"label": "Postgres\n(StatefulSet + PVC)"}, "style": _DB},
        {"id": "redis",        "type": "output", "position": {"x": 940, "y": 480},
         "data": {"label": "Redis\n(StatefulSet + PVC)"}, "style": _CACHE},

        # ── End user (y=480, left side) ────────────────────────────────
        {"id": "browser",      "type": "input",  "position": {"x":   0, "y": 480},
         "data": {"label": "Browser\nprodx.pbcv.dev"}, "style": _USER},
    ],

    "edges": [
        # CI chain
        {"id": "e-src-ci",      "source": "gh-prodx",   "target": "ci",
         "label": "git push", "animated": True},
        {"id": "e-ci-hub",      "source": "ci",         "target": "dockerhub",
         "label": "build + push :latest", "animated": True},

        # GitOps loop
        {"id": "e-prodxcd-argo","source": "gh-prodxcd", "target": "argocd",
         "label": "Argo watches", "animated": True},

        # Provisioning
        {"id": "e-tf-argo",     "source": "hcp-tf",     "target": "argocd",
         "label": "TF installs", "style": {"strokeDasharray": "4 4"}},
        {"id": "e-tf-cf",       "source": "hcp-tf",     "target": "cloudflared",
         "label": "TF deploys", "style": {"strokeDasharray": "4 4"}},

        # Argo CD reconciles workloads
        {"id": "e-argo-web",    "source": "argocd",     "target": "prodx-web",
         "label": "sync"},
        {"id": "e-argo-api",    "source": "argocd",     "target": "prodx-api",
         "label": "sync"},

        # In-cluster traffic
        {"id": "e-web-api",     "source": "prodx-web",  "target": "prodx-api",
         "label": "/api → :8000"},
        {"id": "e-api-pg",      "source": "prodx-api",  "target": "postgres",
         "label": "SQLAlchemy"},
        {"id": "e-api-redis",   "source": "prodx-api",  "target": "redis",
         "label": "cache GET"},

        # Public entry
        {"id": "e-browser-cf",  "source": "browser",    "target": "cloudflared",
         "label": "HTTPS via CF edge", "animated": True},
        {"id": "e-cf-web",      "source": "cloudflared","target": "prodx-web",
         "label": "prodx.pbcv.dev"},
        {"id": "e-cf-api",      "source": "cloudflared","target": "prodx-api",
         "label": "prodxapi.pbcv.dev"},
        {"id": "e-cf-argo",     "source": "cloudflared","target": "argocd",
         "label": "argocd.pbcv.dev"},

        # Image pull (subtle, dashed)
        {"id": "e-hub-api",     "source": "dockerhub",  "target": "prodx-api",
         "label": "image pull", "style": {"strokeDasharray": "4 4"}},
        {"id": "e-hub-web",     "source": "dockerhub",  "target": "prodx-web",
         "label": "image pull", "style": {"strokeDasharray": "4 4"}},
    ],
}
