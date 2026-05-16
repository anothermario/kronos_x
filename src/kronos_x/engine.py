from __future__ import annotations

from dataclasses import dataclass

from .interfaces import Broker, Journal, MarketDataProvider, RiskManager, StrategyEngine


@dataclass(slots=True)
class TradingEngine:
    symbol: str
    market_data: MarketDataProvider
    strategy: StrategyEngine
    risk: RiskManager
    broker: Broker
    journal: Journal
    equity: float

    def run_once(self) -> dict:
        candle = self.market_data.latest_candle(self.symbol)
        signal = self.strategy.generate_signal(candle)

        event: dict = {
            "timestamp": candle.timestamp.isoformat(),
            "symbol": self.symbol,
            "close": candle.close,
            "signal": {
                "side": signal.side,
                "confidence": signal.confidence,
                "reason": signal.reason,
            },
        }

        order = self.risk.to_order(signal, self.equity)
        if order is None:
            event["action"] = "skip"
            event["result"] = "risk_rejected_or_hold"
            self.journal.write_event(event)
            return event

        result = self.broker.submit(order)
        event["action"] = "submit_order"
        event["order"] = {
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "order_type": order.order_type,
        }
        event["execution"] = {
            "accepted": result.accepted,
            "message": result.message,
            "order_id": result.order_id,
        }
        self.journal.write_event(event)
        return event
