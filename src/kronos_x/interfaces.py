from __future__ import annotations

from typing import Protocol

from .models import Candle, Order, Signal, TradeResult


class MarketDataProvider(Protocol):
    def latest_candle(self, symbol: str) -> Candle: ...


class StrategyEngine(Protocol):
    def generate_signal(self, candle: Candle) -> Signal: ...


class RiskManager(Protocol):
    def to_order(self, signal: Signal, equity: float) -> Order | None: ...


class Broker(Protocol):
    def submit(self, order: Order) -> TradeResult: ...


class Journal(Protocol):
    def write_event(self, event: dict) -> None: ...
