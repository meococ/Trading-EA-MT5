from pathlib import Path
import json

parsed = Path(r"d:\Trading EA MT5\02. AlphaFactory\runs\EA_M15TickVolImpulse\20260713_235635\report_parsed.json")
out = {
    "run_id": "20260713_235635",
    "hypothesis_id": "HYP-TICKVOL-IMPULSE-M15-001",
    "ea": "EA_M15TickVolImpulse",
    "symbol": "USDJPY",
    "period": "M15",
    "model": 0,
    "window": "2021.01.01-2025.12.31",
    "pf": 1.00,
    "trades": 890,
    "net_profit": -109.56,
    "gross_profit": 27203.83,
    "gross_loss": -27313.39,
    "expectancy": -0.12,
    "max_equity_dd_pct": 23.41,
    "win_rate_pct": 40.79,
    "elapsed_calendar_weeks": 260.71,
    "trades_per_elapsed_week": 3.41,
    "verdict": "killed",
    "note": "Tong loi nhuan rong=-109.56; Loi nhuan rong label is gross profit in VI MT5 report",
}
parsed.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print("parsed ok")

reg = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\CANDIDATE_REGISTRY.jsonl")
lines = reg.read_text(encoding="utf-8").splitlines()
updated = False
new_lines = []
for ln in lines:
    if "HYP-TICKVOL-IMPULSE-M15-001" in ln:
        obj = json.loads(ln)
        obj["state"] = "killed"
        obj["readout_path"] = (
            "03. EA Developer/EA_SonicR/research/readouts/"
            "20260713_HYP_TICKVOL_IMPULSE_M15_001_READOUT.md"
        )
        obj["run_ids"] = ["20260713_235635"]
        obj["metrics"] = {
            "trades": 890,
            "trades_per_elapsed_week": 3.41,
            "pf": 1.00,
            "net": -109.56,
            "max_dd_pct": 23.41,
            "expectancy": -0.12,
        }
        obj["verdict"] = "kill"
        obj["reason"] = (
            "Model 0 USDJPY M15 2021-2025: PF 1.00, net -109.56, expectancy -0.12, "
            "cadence 3.41/week. Cadence OK; edge fail. Do not mine vol/body/CI/hours/days."
        )
        obj["updated_at"] = "2026-07-13"
        new_lines.append(json.dumps(obj, ensure_ascii=False))
        updated = True
    else:
        new_lines.append(ln)
if updated:
    reg.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("registry updated", updated)
