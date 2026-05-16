from src.kronos_x.main import run_demo


def test_run_demo_returns_event() -> None:
    event = run_demo()
    assert "symbol" in event
    assert "signal" in event
    assert "action" in event
