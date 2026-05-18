import unittest

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
        original_fetch_ticker = dashboard.fetch_ticker

        def _raise_error() -> dict:
            raise RuntimeError("boom")

        try:
            dashboard.fetch_ticker = _raise_error  # type: ignore[assignment]
            payload = dashboard._load_dashboard_data(interval="1h", limit=24)
        finally:
            dashboard.fetch_ticker = original_fetch_ticker  # type: ignore[assignment]

        self.assertEqual("lite_fallback", payload["source"])
        self.assertIn("boom", payload["error"])
        self.assertEqual(24, len(payload["candles"]))


if __name__ == "__main__":
    unittest.main()
