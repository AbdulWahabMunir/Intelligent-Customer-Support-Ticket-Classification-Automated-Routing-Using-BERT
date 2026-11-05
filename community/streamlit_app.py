"""Streamlit Community Cloud entrypoint; inference stays in FastAPI."""
import os
from pathlib import Path
import runpy

import streamlit as st

required = ("SUPPORT_API_URL", "SUPPORT_API_KEY", "SUPPORT_DASHBOARD_PASSWORD")
try:
    settings = dict(st.secrets)
except FileNotFoundError:
    settings = {}
missing = [key for key in required if key not in settings]
if missing:
    st.error("Deployment secrets are incomplete. Configure the API URL, API key and workspace password.")
    st.stop()
if not settings["SUPPORT_API_URL"].startswith("https://"):
    st.error("The hosted API must use HTTPS.")
    st.stop()
if len(settings["SUPPORT_API_KEY"]) < 32 or len(settings["SUPPORT_DASHBOARD_PASSWORD"]) < 12:
    st.error("Configure an API key of at least 32 characters and workspace password of at least 12 characters.")
    st.stop()
for key in required:
    os.environ[key] = str(settings[key])
runpy.run_path(str(Path(__file__).resolve().parents[1] / "app/dashboard.py"), run_name="__main__")
