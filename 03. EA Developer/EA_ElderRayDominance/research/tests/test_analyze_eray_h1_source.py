from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd


PATH = Path(__file__).resolve().parents[1] / "analyze_eray_h1_source.py"
SPEC = spec_from_file_location("eray", PATH)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def frame(rows: list[tuple[str, float, float, float]]) -> pd.DataFrame:
    times = pd.to_datetime([row[0] for row in rows], utc=True)
    return pd.DataFrame({
        "symbol": "EURUSD",
        "timeframe": "H1",
        "source_epoch": times.astype("int64") // 1_000_000_000,
        "time_utc": times,
        "utc_ambiguous": False,
        "high": [row[1] for row in rows],
        "low": [row[2] for row in rows],
        "close": [row[3] for row in rows],
    })


def test_ema13_uses_sma_seed_then_exact_recursion() -> None:
    close = pd.Series(range(1, 16), dtype=float).to_numpy()
    ema = MODULE.ema13(close)
    assert pd.isna(ema[11])
    assert ema[12] == 7.0
    assert ema[13] == (2.0 / 14.0) * 14.0 + (12.0 / 14.0) * 7.0


def test_strict_dominance_transitions_and_equality() -> None:
    rows = []
    start = pd.Timestamp("2017-12-31T10:00:00Z")
    for index in range(12):
        stamp = start + pd.Timedelta(hours=index)
        rows.append((stamp.isoformat(), 1.0, 1.0, 1.0))
    rows += [
        ((start + pd.Timedelta(hours=12)).isoformat(), 1.0, 1.0, 1.0),
        ((start + pd.Timedelta(hours=13)).isoformat(), 1.2, 1.0, 1.1),
        ((start + pd.Timedelta(hours=14)).isoformat(), 1.3, 1.2, 1.25),
        ((start + pd.Timedelta(hours=15)).isoformat(), 1.1, 0.8, 0.9),
    ]
    data = frame(rows)
    ema = MODULE.ema13(data["close"].to_numpy(dtype=float))
    bear = data["low"].to_numpy(dtype=float) - ema
    assert bear[13] <= 0.0
    assert bear[14] > 0.0


def test_event_ledger_allowlist_has_no_outcome_fields() -> None:
    assert "entry_price" not in MODULE.EVENT_KEYS
    assert "return" not in MODULE.EVENT_KEYS
    assert "pnl" not in MODULE.EVENT_KEYS
    assert "profit_factor" not in MODULE.EVENT_KEYS


def test_claim_precedes_prereg_manifest_and_data_hashes() -> None:
    source = PATH.read_text(encoding="utf-8")
    start = source.index(
        "started, marker_path, claimed_analyzer_sha = claim_attempt(output_dir)"
    )
    initial_hashes = source.index(
        "initial_hashes = {name: sha256_file(path) for name, path in bound_inputs.items()}",
        start,
    )
    assert start < initial_hashes
    assert source.index('"prereg": prereg', start) < initial_hashes
    assert source.index('"manifest": manifest', start) < initial_hashes
    assert source.index('"data": data_path', start) < initial_hashes


def test_exact_next_requires_both_clocks_and_never_reads_next_ohlc() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert 'pd.Timedelta(hours=1)' in source
    assert '+ 3600.0' in source
    assert '"next_row_ohlc_read": False' in source
    assert '"next_row_ohlc_reads": 0' in source


def test_year_bucketing_uses_decision_time_utc() -> None:
    events = [{
        "source_bar_time_utc": "2020-12-31T23:00:00Z",
        "decision_time_utc": "2021-01-01T00:00:00Z",
    }]
    assert MODULE.decision_years(events).tolist() == [2021]


def test_bound_inputs_are_rehashed_and_test_is_receipt_bound() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert '"test": test_path' in source
    assert 'final_hashes != initial_hashes' in source
    assert '"sha256": initial_hashes["test"]' in source


def test_claimed_analyzer_hash_is_the_executed_input_identity() -> None:
    source = PATH.read_text(encoding="utf-8")
    claim = source.index("claimed_analyzer_sha = sha256_file(Path(__file__).resolve())")
    initial = source.index('initial_hashes = {name: sha256_file(path)')
    comparison = source.index('initial_hashes["analyzer"] != claimed_analyzer_sha')
    assert claim < initial < comparison
