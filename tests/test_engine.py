import unittest
from datetime import datetime, timezone

from src.kronos_x.main import BasicRisk, PaperBroker, run_demo
from src.kronos_x.models import Order, Signal


class TestEngine(unittest.TestCase):
    def test_run_demo_returns_event_with_required_fields(self) -> None:
        event = run_demo()
        self.assertIn("symbol", event)
        self.assertIn("signal", event)
        self.assertIn("action", event)

    def test_basic_risk_rejects_hold_signal(self) -> None:
        risk = BasicRisk(risk_fraction=0.01, min_quantity=0.001)
        signal = Signal(
            symbol="BTCUSDT",
            side="hold",
            confidence=0.5,
            reason="no_edge",
            timestamp=datetime.now(timezone.utc),
            metadata={"price": 100.0},
        )
        self.assertIsNone(risk.to_order(signal, 10_000.0))

    def test_basic_risk_rejects_invalid_price(self) -> None:
        risk = BasicRisk(risk_fraction=0.01, min_quantity=0.001)
        signal = Signal(
            symbol="BTCUSDT",
            side="buy",
            confidence=0.6,
            reason="entry",
            timestamp=datetime.now(timezone.utc),
            metadata={"price": 0.0},
        )
        self.assertIsNone(risk.to_order(signal, 10_000.0))

    def test_basic_risk_rejects_sub_minimum_quantity(self) -> None:
        risk = BasicRisk(risk_fraction=0.01, min_quantity=2.0)
        signal = Signal(
            symbol="BTCUSDT",
            side="buy",
            confidence=0.6,
            reason="entry",
            timestamp=datetime.now(timezone.utc),
            metadata={"price": 100.0},
        )
        self.assertIsNone(risk.to_order(signal, 10_000.0))

    def test_paper_broker_rejects_invalid_order(self) -> None:
        broker = PaperBroker()
        bad_order = Order(
            symbol="BTCUSDT",
            side="hold",
            quantity=0.0,
            timestamp=datetime.now(timezone.utc),
        )
        result = broker.submit(bad_order)
        self.assertFalse(result.accepted)


if __name__ == "__main__":
    unittest.main()
