#!/usr/bin/env python3
"""Post WTI/WALCL — signed flow + true forwards offline probes on RR2 shelf.

A priori frozen (do not mine):
  O1 HYP-RR2-NYFED-PD-GS-NETFLOW-GATE-001
  O2 HYP-RR2-MMF-RETAIL-INFLOW-GATE-001
  O3 HYP-RR2-JPY-CME6J-FWDBASIS-ZGATE-001

Joint screen: N, PF, tpw, +$12 x1.5 vs RR2 baseline. Model 0 only if PROBE_SURVIVOR.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
EXO = PRE / "v8_exogenous"
PD_PANEL = EXO / "panels" / "nyfed_pd_ust_net_pos_w1_v1.csv"
MMF_PANEL = EXO / "panels" / "fred_retail_mmf_wow_w1_v1.csv"
FWD_PANEL = EXO / "panels" / "jpy_cme6j_spot_fwd_basis_d1_v1.csv"
RR2_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SilverBullet" / "20260714_194548"

OUT_JSON = PRE / "20260714_FORWARDS_SIGNEDFLOW_OFFLINE_PROBES.json"
OUT_MD = READ / "20260714_FORWARDS_SIGNEDFLOW_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260714_FORWARDS_SIGNEDFLOW_DEDUP_CLEARANCE.md"
OUT_CLOSE = READ / "20260714_FORWARDS_SIGNEDFLOW_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260714_FORWARDS_SIGNEDFLOW_VN_ACTION_BRIEF.md"
OUT_ACQ = READ / "20260714_FORWARDS_SIGNEDFLOW_ACQUISITION_READOUT.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
COST12 = 12.0

# A priori — do not mine
FWD_Z_ABS = 0.75
FWD_LOOKBACK = 60
FWD_MIN_OBS = 40


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = COST12) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    tpw = n / ELAPSED_WEEKS if ELAPSED_WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(m: dict, hc: dict, baseline_x15: float | None = None) -> tuple[str, list[str]]:
    notes = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.0 <= tpw <= 6.5):
        notes.append("cadence_fail")
    if pf < 1.05:
        notes.append("pf_fail")
    if x15 < 1.10:
        notes.append("stress_fail")
    if baseline_x15 is not None and x15 <= baseline_x15 + 1e-9:
        notes.append("no_stress_lift_vs_baseline")
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
        and (baseline_x15 is None or x15 > baseline_x15 + 0.01)
    ):
        return "PROBE_SURVIVOR", notes
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    return "KILLED_AT_OFFLINE_PROBE", ["joint_screen_miss"]


def find_trades_csv(run_dir: Path) -> Path:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    if not hits:
        raise FileNotFoundError(f"no trades csv under {run_dir}")
    return sorted(hits)[0]


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def load_rr2_closed() -> list[dict]:
    path = find_trades_csv(RR2_DIR)
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in (
                "1",
                "true",
                "True",
            ):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                ot = parse_dt(op.get("event_time") or "")
                ct = parse_dt(row.get("event_time") or "")
                if ot is None or not (FROM <= ot <= TO):
                    continue
                closed.append({"open_time": ot, "close_time": ct, "pnl": pnl})
    return closed


def daily_bool_lookup(events: list[tuple[date, bool]]) -> dict[date, bool]:
    events = sorted(events, key=lambda x: x[0])
    out: dict[date, bool] = {}
    last = None
    idx = 0
    day = FROM.date()
    end = TO.date()
    while day <= end:
        while idx < len(events) and events[idx][0] <= day:
            last = events[idx][1]
            idx += 1
        if last is not None:
            out[day] = last
        day += timedelta(days=1)
    return out


def daily_float_lookup(events: list[tuple[date, float]]) -> dict[date, float]:
    events = sorted(events, key=lambda x: x[0])
    out: dict[date, float] = {}
    last = None
    idx = 0
    day = FROM.date()
    end = TO.date()
    while day <= end:
        while idx < len(events) and events[idx][0] <= day:
            last = events[idx][1]
            idx += 1
        if last is not None:
            out[day] = last
        day += timedelta(days=1)
    return out


def build_pd_allow() -> dict[date, bool]:
    """Allow when latest available WoW delta of PD GS net > 0 (inventory rising)."""
    events: list[tuple[date, bool]] = []
    with PD_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            wow = (row.get("wow_delta_mn") or "").strip()
            if not wow:
                continue
            avail = date.fromisoformat(row["available_at_utc"][:10])
            events.append((avail, float(wow) > 0.0))
    return daily_bool_lookup(events)


def build_mmf_allow() -> dict[date, bool]:
    """Allow when latest available retail MMF WoW pct > 0 (inflow / USD cash bid)."""
    events: list[tuple[date, bool]] = []
    with MMF_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            wow = (row.get("wow_pct") or "").strip()
            if not wow:
                continue
            avail = date.fromisoformat(row["available_at_utc"][:10])
            events.append((avail, float(wow) > 0.0))
    return daily_bool_lookup(events)


def build_fwd_z() -> dict[date, float]:
    rows = []
    with FWD_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            avail = date.fromisoformat(row["available_at_utc"][:10])
            val = float(row["fwd_basis"])
            rows.append((avail, val))
    rows.sort(key=lambda x: x[0])
    z_events: list[tuple[date, float]] = []
    hist: list[float] = []
    for avail, val in rows:
        hist.append(val)
        if len(hist) < FWD_MIN_OBS:
            continue
        window = hist[-FWD_LOOKBACK:]
        mu = sum(window) / len(window)
        var = sum((x - mu) ** 2 for x in window) / max(1, len(window) - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        z = (val - mu) / sd if sd > 1e-12 else 0.0
        z_events.append((avail, z))
    return daily_float_lookup(z_events)


def gate_probe(
    hyp_id: str,
    cls: str,
    trades: list[dict],
    allow: dict[date, bool],
    rule: str,
    lag: str,
    missing_key: str,
) -> dict[str, Any]:
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    base_x15 = (base_hc.get("x1_5") or {}).get("pf")
    kept = []
    skipped = 0
    no_data = 0
    for t in trades:
        d = t["open_time"].date()
        a = allow.get(d)
        if a is None:
            no_data += 1
            skipped += 1
            continue
        if a:
            kept.append(t["pnl"])
        else:
            skipped += 1
    m = metrics(kept)
    hc = haircuts(kept)
    verdict, notes = joint_verdict(m, hc, baseline_x15=base_x15)
    return {
        "hypothesis_id": hyp_id,
        "class": cls,
        "sleeve": "RR2_194548",
        "funnel": {
            "n_baseline": len(trades),
            "n_kept": len(kept),
            "n_skipped": skipped,
            missing_key: no_data,
            "keep_frac": round(len(kept) / len(trades), 4) if trades else 0.0,
        },
        "baseline": {"metrics": base_m, "haircuts": base_hc},
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "a_priori": {"rule": rule, "lag": lag, "fail_closed_missing": True},
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "stress_lift_vs_baseline_x15": None
        if base_x15 is None
        else round(((hc.get("x1_5") or {}).get("pf") or 0.0) - base_x15, 4),
    }


def fwd_z_gate(trades: list[dict], zmap: dict[date, float]) -> dict[str, Any]:
    """Allow RR2 when |fwd_basis z| >= FWD_Z_ABS (forward premium/discount extreme)."""
    allow = {d: abs(z) >= FWD_Z_ABS for d, z in zmap.items()}
    return gate_probe(
        "HYP-RR2-JPY-CME6J-FWDBASIS-ZGATE-001",
        "true_fx_forward_basis_z_allow_gate",
        trades,
        allow,
        f"allow_only_when_|fwd_basis_z| >= {FWD_Z_ABS} (lookback={FWD_LOOKBACK})",
        "settle+1d",
        "n_no_fwd",
    )


def write_docs(payload: dict) -> None:
    objs = payload["objects"]
    lines = [
        "# Forwards / signed-flow offline probes — 2026-07-14",
        "",
        f"Status: `{payload['campaign_status']}`",
        f"Receipt SHA256: `{payload['receipt_sha256']}`",
        "",
        "## Objects",
        "",
        "| ID | N | PF | tpw | x1.5 | lift | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for o in objs:
        m = o["metrics"]
        hc = o["haircuts"]
        lines.append(
            f"| `{o['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{(hc.get('x1_5') or {}).get('pf')} | {o.get('stress_lift_vs_baseline_x15')} | "
            f"**{o['verdict']}** |"
        )
    lines += [
        "",
        "## Model 0",
        "",
        "Withheld" if payload["campaign_status"] != "PROBE_SURVIVOR_PRESENT" else "Authorized for survivor only",
        "",
        "## Acquire blockers (attempted)",
        "",
    ]
    for b in payload.get("acquire_blockers", []):
        lines.append(f"- **{b['surface']}**: {b['blocker']}")
    lines += ["", "## Panels", ""]
    for k, v in payload.get("panel_sha256", {}).items():
        lines.append(f"- `{k}` `{v}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup clearance — forwards / signed-flow gates",
                "",
                "Status: `INTAKE_CLEARED / INDEPENDENT` (a priori)",
                "",
                "| Object | Vs killed shelf |",
                "|---|---|",
                "| O1 NY Fed PD GS net-flow gate | Not COT |z|/size; cash dealer inventory, not futures TFF |",
                "| O2 Retail MMF inflow gate | Not WALCL Fed-balance-sheet twin; private MMF AUM flow |",
                "| O3 CME 6J−spot forward-basis z-gate | Not OIS SOFR−€STR / bond-diff / VIX; true futures−spot basis |",
                "",
                "Banned densify remains: Wave1–9 / dichotomy / COT size+|z| / WTI z / WALCL sign /",
                "USDCAD displace / SOFR−SONIA twin / HY−OAS−MOVE−DTWEX VIX siblings.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    kill_n = sum(1 for o in objs if o["verdict"] != "PROBE_SURVIVOR")
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — forwards / signed-flow acquire + probe",
                "",
                "Date: 2026-07-14",
                f"Status: `{payload['campaign_status']}`",
                "Lane: single checkout; no-Git",
                "",
                "## Executed",
                "",
                "1. Attempted legal acquire of FX forwards (Stooq/Yahoo v7 fail; Yahoo chart v8 OK),",
                "   signed flow (NY Fed PD + FRED WRMFSL OK), OIS/basis proxy (CP90 raw OK; not auto-probed as VIX sibling).",
                "2. SHA-froze panels + lag contracts.",
                "3. De-dup cleared three new objects.",
                "4. Offline joint probe on RR2 `194548`.",
                "",
                "| ID | Verdict |",
                "|---|---|",
                *[f"| `{o['hypothesis_id']}` | **{o['verdict']}** |" for o in objs],
                "",
                f"Receipt: `{payload['receipt_sha256']}`",
                f"Artifacts: `preflight/{OUT_JSON.name}`",
                "",
                "## Model 0",
                "",
                "Withheld (no PROBE_SURVIVOR)."
                if kill_n == len(objs)
                else "See survivor object only.",
                "",
                "## Next autonomous EV",
                "",
                "1. Do not densify PD WoW sign / MMF wow / 6J basis z.",
                "2. Keep Real QFSI accumulate for multi-year session×symbol cost (still GAP).",
                "3. Next object outside Wave1–9 / dichotomy / COT / WTI / WALCL / PD-MMF-6J killboard.",
                "",
                "Best shelf unchanged: RR2 `20260714_194548`. Phase-0 still BLOCKED. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# Brief VN — Forwards / signed-flow session",
                "",
                f"**Kết quả:** `{payload['campaign_status']}` — không Model 0 nếu không có survivor.",
                "",
                "- Đã acquire + freeze: NY Fed PD GS net, FRED retail MMF, CME 6J−spot basis.",
                "- Stooq/Yahoo download CSV: fail (JS/crumb); Yahoo chart API: OK.",
                "- Ba gate trên RR2 shelf — xem closeout EN.",
                "- Cấm densify PD/MMF/6J; shelf tốt nhất vẫn RR2 `194548`.",
                "- Next: object mới ngoài killboard hoặc đợi QFSI multi-year cost.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_ACQ.write_text(
        "\n".join(
            [
                "# Acquisition readout — forwards / signed-flow",
                "",
                f"Manifest: `v8_exogenous/manifests/20260714_FORWARDS_SIGNEDFLOW_ACQUISITION_V1.json`",
                "",
                "## OK",
                "",
                "- NY Fed Primary Dealer all timeseries CSV (~26MB) → panel `PDPOSGST-TOT`",
                "- FRED `WRMFSL` / `WIMFSL` retail+inst MMF",
                "- FRED `DEXJPUS` + Yahoo chart `6J=F` → forward-basis panel",
                "- BoC Valet FX daily (spot; not true forwards — raw only)",
                "- FRED CP90 AA (basis raw; not probed this pass — VIX-sibling risk)",
                "",
                "## FAIL",
                "",
                "- Stooq `jf.f` / `ef.f`: JS bot challenge",
                "- Yahoo v7 finance/download: empty/crumb",
                "- BoC: no free FX-forward group found in Valet lists",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    assert PD_PANEL.is_file() and MMF_PANEL.is_file() and FWD_PANEL.is_file()
    trades = load_rr2_closed()
    assert len(trades) >= 100, f"RR2 trades too few: {len(trades)}"

    o1 = gate_probe(
        "HYP-RR2-NYFED-PD-GS-NETFLOW-GATE-001",
        "signed_dealer_gs_inventory_flow_allow_gate",
        trades,
        build_pd_allow(),
        "allow_only_when_latest_available_PDPOSGST-TOT_wow_delta_mn > 0",
        "observation+8d",
        "n_no_pd",
    )
    o2 = gate_probe(
        "HYP-RR2-MMF-RETAIL-INFLOW-GATE-001",
        "signed_usd_mmf_inflow_allow_gate",
        trades,
        build_mmf_allow(),
        "allow_only_when_latest_available_WRMFSL_wow_pct > 0",
        "observation+2d",
        "n_no_mmf",
    )
    o3 = fwd_z_gate(trades, build_fwd_z())
    objects = [o1, o2, o3]
    survivors = [o for o in objects if o["verdict"] == "PROBE_SURVIVOR"]
    status = (
        "PROBE_SURVIVOR_PRESENT"
        if survivors
        else "OFFLINE_ALL_KILL / NO_MODEL0"
    )

    payload = {
        "schema": "forwards_signedflow_offline_probes.v1",
        "created_at_utc": utc_now(),
        "campaign_status": status,
        "authority": "post_WTI_WALCL_kill; prefer forwards/signed_flow; Model0 only on survivor",
        "rr2_sleeve": "20260714_194548",
        "n_rr2_trades": len(trades),
        "panel_sha256": {
            PD_PANEL.name: sha256_file(PD_PANEL),
            MMF_PANEL.name: sha256_file(MMF_PANEL),
            FWD_PANEL.name: sha256_file(FWD_PANEL),
        },
        "acquire_blockers": [
            {"surface": "Stooq jf.f/ef.f", "blocker": "JS_bot_challenge"},
            {
                "surface": "Yahoo v7 download 6J=F",
                "blocker": "empty_or_crumb; recovered via chart v8 API",
            },
            {
                "surface": "BoC Valet FX forwards",
                "blocker": "no_public_FX_forward_group; daily spot only",
            },
        ],
        "objects": objects,
        "model0": "WITHHELD" if not survivors else "AUTHORIZED_SURVIVOR_ONLY",
        "banned_densify": [
            "PD_wow_sign_retune",
            "MMF_wow_threshold_mine",
            "6J_basis_z_mine",
            "COT_z_or_size",
            "WTI_WALCL_retune",
            "Wave1_9_price_twin",
        ],
    }
    raw = json.dumps(payload, indent=2) + "\n"
    # placeholder then rehash
    payload["receipt_sha256"] = "PENDING"
    raw = json.dumps(payload, indent=2) + "\n"
    payload["receipt_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    # final with receipt embedded
    final = json.dumps(payload, indent=2) + "\n"
    # recompute receipt over body with receipt field zeroed for stability
    tmp = dict(payload)
    tmp["receipt_sha256"] = ""
    payload["receipt_sha256"] = hashlib.sha256(
        json.dumps(tmp, indent=2, sort_keys=True).encode("utf-8")
    ).hexdigest().upper()
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_docs(payload)
    print(json.dumps({"status": status, "objects": [
        {"id": o["hypothesis_id"], "verdict": o["verdict"], "m": o["metrics"], "x15": (o["haircuts"].get("x1_5") or {}).get("pf"), "lift": o.get("stress_lift_vs_baseline_x15")}
        for o in objects
    ], "receipt": payload["receipt_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
