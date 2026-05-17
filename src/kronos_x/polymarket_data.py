"""Polymarket-style data layer for BTC/USD futures.

Fetches public data from Binance Futures REST API (no API key required).
All functions return plain dicts/lists so the dashboard layer stays decoupled.
"""
from __future__ import annotations

import urllib.error
import urllib.request
import json
from typing import Any


_BASE = "https://fapi.binance.com"
_SYMBOL = "BTCUSDT"
_TIMEOUT = 8


def _get(path: str, params: dict[str, str] | None = None) -> Any:
    url = f"{_BASE}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def fetch_ticker() -> dict[str, Any]:
    """24-hour rolling-window price statistics for BTCUSDT perpetual."""
    data = _get("/fapi/v1/ticker/24hr", {"symbol": _SYMBOL})
    return {
        "symbol": data.get("symbol", _SYMBOL),
        "last_price": float(data.get("lastPrice", 0)),
        "price_change": float(data.get("priceChange", 0)),
        "price_change_pct": float(data.get("priceChangePercent", 0)),
        "high_24h": float(data.get("highPrice", 0)),
        "low_24h": float(data.get("lowPrice", 0)),
        "volume_24h": float(data.get("volume", 0)),
        "quote_volume_24h": float(data.get("quoteVolume", 0)),
        "trades_24h": int(data.get("count", 0)),
    }


def fetch_funding_rate() -> dict[str, Any]:
    """Latest funding rate and next funding time."""
    data = _get("/fapi/v1/premiumIndex", {"symbol": _SYMBOL})
    return {
        "mark_price": float(data.get("markPrice", 0)),
        "index_price": float(data.get("indexPrice", 0)),
        "funding_rate": float(data.get("lastFundingRate", 0)),
        "next_funding_time_ms": int(data.get("nextFundingTime", 0)),
    }


def fetch_open_interest() -> dict[str, Any]:
    """Current open interest in contracts and USD."""
    data = _get("/fapi/v1/openInterest", {"symbol": _SYMBOL})
    oi_contracts = float(data.get("openInterest", 0))
    # fetch ticker separately to get last price for USD conversion
    try:
        ticker = _get("/fapi/v1/ticker/price", {"symbol": _SYMBOL})
        last = float(ticker.get("price", 0))
    except Exception:
        last = 0.0
    return {
        "open_interest_contracts": oi_contracts,
        "open_interest_usd": oi_contracts * last,
    }


def fetch_klines(interval: str = "1h", limit: int = 48) -> list[dict[str, Any]]:
    """OHLCV kline data.

    interval: e.g. '1m', '5m', '15m', '1h', '4h', '1d'
    limit: number of candles (max 1500)
    """
    raw = _get(
        "/fapi/v1/klines",
        {"symbol": _SYMBOL, "interval": interval, "limit": str(limit)},
    )
    candles = []
    for row in raw:
        candles.append(
            {
                "open_time_ms": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "close_time_ms": int(row[6]),
                "quote_volume": float(row[7]),
                "trades": int(row[8]),
                "taker_buy_volume": float(row[9]),
                "taker_buy_quote_volume": float(row[10]),
            }
        )
    return candles


def fetch_order_book_depth(limit: int = 10) -> dict[str, Any]:
    """Best bids and asks from the order book."""
    data = _get("/fapi/v1/depth", {"symbol": _SYMBOL, "limit": str(limit)})
    bids = [[float(p), float(q)] for p, q in data.get("bids", [])]
    asks = [[float(p), float(q)] for p, q in data.get("asks", [])]
    return {"bids": bids, "asks": asks}
