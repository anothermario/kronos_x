"""Polymarket-style Streamlit dashboard for BTC/USD Futures.

Renders a full-page dashboard with:
  - Live KPI banner (price, 24h change, volume, OI, funding rate)
  - Candlestick / line price chart with selectable interval
  - Bull vs Bear "outcome probability" gauge (derived from taker-buy ratio)
  - Bid/Ask depth table
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    import streamlit as st
    import streamlit.components.v1 as components
except ModuleNotFoundError:
    st = None  # type: ignore[assignment]

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None  # type: ignore[assignment]

from .polymarket_data import (
    fetch_funding_rate,
    fetch_klines,
    fetch_open_interest,
    fetch_order_book_depth,
    fetch_ticker,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _fmt_price(v: float) -> str:
    return f"${v:,.2f}"


def _fmt_large(v: float) -> str:
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    return f"${v:,.0f}"


def _fmt_pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def _fmt_funding(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v * 100:.4f}%"


def _color(v: float) -> str:
    return "green" if v >= 0 else "red"


def _bull_bear_pct(candles: list[dict]) -> tuple[float, float]:
    """Derive bull/bear sentiment from taker-buy volume ratio over last N candles."""
    total_vol = sum(c["volume"] for c in candles if c["volume"] > 0)
    total_buy = sum(c["taker_buy_volume"] for c in candles)
    if total_vol == 0:
        return 50.0, 50.0
    bull = (total_buy / total_vol) * 100
    bear = 100 - bull
    return round(bull, 1), round(bear, 1)


# ── KPI banner ────────────────────────────────────────────────────────────────


def _render_kpi_banner(ticker: dict, funding: dict, oi: dict) -> None:
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)

    pct = ticker["price_change_pct"]
    col1.metric(
        "Last Price",
        _fmt_price(ticker["last_price"]),
        delta=f"{_fmt_pct(pct)} 24h",
        delta_color="normal",
    )
    col2.metric("24h High", _fmt_price(ticker["high_24h"]))
    col2.metric("24h Low", _fmt_price(ticker["low_24h"]))
    col3.metric("24h Volume (BTC)", f"{ticker['volume_24h']:,.0f}")
    col3.metric("24h Volume (USD)", _fmt_large(ticker["quote_volume_24h"]))
    col4.metric("Open Interest", _fmt_large(oi["open_interest_usd"]))
    col4.metric("OI (contracts)", f"{oi['open_interest_contracts']:,.0f}")
    col5.metric("Funding Rate", _fmt_funding(funding["funding_rate"]))
    col5.metric("Mark Price", _fmt_price(funding["mark_price"]))
    st.markdown("---")


# ── price chart ───────────────────────────────────────────────────────────────


def _render_price_chart(candles: list[dict], interval: str) -> None:
    if pd is None:
        st.warning("pandas not installed — chart unavailable.")
        return

    df = pd.DataFrame(candles)
    df["time"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    df = df.set_index("time")

    # Try plotly for candlestick, fall back to line chart
    try:
        import plotly.graph_objects as go

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df.index,
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                    name="BTCUSDT",
                    increasing_line_color="#26a69a",
                    decreasing_line_color="#ef5350",
                )
            ]
        )
        fig.update_layout(
            title=f"BTC/USD Perpetual — {interval} candles",
            xaxis_title="",
            yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False,
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font=dict(color="#fafafa"),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)
    except ModuleNotFoundError:
        # fallback: simple line chart
        st.line_chart(df[["close"]], height=320)


# ── bull/bear outcome panel ───────────────────────────────────────────────────


def _render_outcome_panel(bull: float, bear: float) -> None:
    st.subheader("📊 Market Sentiment (taker-buy ratio)")
    c1, c2 = st.columns(2)
    c1.metric("🟢 Bull (buy pressure)", f"{bull}%")
    c2.metric("🔴 Bear (sell pressure)", f"{bear}%")

    # Simple HTML progress bar
    bar_html = f"""
    <div style="background:#ef5350;border-radius:6px;height:28px;width:100%;position:relative;overflow:hidden;">
      <div style="background:#26a69a;width:{bull}%;height:100%;display:flex;align-items:center;padding-left:8px;">
        <span style="color:#fff;font-weight:600;font-size:14px;">{bull}% Bull</span>
      </div>
      <span style="position:absolute;right:8px;top:50%;transform:translateY(-50%);color:#fff;font-weight:600;font-size:14px;">{bear}% Bear</span>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)
    st.markdown("")


# ── order book depth ──────────────────────────────────────────────────────────


def _render_depth(depth: dict) -> None:
    st.subheader("📖 Order Book (top 10)")
    if pd is None:
        st.warning("pandas not installed — order book unavailable.")
        return

    col_bid, col_ask = st.columns(2)
    bids_df = pd.DataFrame(depth["bids"], columns=["Bid Price", "Qty"])
    asks_df = pd.DataFrame(depth["asks"], columns=["Ask Price", "Qty"])

    bids_df["Bid Price"] = bids_df["Bid Price"].map(_fmt_price)
    asks_df["Ask Price"] = asks_df["Ask Price"].map(_fmt_price)

    col_bid.markdown("**Bids 🟢**")
    col_bid.dataframe(bids_df, hide_index=True, use_container_width=True)
    col_ask.markdown("**Asks 🔴**")
    col_ask.dataframe(asks_df, hide_index=True, use_container_width=True)


# ── main render entry point ───────────────────────────────────────────────────


def render_polymarket_dashboard() -> None:
    """Render the full Polymarket-style BTC/USD Futures dashboard."""
    if st is None:
        raise RuntimeError("streamlit is not installed.")

    # ── header ────────────────────────────────────────────────────────────────
    st.markdown(
        "<h1 style='margin-bottom:0'>₿ BTC/USD Futures Dashboard</h1>"
        "<p style='color:#aaa;margin-top:2px'>Binance Perpetual · Live</p>",
        unsafe_allow_html=True,
    )

    # ── sidebar controls ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        interval = st.selectbox(
            "Candle Interval",
            options=["1m", "5m", "15m", "1h", "4h", "1d"],
            index=3,
        )
        limit = st.slider("Candles", min_value=24, max_value=200, value=48, step=24)
        auto_refresh = st.checkbox("Auto-refresh (30 s)", value=False)
        refresh_btn = st.button("🔄 Refresh Now", use_container_width=True)

    if auto_refresh:
        # Static, trusted script — no user input involved.
        # Reloads the page every 30 seconds to pull fresh data.
        components.html(
            "<script>setTimeout(()=>window.location.reload(),30000);</script>",
            height=0,
        )

    # ── data fetch ────────────────────────────────────────────────────────────
    with st.spinner("Fetching live data …"):
        try:
            ticker = fetch_ticker()
            funding = fetch_funding_rate()
            oi = fetch_open_interest()
            candles = fetch_klines(interval=interval, limit=limit)
            depth = fetch_order_book_depth()
        except Exception as exc:
            st.error(f"Failed to fetch data: {exc}")
            st.stop()

    # ── timestamp ─────────────────────────────────────────────────────────────
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.caption(f"Last updated: {now_utc}")

    # ── KPI banner ────────────────────────────────────────────────────────────
    _render_kpi_banner(ticker, funding, oi)

    # ── main layout: chart + outcome ──────────────────────────────────────────
    chart_col, side_col = st.columns([3, 1])

    with chart_col:
        _render_price_chart(candles, interval)

    with side_col:
        bull, bear = _bull_bear_pct(candles)
        _render_outcome_panel(bull, bear)

        st.markdown("#### 📈 24h Stats")
        st.write(f"Trades: **{ticker['trades_24h']:,}**")
        pct = ticker["price_change_pct"]
        color = "green" if pct >= 0 else "red"
        st.markdown(
            f"Price Change: <span style='color:{color}'>"
            f"<b>{_fmt_pct(pct)}</b></span>",
            unsafe_allow_html=True,
        )

    # ── order book ────────────────────────────────────────────────────────────
    with st.expander("Order Book", expanded=False):
        _render_depth(depth)
