"""ASGI entrypoint for uvicorn / gunicorn.

Run with: gunicorn app.asgi:app -k uvicorn.workers.UvicornWorker
or:      uvicorn app.asgi:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import uvicorn

from app.main import app

__all__ = ["app"]


def run() -> None:
    """Convenience entrypoint for `python -m app.asgi`."""
    uvicorn.run("app.asgi:app", host="0.0.0.0", port=8000, reload=False)  # noqa: S104


if __name__ == "__main__":
    run()
