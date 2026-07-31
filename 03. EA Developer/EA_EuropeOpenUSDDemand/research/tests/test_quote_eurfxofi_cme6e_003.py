from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import sys


RESEARCH = Path(__file__).resolve().parents[1]
PATH = RESEARCH / "quote_eurfxofi_cme6e_003.py"
SPEC = importlib.util.spec_from_file_location("quote_eurfxofi_cme6e_003", PATH)
assert SPEC is not None and SPEC.loader is not None
quote = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = quote
SPEC.loader.exec_module(quote)


def row(day: str, split: str = "TRAIN") -> dict[str, str]:
    return {"request_id": f"ECBFX-{day}", "local_date": day, "split": split}


def test_winter_window_is_exact_final_fifteen_seconds() -> None:
    window = quote.build_window(row("2019-01-03"))
    assert window["start"] == "2019-01-03T13:14:45.000Z"
    assert window["end"] == "2019-01-03T13:15:00.000Z"


def test_summer_window_is_exact_final_fifteen_seconds() -> None:
    window = quote.build_window(row("2019-07-03"))
    assert window["start"] == "2019-07-03T12:14:45.000Z"
    assert window["end"] == "2019-07-03T12:15:00.000Z"
    start = datetime.fromisoformat(window["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(window["end"].replace("Z", "+00:00"))
    assert (end - start).total_seconds() == quote.WINDOW_SECONDS == 15


def test_quote_all_calls_metadata_only() -> None:
    class Metadata:
        def __init__(self) -> None:
            self.cost = 0
            self.size = 0

        def get_cost(self, **kwargs):
            self.cost += 1
            return 0.1

        def get_billable_size(self, **kwargs):
            self.size += 1
            return 100

    class Client:
        def __init__(self) -> None:
            self.metadata = Metadata()

    clients = []

    def factory():
        client = Client()
        clients.append(client)
        return client

    windows = [quote.build_window(row("2019-01-03")), quote.build_window(row("2019-01-04"))]
    rows = quote.quote_all(factory, windows, workers=1)
    assert sum(client.metadata.cost for client in clients) == 2
    assert sum(client.metadata.size for client in clients) == 2
    assert sum(item["billable_bytes"] for item in rows) == 200


def test_ceiling_and_window_are_frozen() -> None:
    assert quote.OWNER_CEILING_USD == 2.25
    assert quote.WINDOW_SECONDS == 15
    assert quote.EXPECTED_DATES == sum(quote.EXPECTED_SPLITS.values()) == 1359
