from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_AIRQMB_RegimeFusion"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
RESULTS = PACKAGE / "research" / "screen006_results.json"
RESULTS_SHA256 = "598438A9B0A50C313E7B10F99B0D1E62369314EA57E77EE0DB6D2098DFCC0EFC"
REPORT_SHA256 = "F5D2ED6EEBD45A60BE45C65E197BAE9858B431160705D03F6A3F6ECAC22AE35A"


def main() -> None:
    lines = [line for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest: dict[str, dict] = {}
    for line in lines:
        row = json.loads(line)
        latest[row["hypothesis_id"]] = row
    packet = json.loads(RESULTS.read_text(encoding="utf-8"))
    appended: list[dict] = []

    for result in packet["results"]:
        symbol = result["symbol"]
        hypothesis_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-006"
        prior = latest[hypothesis_id]
        if prior.get("state") != "probe":
            raise SystemExit(f"unexpected SCREEN-006 state: {hypothesis_id}")
        row = deepcopy(prior)
        row["state"] = "killed"
        row["verdict"] = "KILL_NO_EDGE_REAL_TICKS_NO_PARAMETER_GRID"
        row["reason"] = (
            f"Frozen real-tick baseline failed: PF={result['profit_factor']:.3f}, "
            f"expectancy={result['expectancy_per_trade']:.2f}/trade, "
            f"DD={result['max_drawdown_pct']:.2f}%, cadence={result['trades_per_week']:.2f}/week. "
            "No symbol cleared the preregistered screen, so the per-pair grid stayed locked."
        )
        row["updated_at_utc"] = "2026-08-05T19:50:00Z"
        row["run_ids"] = [result["run_id"]]
        row["metrics"] = {
            "mt5_launches": 1,
            "reports_generated": 1,
            "performance_outcome_reads": 1,
            "economic_trials_consumed": 1,
            "optimization_trials_consumed": 0,
            "history_quality_pct": result["history_quality_pct"],
            "trades": result["trades"],
            "trades_per_week": result["trades_per_week"],
            "long_trades": result["long_trades"],
            "short_trades": result["short_trades"],
            "profit_factor": result["profit_factor"],
            "net_profit": result["net_profit"],
            "expectancy_per_trade": result["expectancy_per_trade"],
            "max_drawdown_pct": result["max_drawdown_pct"],
            "win_rate_pct": result["win_rate_pct"],
            "first_close_utc": result["first_close_utc"],
            "last_close_utc": result["last_close_utc"],
            "account_lock_rejects": result["account_lock_rejects"],
        }
        row["validation"].update({
            "engineering_valid": True,
            "indicator_runtime_smoke": "PASS",
            "order_execution_smoke": "PASS",
            "lifecycle_reconciliation": "PASS",
            "model4_screen_authorized": False,
            "model0_authorized": False,
            "optimization_authorized": False,
            "validation_access_authorized": False,
            "holdout_access_authorized": False,
            "economic_valid": False,
            "promotion_eligible": False,
            "screen_pass": False,
            "screen_gate": result["screen_gate"],
            "no_parameter_grid": True,
            "results_json_sha256": RESULTS_SHA256,
            "results_report_sha256": REPORT_SHA256,
        })
        appended.append(row)

    with REGISTRY.open("a", encoding="utf-8", newline="\n") as handle:
        for row in appended:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")
    print("killed 9 SCREEN-006 cells; zero optimization survivors")


if __name__ == "__main__":
    main()
