"""Fetch and validate model weights during the hosted build."""
import os
from pathlib import Path
from app.bootstrap import ensure_models

if __name__ == '__main__':
    ensure_models(Path(os.environ.get('SUPPORT_MODELS_PATH', 'models')))
