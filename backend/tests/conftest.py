"""Pytest config: set env vars before app modules are imported.

`app.config.Settings` requires DATABASE_URL and REDIS_URL with no defaults;
without these, even `from app.main import app` raises pydantic validation
errors. The values themselves aren't used unless the lifespan runs (it
doesn't in unit tests).
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
