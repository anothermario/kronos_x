import streamlit as st

from src.kronos_x.main import render_streamlit_app
from src.kronos_x.polymarket_dashboard import render_polymarket_dashboard

st.set_page_config(
    page_title="kronos_x",
    page_icon="₿",
    layout="wide",
)

st.sidebar.title("kronos_x")
page = st.sidebar.radio(
    "Page",
    options=["₿ BTC/USD Futures Dashboard", "⚙️ Trading Engine Demo"],
)

if page == "₿ BTC/USD Futures Dashboard":
    render_polymarket_dashboard()
else:
    render_streamlit_app()
