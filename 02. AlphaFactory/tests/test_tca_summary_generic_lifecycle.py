import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "tca_summary.py"
SPEC = importlib.util.spec_from_file_location("tca_summary_generic_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
TCA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TCA)


def test_generic_lifecycle_v3_is_discovered_and_reconciled(tmp_path: Path) -> None:
    token = "HYP-GENERIC_123"
    trades = tmp_path / f"EURUSD_LifecycleTrades_{token}.csv"
    trades.write_text(
        "action,is_final_close,close_source,deal_reason,achievedr,net_profit\n"
        "OPEN,0,DEAL_REASON_EXPERT,DEAL_REASON_EXPERT,0,0\n"
        "CLOSE,0,EA_TP1,DEAL_REASON_EXPERT,1.0,4.0\n"
        "CLOSE,1,DEAL_REASON_TP,DEAL_REASON_TP,2.0,8.0\n",
        encoding="utf-8",
    )
    meta = tmp_path / f"EURUSD_RunMeta_{token}.json"
    meta.write_text(
        json.dumps(
            {
                "schema_version": "alphafactory_run_meta.v1",
                "run_id": token,
                "funnel": {"entries_opened": 1, "final_closes": 1},
            }
        ),
        encoding="utf-8",
    )

    selected_token, exec_file, trade_file, meta_file = TCA.select_run_files(tmp_path)
    summary = TCA.analyze_trades(trade_file)

    assert selected_token == token
    assert exec_file is None
    assert trade_file == trades
    assert meta_file == meta
    assert summary["rows"] == 3
    assert summary["final_closes"] == 1
    assert summary["partial_close_rows"] == 1
    assert summary["net_profit"]["n"] == 1
