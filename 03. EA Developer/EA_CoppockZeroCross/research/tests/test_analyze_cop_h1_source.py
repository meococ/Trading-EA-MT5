from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

PATH = Path(__file__).resolve().parents[1] / "analyze_cop_h1_source.py"
SPEC = spec_from_file_location("cop", PATH); MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader; SPEC.loader.exec_module(MODULE)


def test_coppock_first_indices_and_wma_weights() -> None:
    close = np.arange(1.0, 50.0)
    roc11, roc14, curve = MODULE.coppock(close)
    assert np.isnan(roc11[10]) and np.isfinite(roc11[11])
    assert np.isnan(roc14[13]) and np.isfinite(roc14[14])
    assert np.isnan(curve[22]) and np.isfinite(curve[23])
    raw = roc11 + roc14
    assert curve[23] == np.dot(raw[14:24], np.arange(1.0, 11.0)) / 55.0


def test_roc_formula_is_exact() -> None:
    close = np.linspace(1.0, 2.0, 50)
    roc11, roc14, _ = MODULE.coppock(close)
    assert roc11[11] == 100.0 * (close[11] / close[0] - 1.0)
    assert roc14[14] == 100.0 * (close[14] / close[0] - 1.0)


def test_event_allowlist_is_outcome_blind() -> None:
    forbidden = {"entry", "exit", "return", "pnl", "profit_factor", "cost"}
    assert not (MODULE.EVENT_KEYS & forbidden)


def test_sealed_dual_clock_and_decision_year() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert "pd.Timedelta(hours=1)" in source and "+ 3600.0" in source
    assert 'pd.Timestamp(row["decision_time_utc"]).year' in source
    assert '"next_row_ohlc_read": False' in source


def test_claim_and_bound_input_sealing() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert 'initial["analyzer"] != claimed' in source
    assert "if final != initial" in source
    assert '"test": test_path' in source


def test_zero_cross_equalities_are_frozen() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert "np.roll(curve, 1) <= 0.0" in source and "curve > 0.0" in source
    assert "np.roll(curve, 1) >= 0.0" in source and "curve < 0.0" in source
