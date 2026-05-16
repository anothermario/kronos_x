from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Candle:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True)
class Signal:
    symbol: str
    side: str  # buy | sell | hold
    confidence: float
    reason: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Order:
    symbol: str
    side: str
    quantity: float
    timestamp: datetime
    order_type: str = "market"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TradeResult:
    accepted: bool
    message: str
    order_id: str | None = None
