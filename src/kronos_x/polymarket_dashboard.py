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

SOURCE_LIVE = "live"

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


def _interval_ms(interval: str) -> int:
    mapping = {
        "1m": 60_000,
        "5m": 300_000,
        "15m": 900_000,
        "1h": 3_600_000,
        "4h": 14_400_000,
        "1d": 86_400_000,
    }
    return mapping.get(interval, 3_600_000)


def _build_lite_fallback_data(interval: str, limit: int) -> dict[str, Any]:
    """Create minimal local data so dashboard still renders when live fetch fails."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    candle_ms = _interval_ms(interval)
    base = 65_000.0
    candles: list[dict[str, Any]] = []

    for i in range(limit):
        drift = (i - (limit / 2)) * 6.0
        open_price = base + drift
        close_price = open_price + (8.0 if i % 2 == 0 else -5.0)
        high_price = max(open_price, close_price) + 6.0
        low_price = min(open_price, close_price) - 6.0
        volume = 900.0 + (i * 11.0)
        taker_buy = volume * (0.52 if i % 3 != 0 else 0.48)
        open_time = now_ms - ((limit - i) * candle_ms)
        close_time = open_time + candle_ms - 1
        candles.append(
            {
                "open_time_ms": open_time,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "close_time_ms": close_time,
                "quote_volume": volume * close_price,
                "trades": 1_000 + i * 4,
                "taker_buy_volume": taker_buy,
                "taker_buy_quote_volume": taker_buy * close_price,
            }
        )

    first_close = candles[0]["close"]
    last_close = candles[-1]["close"]
    price_change = last_close - first_close
    pct_change = (price_change / first_close * 100) if first_close else 0.0
    total_volume = sum(c["volume"] for c in candles)
    quote_volume = sum(c["quote_volume"] for c in candles)

    return {
        "ticker": {
            "symbol": "BTCUSDT",
            "last_price": last_close,
            "price_change": price_change,
            "price_change_pct": pct_change,
            "high_24h": max(c["high"] for c in candles),
            "low_24h": min(c["low"] for c in candles),
            "volume_24h": total_volume,
            "quote_volume_24h": quote_volume,
            "trades_24h": sum(c["trades"] for c in candles),
        },
        "funding": {
            "mark_price": last_close,
            "index_price": last_close - 2.0,
            "funding_rate": 0.0001,
            "next_funding_time_ms": now_ms + 8 * 3_600_000,
        },
        "oi": {
            "open_interest_contracts": 48_000.0,
            "open_interest_usd": 48_000.0 * last_close,
        },
        "candles": candles,
        "depth": {
            "bids": [[last_close - i * 5.0, 2.5 + i * 0.2] for i in range(1, 11)],
            "asks": [[last_close + i * 5.0, 2.5 + i * 0.2] for i in range(1, 11)],
        },
    }


def _load_dashboard_data(interval: str, limit: int) -> dict[str, Any]:
    try:
        return {
            "ticker": fetch_ticker(),
            "funding": fetch_funding_rate(),
            "oi": fetch_open_interest(),
            "candles": fetch_klines(interval=interval, limit=limit),
            "depth": fetch_order_book_depth(),
            "source": SOURCE_LIVE,
            "error": None,
        }
    except Exception as exc:
        fallback = _build_lite_fallback_data(interval=interval, limit=limit)
        fallback["source"] = "lite_fallback"
        fallback["error"] = str(exc)
        return fallback


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
    times = [datetime.fromtimestamp(c["open_time_ms"] / 1000, tz=timezone.utc) for c in candles]
    opens = [c["open"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    # Try plotly for candlestick, fall back to line chart
    try:
        import plotly.graph_objects as go

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=times,
                    open=opens,
                    high=highs,
                    low=lows,
                    close=closes,
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
        st.line_chart(closes, height=320)


def _render_lite_orientation(ticker: dict[str, Any], candles: list[dict], source: str) -> None:
    first_close = candles[0]["close"] if candles else ticker["last_price"]
    last_close = candles[-1]["close"] if candles else ticker["last_price"]
    if last_close > first_close:
        trend = "Uptrend"
    elif last_close < first_close:
        trend = "Downtrend"
    else:
        trend = "Flat"

    st.subheader("🧭 Dashboard Orientation")
    c1, c2, c3 = st.columns(3)
    c1.metric("Data Source", "Live" if source == SOURCE_LIVE else "Lite fallback")
    c2.metric("Window Trend", trend)
    c3.metric("Candles Loaded", f"{len(candles)}")
    st.caption("Core view: price trend, 24h move, participation, and order flow pressure.")


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

    if refresh_btn:
        # Streamlit added st.rerun in newer versions; keep legacy fallback for compatibility.
        rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
        if callable(rerun_fn):
            rerun_fn()

    if auto_refresh:
        # Static, trusted script — no user input involved.
        # Reloads the page every 30 seconds to pull fresh data.
        components.html(
            "<script>setTimeout(()=>window.location.reload(),30000);</script>",
            height=0,
        )

    # ── data fetch ────────────────────────────────────────────────────────────
    with st.spinner("Fetching live data …"):
        dashboard_data = _load_dashboard_data(interval=interval, limit=limit)

    ticker = dashboard_data["ticker"]
    funding = dashboard_data["funding"]
    oi = dashboard_data["oi"]
    candles = dashboard_data["candles"]
    depth = dashboard_data["depth"]
    source = dashboard_data["source"]
    error = dashboard_data["error"]

    if source != SOURCE_LIVE:
        st.warning("Live market data unavailable. Showing lite orientation mode.")
        st.caption(f"Fetch error: {error}")

    # ── timestamp ─────────────────────────────────────────────────────────────
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.caption(f"Last updated: {now_utc}")

    _render_lite_orientation(ticker=ticker, candles=candles, source=source)

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
