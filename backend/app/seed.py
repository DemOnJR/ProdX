"""Initial React Flow graph showing the ProdX local stack."""


def _style(bg: str, border: str) -> dict:
    return {
        "background": bg,
        "color": "#ffffff",
        "border": f"2px solid {border}",
        "borderRadius": 8,
        "fontWeight": 600,
        "padding": 8,
    }


_BROWSER = _style("#0ea5e9", "#0369a1")
_WEB = _style("#7c3aed", "#5b21b6")
_API = _style("#059669", "#047857")
_DB = _style("#2563eb", "#1d4ed8")
_CACHE = _style("#dc2626", "#991b1b")


PRODX_GRAPH: dict = {
    "nodes": [
        {
            "id": "browser",
            "type": "input",
            "position": {"x": 0, "y": 120},
            "data": {"label": "Browser"},
            "style": _BROWSER,
        },
        {
            "id": "web",
            "position": {"x": 220, "y": 120},
            "data": {"label": "Nginx (React SPA)"},
            "style": _WEB,
        },
        {
            "id": "api",
            "position": {"x": 460, "y": 120},
            "data": {"label": "FastAPI"},
            "style": _API,
        },
        {
            "id": "postgres",
            "type": "output",
            "position": {"x": 720, "y": 40},
            "data": {"label": "PostgreSQL"},
            "style": _DB,
        },
        {
            "id": "redis",
            "type": "output",
            "position": {"x": 720, "y": 220},
            "data": {"label": "Redis (cache)"},
            "style": _CACHE,
        },
    ],
    "edges": [
        {"id": "browser-web", "source": "browser", "target": "web", "label": "HTTP :8080", "animated": True},
        {"id": "web-api", "source": "web", "target": "api", "label": "fetch /api", "animated": True},
        {"id": "api-pg", "source": "api", "target": "postgres", "label": "SQLAlchemy"},
        {"id": "api-redis", "source": "api", "target": "redis", "label": "cache GET"},
    ],
}
