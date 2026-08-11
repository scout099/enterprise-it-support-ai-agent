"""Two-page Streamlit entrypoint for the local Phase 11 demo."""

import os

import streamlit as st

from apps.ui.chat_page import render_chat_page
from apps.ui.client import ITSupportAPIClient
from apps.ui.dashboard_page import render_dashboard_page

st.set_page_config(page_title="Enterprise IT Support", page_icon="🛠️", layout="wide")

api_url = os.getenv("IT_SUPPORT_API_BASE_URL", "http://127.0.0.1:8000")
client = ITSupportAPIClient(api_url)
page = st.sidebar.radio("Page", ["IT Support Chat", "Analytics Dashboard"])

if page == "IT Support Chat":
    render_chat_page(client)
else:
    render_dashboard_page(client)
