from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


RESEARCH = Path(__file__).resolve().parents[1]
PATH = RESEARCH / "quote_eurfxofi_cme6e_001.py"
SPEC = importlib.util.spec_from_file_location("quote_eurfxofi_cme6e_001", PATH)
assert SPEC is not None and SPEC.loader is not None
quote = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = quote
SPEC.loader.exec_module(quote)


def test_winter_window_is_utc_plus_one() -> None:
    assert quote.build_window("2019-01-03")["start"] == "2019-01-03T13:14:30.000Z"
    assert quote.build_window("2019-01-03")["end"] == "2019-01-03T13:15:00.000Z"


def test_summer_window_is_utc_plus_two() -> None:
    assert quote.build_window("2019-07-03")["start"] == "2019-07-03T12:14:30.000Z"
    assert quote.build_window("2019-07-03")["end"] == "2019-07-03T12:15:00.000Z"


def test_window_is_exactly_thirty_seconds() -> None:
    from datetime import datetime
    window = quote.build_window("2020-10-26")
    start = datetime.fromisoformat(window["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(window["end"].replace("Z", "+00:00"))
    assert (end - start).total_seconds() == 30


def test_quote_all_never_calls_timeseries() -> None:
    class Metadata:
        def __init__(self): self.cost = 0; self.size = 0
        def get_cost(self, **kwargs): self.cost += 1; return 0.1
        def get_billable_size(self, **kwargs): self.size += 1; return 100
    class Client:
        def __init__(self): self.metadata = Metadata()
    clients = []
    def factory():
        client = Client(); clients.append(client); return client
    windows = [quote.build_window("2019-01-03"), quote.build_window("2019-01-04")]
    rows = quote.quote_all(factory, windows, workers=1)
    assert sum(c.metadata.cost for c in clients) == 2
    assert sum(c.metadata.size for c in clients) == 2
    assert sum(r["billable_bytes"] for r in rows) == 200
