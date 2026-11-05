"""Zero-card deployment: Streamlit UI, internal FastAPI/DistilBERT, Neon storage."""
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st
from app.community_backend import start_backend
from app.dashboard import require_access

try:
    settings = dict(st.secrets)
except FileNotFoundError:
    settings = {}
required = ('DATABASE_URL', 'SUPPORT_API_KEY', 'SUPPORT_DASHBOARD_PASSWORD', 'MODEL_BUNDLE_URL', 'MODEL_BUNDLE_SHA256')
if any(not settings.get(key) for key in required):
    st.error('Deployment setup is incomplete. Configure the application secrets.')
    st.stop()
if len(str(settings['SUPPORT_API_KEY'])) < 32 or len(str(settings['SUPPORT_DASHBOARD_PASSWORD'])) < 12:
    st.error('Deployment access keys do not meet the required length.')
    st.stop()
for key in required:
    os.environ[key] = str(settings[key])
os.environ.setdefault('SUPPORT_MODELS_PATH', str(ROOT / '.cache/community-models'))
os.environ['SUPPORT_API_URL'] = f"http://127.0.0.1:{os.environ.get('SUPPORT_INTERNAL_API_PORT', '8787')}"

# Authenticate before loading the model or accessing tickets.
if not require_access():
    st.stop()


@st.cache_resource(validate=lambda process: process.poll() is None, show_spinner=False)
def backend():
    return start_backend()


try:
    with st.spinner('Starting the support API and DistilBERT. The first launch downloads model weights.'):
        backend()
except RuntimeError as error:
    st.error(str(error))
    st.stop()
runpy.run_path(str(ROOT / 'app/dashboard.py'), run_name='__main__')
