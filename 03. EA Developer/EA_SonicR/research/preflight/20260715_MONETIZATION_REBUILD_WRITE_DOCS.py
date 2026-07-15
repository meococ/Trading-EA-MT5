#!/usr/bin/env python3
"""Write monetization rebuild docs + patch hot.md after outcome-faithful probes."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

OUT_JSON = PRE / "20260715_MONETIZATION_REBUILD_OFFLINE_PROBES.json"
COST_JSON = PRE / "20260715_COST_TICK_ACQUIRE_V2.json"


def main() -> int:
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    cost = json.loads(COST_JSON.read_text(encoding="utf-8")) if COST_JSON.exists() else {}
    cost_receipt = cost.get("receipt_sha256", "")
    cost_verdict = cost.get("verdict") or {}
    cost_table_sha = cost.get("table_sha256", "")

    payload["trades_csv"] = (
        "02. AlphaFactory/runs/EA_SilverBullet/20260714_194548/logs/"
        "USDJPY_20260325_PX6_Trades_20210101_000000_90095968.csv"
    )
    payload["track_a_companion"] = {
        "receipt": cost_receipt,
        "grade": cost_verdict.get("grade"),
        "freeze_eligible": cost_verdict.get("sha_freeze_eligible_for_research_cost_surface"),
        "gaps": cost_verdict.get("missing_for_research_freeze"),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    receipt = hashlib.sha256(OUT_JSON.read_bytes()).hexdigest().upper()
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    base = payload["baseline"]
    probes = payload["probes"]
    survivors = payload.get("survivors") or []

    rows = []
    for p in probes:
        m = p["metrics"]
        hc = p["haircut_flat12"]
        tag = "SURVIVOR" if p["verdict"] == "PROBE_SURVIVOR" else "KILL"
        rows.append(
            f"| `{p['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"**{hc['x1_5']['pf']}** | **{tag}** |"
        )

    (READ / "20260715_MONETIZATION_REBUILD_DESIGN_MEMO.md").write_text(
        "\n".join(
            [
                "# Design memo — monetization rebuild (post-greenfield)",
                "",
                "Date: 2026-07-15",
                "Lane: single; no-Git; offline-first",
                "Authority: Owner authorized rebuild (“đập đi xây lại”); free Model 0 for survivors",
                "",
                "## Problem",
                "",
                "Public price+exo greenfield exhausted. Fixed-RR scalp RR2 `194548` dies under +$12 x1.5.",
                "Need monetization architectures that change **how** winners are cashed — not denser entries.",
                "",
                "## Rejected a priori (killed / banned)",
                "",
                "- BE@1R / trail-from-BE",
                "- MFE stall-cut hard-close",
                "- Vol-target ATR risk sizing / H4 regime-align gate",
                "- FRED/XS/LNY/Asia densify",
                "- Free +3R upgrade without path proof",
                "",
                "## Methodology",
                "",
                "**Outcome-faithful transforms on tester PnL/risk_usd** (risk_usd ≈ |pnl| on losers).",
                "",
                "OHLC M15 path rebuild for scale-out/ATR/volregime is **VOIDED** as decision evidence:",
                "false SL inflation (~444 vs ~300 real losers) — same bias class as MFE stall path board.",
                "ATR-trail remains a design candidate only after tick-path or Model 0 native path.",
                "",
                "## Design 1 — Scale-out (`HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001`)",
                "",
                "Take 50% at +1.0R; remainder to +2.0R → TP winners monetize at **1.5R**.",
                "",
                "## Design 2 — Time-box scalp lock (`HYP-RR2-EXIT-TIMEBOX-SCALPLOCK-2H-001`)",
                "",
                "If hold ≤2h: keep. If hold >2h and realized R≥1: lock **1.0R** at box",
                "(conservative hybrid; optimistic extend-to-3R forbidden without path).",
                "",
                "## Design 3 — Vol-regime R multiple (`HYP-RR2-VOLREGIME-RMULT-H1ATR-001`)",
                "",
                "H1 ATR%ile → TP 1.5 / 2.0 / 3.0R. On original ~2R TP hits: earlier 1.5R applied;",
                "3R **not** credited without path proof (keep 2R).",
                "",
                "## Model 0 policy",
                "",
                "Only `PROBE_SURVIVOR`. Else withhold.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (READ / "20260715_MONETIZATION_REBUILD_DEDUP_CLEARANCE.md").write_text(
        "\n".join(
            [
                "# De-dup clearance — monetization rebuild",
                "",
                "Date: 2026-07-15",
                "Authority: Owner rebuild authorized; EXO_FRED_DISPLACE_SPAM_PAUSED",
                "",
                "## Objects",
                "",
                "| ID | Class | Independence claim |",
                "|---|---|---|",
                "| `HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001` | Partial scale-out | ≠ BE@1R; ≠ MFE stall; ≠ vol-target; ≠ H4 gate |",
                "| `HYP-RR2-EXIT-TIMEBOX-SCALPLOCK-2H-001` | Time-box scalp lock hybrid | ≠ ATR OHLC; ≠ MFE stall timer; ≠ BE clamp |",
                "| `HYP-RR2-VOLREGIME-RMULT-H1ATR-001` | Vol-regime TP multiple | ≠ H4 EMA gate; ≠ entry densify; ≠ sizing vol-target |",
                "",
                "## Banned collisions",
                "",
                "- BE@1R / MFE stall-cut / vol-target / H4-regime",
                "- FRED / XS / LNY / Asia densify",
                "- Using voided OHLC false-SL path as kill authority for scale-out/ATR",
                "",
                "## Survivor bar",
                "",
                "N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 ∧ stress lift vs RR2 baseline x1.5.",
                "",
                "## Clearance",
                "",
                "**CLEARED** for offline probe only (outcome-faithful scoring).",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    status = "OFFLINE_ALL_KILL" if not survivors else "PROBE_SURVIVOR_PRESENT"
    (READ / "20260715_MONETIZATION_REBUILD_SESSION_CLOSEOUT.md").write_text(
        "\n".join(
            [
                "# Session closeout — monetization rebuild + cost/tick V2",
                "",
                "Date: 2026-07-15",
                f"Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `NO_MODEL0`",
                "Lane: single checkout; no-Git; offline-first",
                "",
                "## Track A — cost/tick acquire V2",
                "",
                f"- Grade: `{cost_verdict.get('grade')}`",
                f"- Research freeze eligible: **{cost_verdict.get('sha_freeze_eligible_for_research_cost_surface')}**",
                f"- Union quote days: **{cost_verdict.get('n_union_quote_calendar_days')}** / 90 → "
                f"`{cost_verdict.get('union_quote_calendar_days')}`",
                f"- Sessions covered: `{cost_verdict.get('sessions_covered_union')}`",
                f"- Gaps: `{cost_verdict.get('missing_for_research_freeze')}`",
                f"- Receipt: `{cost_receipt}`",
                f"- Table SHA: `{cost_table_sha}`",
                "- Proof: `20260715_COST_TICK_ACQUIRE_V2_COVERAGE_PROOF.md`",
                "",
                "## Track B — monetization probes (outcome-faithful)",
                "",
                "| ID | N | PF | tpw | stress x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *rows,
                "",
                f"Receipt: `{receipt}`",
                f"Baseline RR2 x1.5: **{base['haircut_flat12']['x1_5']['pf']}**",
                "Design: `20260715_MONETIZATION_REBUILD_DESIGN_MEMO.md`",
                "De-dup: `20260715_MONETIZATION_REBUILD_DEDUP_CLEARANCE.md`",
                "Probes: `20260715_MONETIZATION_REBUILD_OFFLINE_PROBES.json`",
                "",
                "## Model 0",
                "",
                "Withheld (zero PROBE_SURVIVOR).",
                "",
                "## Decisions",
                "",
                "1. Keep `EXO_FRED_DISPLACE_SPAM_PAUSED`.",
                "2. Do **not** densify scale frac / timebox hours / R-mult bands from this readout.",
                "3. Do **not** revive BE@1R / MFE stall / vol-target / H4-regime / FRED / XS.",
                "4. Do **not** SHA-freeze research cost surface; GAP remains NARROWED_NOT_CLEARED.",
                "5. ATR-trail OHLC path parked (method voided); needs tick-path before joint score.",
                "6. Best shelf unchanged: RR2 `194548`. GOAL unmet.",
                "",
                "## Next autonomous EV",
                "",
                "1. Keep Real QFSI accumulate toward ≥90 quote days + commission/slip samples.",
                "2. Next monetization class outside scale-out / timebox-scalp-lock / vol-regime-R",
                "   (or tick-path ATR trail) — rebuild still authorized.",
                "3. Do not idle on FRED/XS/LNY densify.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    vn = [
        "# Brief hành động (VN) — Monetization rebuild + cost/tick V2",
        "",
        f"- Track A: freeze **KHÔNG** — grade `{cost_verdict.get('grade')}`; "
        f"union days **{cost_verdict.get('n_union_quote_calendar_days')}/90**; "
        f"sessions Asia→NY trên 11 symbol nhưng history broker chỉ ~2 ngày. "
        f"GAP: `{cost_verdict.get('missing_for_research_freeze')}`.",
        "- Track B: 3 kiến trúc monetization (outcome-faithful) trên RR2 `194548` — "
        "**ALL KILL**; không Model 0.",
    ]
    for p in probes:
        m = p["metrics"]
        x15 = p["haircut_flat12"]["x1_5"]["pf"]
        vn.append(
            f"  - `{p['hypothesis_id']}`: N={m['n']} PF={m['pf']} tpw={m['tpw']} "
            f"x1.5={x15} → **KILL** ({','.join(p['notes'])})"
        )
    vn += [
        f"- Baseline RR2 +$12 x1.5 ≈ **{base['haircut_flat12']['x1_5']['pf']}**. "
        "Scale-out 2R→1.5R và timebox lock 1R làm mỏng edge; vol-regime gần baseline nhưng không lift stress.",
        "- OHLC path rebuild (scale/ATR) **void** — overstate SL; không dùng làm authority.",
        "- Cấm densify; cấm revive BE@1R / MFE stall / FRED / XS. Shelf vẫn RR2 `194548`.",
        f"- Receipts: monetize `{receipt[:16]}…` / cost `{cost_receipt[:16]}…`",
        "- GOAL unmet. Next: QFSI accumulate + monetization class mới (tick-path ATR trail hoặc paradigm khác).",
        "",
    ]
    (READ / "20260715_MONETIZATION_REBUILD_VN_ACTION_BRIEF.md").write_text(
        "\n".join(vn) + "\n", encoding="utf-8"
    )

    md = [
        "# Monetization rebuild — offline probes",
        "",
        f"Receipt: `{receipt}`",
        f"Baseline: N={base['metrics']['n']} PF={base['metrics']['pf']} "
        f"tpw={base['metrics']['tpw']} x1.5={base['haircut_flat12']['x1_5']['pf']}",
        "Method: outcome-faithful (OHLC path voided)",
        "",
        "| ID | N | PF | tpw | x1.5 | lift | Verdict | notes |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for p in probes:
        m = p["metrics"]
        x15 = p["haircut_flat12"]["x1_5"]["pf"]
        md.append(
            f"| `{p['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{x15} | {p['stress_lift_vs_baseline']} | `{p['verdict']}` | "
            f"{','.join(p['notes'])} |"
        )
    md += ["", "Model 0: **WITHHELD**", ""]
    (READ / "20260715_MONETIZATION_REBUILD_OFFLINE_PROBES.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )

    # --- hot.md patch (surgical) ---
    hot = HOT.read_text(encoding="utf-8")
    stamp = "2026-07-15 ~01:55 ICT"
    bullet = (
        f"- **MONETIZATION REBUILD + COST/TICK V2 CLOSEOUT ({stamp}) —\n"
        f"  `EXO_FRED_DISPLACE_SPAM_PAUSED` / `COST_GAP_DIAGNOSTIC_ONLY` / "
        f"`OFFLINE_ALL_KILL` / `NO_MODEL0`.\n"
        f"  Owner-authorized rebuild (“đập đi xây lại”); free Model 0 unused (zero survivor).\n"
        f"  **Track A:** aggressive MT5 day-chunk + anchors on **11** symbols + live deals.\n"
        f"  Union quote days **{cost_verdict.get('n_union_quote_calendar_days')}**/90\n"
        f"  (`{cost_verdict.get('union_quote_calendar_days')}`); sessions Asia→NY covered;\n"
        f"  research freeze **False** grade `{cost_verdict.get('grade')}`.\n"
        f"  Gaps: `{cost_verdict.get('missing_for_research_freeze')}`.\n"
        f"  Receipt `{cost_receipt}`; table `{cost_table_sha}`;\n"
        f"  proof `readouts/20260715_COST_TICK_ACQUIRE_V2_COVERAGE_PROOF.md`.\n"
        f"  **Track B (outcome-faithful; OHLC path voided):**\n"
        f"  1. `HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001` PF **{probes[0]['metrics']['pf']}** "
        f"x1.5 **{probes[0]['haircut_flat12']['x1_5']['pf']}** → **KILL**.\n"
        f"  2. `HYP-RR2-EXIT-TIMEBOX-SCALPLOCK-2H-001` PF **{probes[1]['metrics']['pf']}** "
        f"x1.5 **{probes[1]['haircut_flat12']['x1_5']['pf']}** → **KILL**.\n"
        f"  3. `HYP-RR2-VOLREGIME-RMULT-H1ATR-001` PF **{probes[2]['metrics']['pf']}** "
        f"x1.5 **{probes[2]['haircut_flat12']['x1_5']['pf']}** → **KILL** (nearest; no stress lift).\n"
        f"  Receipt `{receipt}`; VN `readouts/20260715_MONETIZATION_REBUILD_VN_ACTION_BRIEF.md`;\n"
        f"  closeout `readouts/20260715_MONETIZATION_REBUILD_SESSION_CLOSEOUT.md`.\n"
        f"  Do not densify scale/timebox/R-mult; do not invent cost freeze; ATR-trail needs tick-path.\n"
        f"  Best shelf RR2 `194548`. GOAL unmet.\n\n"
    )
    if "## Active Truth\n\n" in hot and "MONETIZATION REBUILD + COST/TICK V2 CLOSEOUT" not in hot:
        hot = hot.replace("## Active Truth\n\n", "## Active Truth\n\n" + bullet, 1)
    hot = re.sub(
        r"^Updated:.*$",
        f"Updated: {stamp} | Monetization rebuild 3/3 KILL; cost V2 GAP; RR2 `194548`; GOAL unmet",
        hot,
        count=1,
        flags=re.M,
    )
    old_active = (
        "- **ACTIVE — Greenfield board closed; research-conclusion lane.**\n"
        "  `EXO_FRED_DISPLACE_SPAM_PAUSED` remains. LNY EUR/GBP + MFE/Asia +\n"
        "  FRED/RR2-exit/COT boards exhausted. Greenfield XS residual / XS mom /\n"
        "  AUDNZD RV **3/3 KILL** offline.\n"
        "  Evidence-backed conclusion: public price+current exo **do not**\n"
        "  jointly clear GOAL under +$12. Highest-EV next (non-login): (1)\n"
        "  acquire multi-month same-broker tick+cost surface to unlock\n"
        "  `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` + research-grade rebind;\n"
        "  **or** (2) Owner-scoped monetization paradigm rebuild beyond\n"
        "  fixed-RR scalp. Keep QFSI 006 accumulate. Do **not** densify\n"
        "  XS/AUDNZD/LNY/Asia/RR2-exit/FRED. Best shelf RR2 `194548`;\n"
        "  `231750` PARK_MISS. GOAL unmet.\n\n"
        "- **CLOSED — Greenfield XS/RV book:**"
    )
    new_active = (
        "- **ACTIVE — Cost acquire + next monetization class (post rebuild board).**\n"
        "  `EXO_FRED_DISPLACE_SPAM_PAUSED`. Scale-out / timebox-scalp-lock / vol-regime-R\n"
        "  **3/3 KILL** (outcome-faithful). Cost freeze still blocked "
        f"(quote_days={cost_verdict.get('n_union_quote_calendar_days')}/90; comm/slip GAP).\n"
        "  Keep QFSI accumulate. Next monetization outside this board (tick-path ATR trail\n"
        "  or new paradigm). Do **not** densify / FRED / XS / LNY. Best shelf RR2 `194548`.\n"
        "  GOAL unmet.\n\n"
        "- **CLOSED — Monetization rebuild + cost/tick V2:** Track A diagnostic-only;\n"
        "  Track B 3/3 KILL. `readouts/20260715_MONETIZATION_REBUILD_SESSION_CLOSEOUT.md`.\n"
        "- **CLOSED — Greenfield XS/RV book:**"
    )
    if old_active in hot:
        hot = hot.replace(old_active, new_active, 1)
    HOT.write_text(hot, encoding="utf-8")
    print(json.dumps({"receipt": receipt, "cost_receipt": cost_receipt, "survivors": survivors}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
