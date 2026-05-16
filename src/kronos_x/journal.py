from __future__ import annotations

import json
from pathlib import Path


class JsonlJournal:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: dict) -> None:
        try:
            payload = json.dumps(event, ensure_ascii=False)
        except TypeError as exc:
            raise ValueError(f"Event is not JSON serializable: {event}") from exc

        with self.path.open("a", encoding="utf-8") as f:
            f.write(payload + "\n")
