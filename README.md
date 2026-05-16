# kronos_x

Initial trading framework scaffold, created to implement what is unblocked right now.

## Implemented now
- Core trading domain models (`Candle`, `Signal`, `Order`, `TradeResult`)
- Interface contracts for market data, strategy, risk manager, broker, and journal
- `TradingEngine` orchestration (`run_once`) with event journaling
- JSONL journal sink at `logs/trading_events.jsonl`
- Runnable demo with mock providers (`python -m src.kronos_x.main`)
- Basic test for engine demo behavior

## Open points (explicitly left TBD)
See `src/kronos_x/open_points.py`.

Most important pending decision from your instruction:
- `davidddtech_replacement`: **TBD by user**

## What I need from you
Please tell me what to use instead of the davidddtech part, so I can wire the real provider/integration next.

## Run
```bash
python -m src.kronos_x.main
streamlit run streamlit_app.py
python -m unittest discover -s tests -q
```
