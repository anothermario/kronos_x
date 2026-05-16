import unittest

from src.kronos_x.main import run_demo


class TestEngine(unittest.TestCase):
    def test_run_demo_returns_event(self) -> None:
        event = run_demo()
        self.assertIn("symbol", event)
        self.assertIn("signal", event)
        self.assertIn("action", event)


if __name__ == "__main__":
    unittest.main()
