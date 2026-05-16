from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

try:
    from .engine import TradingEngine
    from .journal import JsonlJournal
    from .models import Candle, Order, Signal, TradeResult
    from .open_points import OPEN_POINTS
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from kronos_x.engine import TradingEngine
    from kronos_x.journal import JsonlJournal
    from kronos_x.models import Candle, Order, Signal, TradeResult
    from kronos_x.open_points import OPEN_POINTS


@dataclass
class MockMarketData:
    def latest_candle(self, symbol: str) -> Candle:
        return Candle(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=102.0,
            low=99.5,
            close=101.2,
            volume=1234.0,
        )


@dataclass
class BasicMomentumStrategy:
    threshold: float = 0.5

    def generate_signal(self, candle: Candle) -> Signal:
        delta = candle.close - candle.open
        if delta > self.threshold:
            return Signal(
                candle.symbol,
                "buy",
                0.6,
                "close_above_open",
                candle.timestamp,
                metadata={"price": candle.close},
            )
        if delta < -self.threshold:
            return Signal(
                candle.symbol,
                "sell",
                0.6,
                "close_below_open",
                candle.timestamp,
                metadata={"price": candle.close},
            )
        return Signal(
            symbol=candle.symbol,
            side="hold",
            confidence=0.5,
            reason="no_edge",
            timestamp=candle.timestamp,
            metadata={"price": candle.close},
        )


@dataclass
class BasicRisk:
    risk_fraction: float = 0.01
    min_quantity: float = 0.001

    def to_order(self, signal: Signal, equity: float) -> Order | None:
        if signal.side == "hold":
            return None
        price = float(signal.metadata.get("price", 0.0))
        if price <= 0:
            return None
        qty = (equity * self.risk_fraction) / price
        if qty < self.min_quantity:
            return None
        return Order(symbol=signal.symbol, side=signal.side, quantity=round(qty, 6), timestamp=signal.timestamp)


@dataclass
class PaperBroker:
    def submit(self, order: Order) -> TradeResult:
        if order.side not in {"buy", "sell"}:
            return TradeResult(accepted=False, message="invalid_side")
        if order.quantity <= 0:
            return TradeResult(accepted=False, message="invalid_quantity")
        return TradeResult(accepted=True, message="paper_fill", order_id=f"paper-{uuid4()}")


def run_demo(symbol: str = "BTCUSDT") -> dict:
    engine = TradingEngine(
        symbol=symbol,
        market_data=MockMarketData(),
        strategy=BasicMomentumStrategy(),
        risk=BasicRisk(),
        broker=PaperBroker(),
        journal=JsonlJournal("logs/trading_events.jsonl"),
        equity=10_000.0,
    )
    return engine.run_once()


if __name__ == "__main__":
    event = run_demo()
    print(event)
    print("OPEN_POINTS:")
    for key, value in OPEN_POINTS.items():
        print(f"- {key}: {value}")
