#!/usr/bin/env python3
"""Append final parked registry rows for HYP-MZMS-XAU-M5-007..010."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REG = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
EVID = (
    "03. EA Developer/EA_MZMS_Scalper/research/evidence/"
    "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400"
)
READOUT = (
    "03. EA Developer/EA_MZMS_Scalper/research/"
    "HYP-MZMS-XAU-M5-007-010_GROK_SYNTHESIS_READOUT.md"
)
SOURCE = "03. EA Developer/EA_MZMS_Scalper/EA_MZMS_Scalper.mq5"
PREREG = (
    "03. EA Developer/EA_MZMS_Scalper/research/"
    "HYP-MZMS-XAU-M5-007-010_FROZEN_PREREG.md"
)
NR = (
    "03. EA Developer/EA_MZMS_Scalper/research/evidence/"
    "20260722_NONREPAINT_AUDIT_V8/nonrepaint_audit.json"
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest().upper()


ROWS = {
    "HYP-MZMS-XAU-M5-007": {
        "run_id": "20260722_015121",
        "family": "closed-bar-xau-m5-donchian-fresh-impulse-atr-expansion-adx-rise",
        "overrides": (
            "Window=2018.01.01-2026.07.22;XAUUSD;M5;Model0;InpSignalMode=2;"
            "InpHypothesisId=HYP-MZMS-XAU-M5-007;InpMagic=5600727;RiskPercent=0.01;"
            "Deposit=100000;Leverage=100;RequireNewsGuard=false;MaxSpreadXauPoints=35;"
            "StopLookback=5;StopAtr=1.5;StopBufferXauPoints=40;TargetRR=1.6;MaxHoldBars=15;"
            "CooldownBars=5;BreakEven=false;Intrabar=false;SessionUtc=08-17;FlattenUtc=18:15;"
            "Mechanism=Donchian20FreshImpulseAtrExpansionAdxRise"
        ),
        "trades": 3409,
        "pf": 0.8091258725,
        "net": -2064.59,
        "wr": 42.0358,
        "exp": -0.605629,
        "dd": 2.191,
        "cadence": 7.64,
        "executed": 100,
        "near_miss": 0,
        "reason": (
            "Park invalid: Model-0 run 20260722_015121 delivered history quality 98% < frozen 99%. "
            "Diagnostic-only metrics N=3409 PF=0.8091258725 net=-2064.59 WR=42.0358% expectancy=-0.605629 "
            "DD=2.191% cadence~7.64/elapsed-week. Exact lifecycle reconciliation. 100 executed forensic charts "
            "+ Grok synthesis. Directory 20260722_015320 is a partial excluded non-outcome and is not counted. "
            "No promotion/economic authority; no post-hoc rescue/rerun."
        ),
    },
    "HYP-MZMS-XAU-M5-008": {
        "run_id": "20260722_021353",
        "family": "closed-bar-xau-m5-ema20-ema100-trend-pullback-pivot-reclaim",
        "overrides": (
            "Window=2018.01.01-2026.07.22;XAUUSD;M5;Model0;InpSignalMode=3;"
            "InpHypothesisId=HYP-MZMS-XAU-M5-008;InpMagic=5600728;RiskPercent=0.01;"
            "Deposit=100000;Leverage=100;RequireNewsGuard=false;MaxSpreadXauPoints=35;"
            "StopLookback=5;StopAtr=1.5;StopBufferXauPoints=40;TargetRR=1.6;MaxHoldBars=15;"
            "CooldownBars=5;BreakEven=false;Intrabar=false;SessionUtc=08-17;FlattenUtc=18:15;"
            "Mechanism=EMA20EMA100TrendPullbackPivotReclaim"
        ),
        "trades": 80,
        "pf": 1.0699336109,
        "net": 24.86,
        "wr": 42.5,
        "exp": 0.31075,
        "dd": 0.11998,
        "cadence": 0.18,
        "executed": 80,
        "near_miss": 20,
        "reason": (
            "Park invalid: Model-0 run 20260722_021353 delivered history quality 98% < frozen 99%. "
            "Diagnostic-only metrics N=80 PF=1.0699336109 net=+24.86 WR=42.5% expectancy=+0.31075 "
            "DD=0.11998% cadence~0.18/elapsed-week (under-cadence). Exact lifecycle reconciliation. "
            "80 executed + 20 offline near-miss charts + Grok synthesis. Strongest relative diagnostic shape "
            "but not promotable. Post-run orchestration later failed on obsolete packet fingerprint and does "
            "not invalidate this single bound run. No promotion/economic authority; no post-hoc rescue/rerun."
        ),
    },
    "HYP-MZMS-XAU-M5-009": {
        "run_id": "20260722_023841",
        "family": "closed-bar-xau-m5-bollinger-atr-compression-envelope-breakout",
        "overrides": (
            "Window=2018.01.01-2026.07.22;XAUUSD;M5;Model0;InpSignalMode=4;"
            "InpHypothesisId=HYP-MZMS-XAU-M5-009;InpMagic=5600729;RiskPercent=0.01;"
            "Deposit=100000;Leverage=100;RequireNewsGuard=false;MaxSpreadXauPoints=35;"
            "StopLookback=5;StopAtr=1.5;StopBufferXauPoints=40;TargetRR=1.6;MaxHoldBars=15;"
            "CooldownBars=5;BreakEven=false;Intrabar=false;SessionUtc=08-17;FlattenUtc=18:15;"
            "Mechanism=Bollinger20ATRCompressionEnvelopeBreakout"
        ),
        "trades": 1041,
        "pf": 0.9264545799,
        "net": -252.68,
        "wr": 43.9962,
        "exp": -0.242728,
        "dd": 0.4893,
        "cadence": 2.33,
        "executed": 100,
        "near_miss": 0,
        "reason": (
            "Park invalid: Model-0 run 20260722_023841 delivered history quality 98% < frozen 99%. "
            "Diagnostic-only metrics N=1041 PF=0.9264545799 net=-252.68 WR=43.9962% expectancy=-0.242728 "
            "DD=0.4893% cadence~2.33/elapsed-week (inside band but negative expectancy). Exact lifecycle "
            "reconciliation. 100 executed forensic charts + Grok synthesis. No promotion/economic authority; "
            "no post-hoc rescue/rerun."
        ),
    },
    "HYP-MZMS-XAU-M5-010": {
        "run_id": "20260722_024229",
        "family": "closed-bar-xau-m5-rsi-wick-adx-roll-exhaustion-rejection-fade",
        "overrides": (
            "Window=2018.01.01-2026.07.22;XAUUSD;M5;Model0;InpSignalMode=5;"
            "InpHypothesisId=HYP-MZMS-XAU-M5-010;InpMagic=5600730;RiskPercent=0.01;"
            "Deposit=100000;Leverage=100;RequireNewsGuard=false;MaxSpreadXauPoints=35;"
            "StopLookback=5;StopAtr=1.5;StopBufferXauPoints=40;TargetRR=1.6;MaxHoldBars=15;"
            "CooldownBars=5;BreakEven=false;Intrabar=false;SessionUtc=08-17;FlattenUtc=18:15;"
            "Mechanism=RSIWickADXRollExhaustionRejectionFade"
        ),
        "trades": 2,
        "pf": 0.8758314856,
        "net": -1.12,
        "wr": 50.0,
        "exp": -0.56,
        "dd": 0.0,
        "cadence": 0.0045,
        "executed": 2,
        "near_miss": 98,
        "reason": (
            "Park invalid: Model-0 run 20260722_024229 delivered history quality 98% < frozen 99%. "
            "Diagnostic-only metrics N=2 PF=0.8758314856 net=-1.12 WR=50% expectancy=-0.56 "
            "cadence~0.0045/elapsed-week (severe under-cadence; economics non-inferential). Exact lifecycle "
            "reconciliation. 2 executed + 98 offline near-miss charts + Grok synthesis. No promotion/economic "
            "authority; no post-hoc rescue/rerun."
        ),
    },
}


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    existing = REG.read_text(encoding="utf-8")
    to_write: list[str] = []
    for hyp, meta in ROWS.items():
        packet = f"{EVID}/{hyp}_DELIVERY_PACKET.json"
        row = {
            "record_type": "hypothesis_state",
            "schema_version": "alphafactory_candidate_registry.v1",
            "hypothesis_id": hyp,
            "ea_name": "EA_MZMS_Scalper",
            "state": "parked",
            "parent_candidate": (
                "Owner-authorized fresh four-mechanism XAU campaign after terminal/invalid "
                "HYP-006 forensics; not a threshold rescue"
            ),
            "feature_family": meta["family"],
            "lane": "XAUUSD-M5-MZMS-four-mechanism-campaign",
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "window": {"from": "2018.01.01", "to": "2026.07.22"},
            "model": 0,
            "source_provenance": (
                "Shared multi-mode source SHA 96A4E8D0... completed one standalone FivePercent "
                "XAUUSD M5 Model-0 run per frozen ID; history quality 98% failed the frozen 99% gate "
                "so the run is invalid engineering evidence. Delivery packet closes the campaign with "
                "PARKED verdict, 400-chart Grok forensics synthesis, and no promotion authority."
            ),
            "source_path": SOURCE,
            "source_hash": "96A4E8D0CADB0A8B229C124CEB9C70146266A583EEC3D98BB5C406617C80692A",
            "prereg_path": PREREG,
            "prereg_sha256": "ADF33F53F9976FCD12DFA2C78D42F9EBB5D9F09CE1EC5937F00332C4043748F9",
            "exact_overrides": meta["overrides"],
            "acceptance_contract": {
                "min_profit_factor": 1.35,
                "min_trades_per_week": 2,
                "max_trades_per_week": 5,
                "max_drawdown_pct": 6,
                "min_cost_pf_x1_5": 1.25,
                "min_cost_pf_x2": 1,
                "max_monte_carlo_p95_dd_pct": 6,
            },
            "verdict": "PARK_INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99",
            "reason": meta["reason"],
            "updated_at_utc": now,
            "run_ids": [meta["run_id"]],
            "metrics": {
                "valid_model0_runs": 0,
                "invalid_model0_runs": 1,
                "history_quality_pct": 98,
                "frozen_min_history_quality_pct": 99,
                "trades": meta["trades"],
                "profit_factor": meta["pf"],
                "net_profit_usd": meta["net"],
                "win_rate_pct": meta["wr"],
                "expectancy_usd_per_trade": meta["exp"],
                "max_drawdown_pct": meta["dd"],
                "trades_per_elapsed_calendar_week": meta["cadence"],
                "economic_metrics_authoritative": False,
                "forensics_executed_samples": meta["executed"],
                "forensics_near_miss_samples": meta["near_miss"],
                "delivery_packet_path": packet,
                "delivery_packet_sha256": sha(ROOT / packet),
                "readout_path": READOUT,
                "readout_sha256": sha(ROOT / READOUT),
                "grok_synthesis_path": f"{EVID}/GROK_SYNTHESIS_RESULT.json",
                "grok_synthesis_sha256": sha(ROOT / EVID / "GROK_SYNTHESIS_RESULT.json"),
            },
            "validation": {
                "dedup_status": "NEW_MECHANISM_OWNER_AUTHORIZED_NOT_THRESHOLD_RESCUE",
                "probe_status": "INVALID_HISTORY_QUALITY_BELOW_FROZEN_GATE",
                "source_build_authorized": False,
                "offline_probe_authorized": False,
                "model0_authorized": False,
                "performance_metrics_authorized": False,
                "promotion_eligible": False,
                "economic_metrics_authoritative": False,
                "cost_status": "UNVERIFIED_DIAGNOSTIC_ONLY",
                "epistemic_class": "INVALID_ENGINEERING_RUN_NO_ECONOMIC_VERDICT",
                "nonrepaint_audit_path": NR,
                "nonrepaint_audit_sha256": "395C8E67D995C5432F579EE32AC524276494FBB9E08A1F7861B1138448E17C3F",
                "bound_run_path": f"02. AlphaFactory/runs/EA_MZMS_Scalper/{meta['run_id']}",
                "post_hoc_rescue_blocked": True,
            },
        }
        already = False
        for el in existing.splitlines()[-30:]:
            if not el.strip():
                continue
            ed = json.loads(el)
            if (
                ed.get("hypothesis_id") == hyp
                and ed.get("state") == "parked"
                and ed.get("run_ids") == [meta["run_id"]]
                and ed.get("verdict") == row["verdict"]
            ):
                already = True
                break
        if already:
            print(f"skip existing {hyp}")
            continue
        to_write.append(json.dumps(row, ensure_ascii=False, separators=(",", ":")))

    if to_write:
        with REG.open("a", encoding="utf-8") as handle:
            for line in to_write:
                handle.write(line + "\n")
        print(f"appended {len(to_write)}")
        for line in to_write:
            d = json.loads(line)
            print(d["hypothesis_id"], d["run_ids"], d["metrics"]["invalid_model0_runs"])
    else:
        print("nothing appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
