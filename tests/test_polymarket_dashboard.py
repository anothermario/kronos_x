import unittest
from unittest.mock import patch

from src.kronos_x import polymarket_dashboard as dashboard


class TestPolymarketDashboardFallback(unittest.TestCase):
    def test_build_lite_fallback_data_includes_minimum_dashboard_payload(self) -> None:
        payload = dashboard._build_lite_fallback_data(interval="1h", limit=24)

        self.assertIn("ticker", payload)
        self.assertIn("candles", payload)
        self.assertIn("depth", payload)
        self.assertEqual(24, len(payload["candles"]))
        self.assertGreater(payload["ticker"]["last_price"], 0)
        self.assertEqual(10, len(payload["depth"]["bids"]))
        self.assertEqual(10, len(payload["depth"]["asks"]))

    def test_load_dashboard_data_returns_fallback_on_fetch_failure(self) -> None:
        def _raise_error() -> dict:
            raise RuntimeError("boom")

        with patch.object(dashboard, "fetch_ticker", side_effect=_raise_error):
            payload = dashboard._load_dashboard_data(interval="1h", limit=24)

        self.assertEqual("lite_fallback", payload["source"])
        self.assertIn("boom", payload["error"])
        self.assertEqual(24, len(payload["candles"]))


if __name__ == "__main__":
    unittest.main()
