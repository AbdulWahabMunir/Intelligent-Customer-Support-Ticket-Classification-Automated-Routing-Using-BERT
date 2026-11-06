"""Public API entrypoint for a free service with external PostgreSQL."""
import os
from pathlib import Path

from app.bootstrap import ensure_models


def main():
    if len(os.environ.get("SUPPORT_API_KEY", "")) < 32:
        raise ValueError("Public API requires SUPPORT_API_KEY of at least 32 characters")
    if not os.environ.get("DATABASE_URL", "").startswith(("postgresql://", "postgres://")):
        raise ValueError("Public API requires an external PostgreSQL DATABASE_URL")
    print("[support-startup] Preparing verified model bundle", flush=True)
    ensure_models(Path(os.environ.get("SUPPORT_MODELS_PATH", "models")))
    print("[support-startup] Bundle ready; importing API server", flush=True)
    import uvicorn
    uvicorn.run("app.api:app", host=os.environ.get("SUPPORT_API_HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "10000")), workers=1)


if __name__ == "__main__":
    main()
