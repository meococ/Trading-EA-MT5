"""arrival_freeze2 — R02 freeze writer (R02-K, CONDITIONAL on B1+B2).

Phase A (blind): rebuilds every (symbol, generator) bundle — events,
t-1 arm tags, zone attributes, E1/resid/E3 bounds + arm sizes, balance
gate results, E2 pair tags — pickles them to `_scratch/frozen_bundles/`
for the post-freeze outcome runner, and emits the measured tables.

Phase B (freeze): writes `rounds/R02/FREEZE_v2.json` — ledger anchor,
prereg SHA256, code bundle hashes, frozen-bundle hashes, arm/event
tables, every declared threshold — BEFORE any outcome column exists
anywhere on disk.  WRITE-ONCE: the target must not already exist —
a freeze is a seal, not a draft (R02-L item 2).

    python -B arrival_freeze2.py EURUSD GBPUSD AUDUSD USDJPY

OUTCOME-BLIND: imports arrival_outcome nowhere; resolves nothing.
"""

import hashlib
import itertools
import json
import os
import pickle
import sys
from datetime import datetime, timezone

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, os.path.join(_PROOT, "lib"),
           os.path.join(_PROOT, "research", "physics")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_slots                                # noqa: E402
import pa_ledger                               # noqa: E402
import arrival_common as ac                    # noqa: E402
import arrival_contrast as cc                  # noqa: E402
import arrival_estimate as ae                  # noqa: E402

W_SCALE = 0.75
GENS = ("line1_cluster", "fractal_h1", "kde_swing",
        "profile_va", "sd_base", "ref_levels")
SYMS = ("EURUSD", "GBPUSD", "AUDUSD", "USDJPY")

CODE_FILES = [
    "research/arrival/arrival_common.py",
    "research/arrival/arrival_contrast.py",
    "research/arrival/arrival_estimate.py",
    "research/arrival/arrival_feas2.py",
    "research/arrival/arrival_outcome.py",
    "research/arrival/arrival_outcome_run.py",
    "research/arrival/arrival_freeze2.py",
    "research/arrival/tests/test_arrival.py",
    "research/physics/phys_resolve.py",
    "research/physics/phys_common.py",
]

THRESHOLDS = {
    "w_scale": W_SCALE, "margin": 0.5,
    "trim_lo": cc.TRIM_LO, "trim_hi": cc.TRIM_HI,
    "winsor_q": cc.WINSOR_Q, "smd_gate": cc.SMD_GATE,
    "recency_gate": cc.RECENCY_GATE, "since_cap": cc.SINCE_CAP,
    "boot_B": ae.BOOT_B, "boot_seed": ae.BOOT_SEED,
    "claim_d_pp": 5.0, "tie_margin_pp": 2.0, "bh_q": 0.10,
    "attenuation_r2": 0.90, "cap_s_gate": 0.50,
    "min_kept_arm": 50, "min_contrib_cells": 3,
    "resolved_floor_per_arm": 1000,
    "design_years_req": "4/6 within contributing cells",
    "features": list(cc.FEATURES),
    "e3_features": list(cc.E3_FEATURES),
    "recency_features": list(cc.RECENCY_FEATURES),
    "p_recipe": "p = (1 + #{D_b <= 0}) / (B + 1), one-sided",
    "family_unit": "generator (pair for E2) x endpoint",
    "horizon_m5": 48,
}


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _grids_events(bars, ctx, segs, u_atr):
    o = np.asarray(bars["o"], dtype=np.float64)
    grids = []
    for di, (d0, _d1) in enumerate(segs):
        A = ctx.a(d0)
        bands, w_p = ac.build_day_grid(float(o[d0]), A, u_atr, W_SCALE)
        grids.append((bands, w_p, di, float(o[d0]), A) if bands
                     else None)
    return ac.arrival_events(bars, ctx, grids)


def build_symbol(symbol):
    """Blind bundle for one symbol.  No outcome field anywhere."""
    from data_helpers import load_ctx
    import registry
    from phys_source import GenSource

    ctx = load_ctx(symbol, max_bars=None)
    bars = ctx.bars
    segs = ac.day_segments(bars)
    bnd = {"symbol": symbol, "gens": {}, "pairs": {}}
    srcs, us, evs, arms = {}, {}, {}, {}
    for g in GENS:
        srcs[g] = GenSource(g, registry.get(g), ctx).run()
        us[g] = ac.armed_width_atr(srcs[g], step=288)[0]
        evs[g], _cnt = _grids_events(bars, ctx, segs, us[g])
        a, _d = ac.tag_arms(evs[g], srcs[g], margins=(0.5,), bars=bars)
        arms[g] = a[0.5]
        cc.attach_touches(evs[g], srcs[g])

    for g in GENS:
        ev, tr = evs[g], arms[g]["treated"]
        cell = {"u_atr": us[g], "n_events": len(ev),
                "n_treated": len(tr)}
        cell["e1_bounds"] = ae.tercile_bounds(ev, tr)
        e1 = cc.e1_arms(ev, tr, cell["e1_bounds"])
        rep = cc.balance_report(ev, e1["top"], e1["bot"])
        rec = (cc.recency_report(ev, e1["top"], e1["bot"], rep)
               if not rep.get("skipped") else {"skipped": True})
        cell["e1"] = {"n_top": len(e1["top"]), "n_mid": len(e1["mid"]),
                      "n_bot": len(e1["bot"]),
                      "gate_pass": rep.get("gate_pass"),
                      "smd_post": rep.get("smd_post"),
                      "recency": rec}
        resid, rdiag = cc.resid_strength(ev, tr, return_diag=True)
        rb = (tuple(float(x) for x in
                    np.quantile(list(resid.values()),
                                [1.0 / 3.0, 2.0 / 3.0]))
              if resid else None)
        ra = cc.resid_arms(resid, tr, rb) if rb else None
        rep_r = (cc.balance_report(ev, ra["top"], ra["bot"])
                 if ra else {"skipped": True})
        rec_r = (cc.recency_report(ev, ra["top"], ra["bot"], rep_r)
                 if ra and not rep_r.get("skipped")
                 else {"skipped": True})
        cell["resid"] = {"bounds": rb, "r2": rdiag["r2"],
                         "resid_var_share": rdiag["resid_var_share"],
                         "n_top": len(ra["top"]) if ra else 0,
                         "n_bot": len(ra["bot"]) if ra else 0,
                         "gate_pass": rep_r.get("gate_pass"),
                         "smd_post": rep_r.get("smd_post"),
                         "recency": rec_r}
        zst = np.asarray([ev[i]["zone_since_touch"] for i in tr
                          if ev[i].get("zone_since_touch") is not None],
                         dtype=np.float64)
        e3b = (tuple(float(x) for x in
                     np.quantile(zst, [1.0 / 3.0, 2.0 / 3.0]))
               if zst.size else None)
        e3 = (cc.e3_arms(ev, tr, e3b) if e3b else
              {"recent": [], "mid": [], "stale": [],
               "degenerate": True})
        rep3 = (cc.balance_report(ev, e3["recent"], e3["stale"],
                                  feats=cc.E3_FEATURES)
                if not e3["degenerate"] else
                {"skipped": True})
        cap_s = (float(np.mean([ev[i]["zone_since_touch"]
                                >= cc.SINCE_CAP for i in e3["stale"]]))
                 if e3["stale"] else float("nan"))
        cell["e3"] = {"bounds": e3b, "n_recent": len(e3["recent"]),
                      "n_mid": len(e3["mid"]),
                      "n_stale": len(e3["stale"]),
                      "degenerate": e3["degenerate"],
                      "cap_share_stale": cap_s,
                      "gate_pass": rep3.get("gate_pass"),
                      "smd_post": rep3.get("smd_post")}
        bnd["gens"][g] = {"events": ev, "treated": tr,
                          "table": cell}
        print(f"  {symbol} {g} done", flush=True)

    all_tp = sorted({int(e["bar_idx"]) - 1
                     for g in GENS for e in evs[g]})
    tabs = {g: cc.live_overlap_tables(srcs[g], all_tp) for g in GENS}
    for g, h in itertools.combinations(GENS, 2):
        base = g if us[g] <= us[h] else h
        other = h if base == g else g
        ev = evs[base]
        tg = cc.tag_pair(ev, srcs[base], srcs[other], bars=bars,
                         live_tab_g=tabs[base], live_tab_h=tabs[other])
        ia, ib = (tg["g"], tg["h"]) if base == g \
            else (tg["h"], tg["g"])
        rep = cc.balance_report(ev, ia, ib)
        bnd["pairs"][f"{g}|{h}"] = {
            "grid": base, "n_a": len(ia), "n_b": len(ib),
            "n_x": len(tg["x"]), "gate_pass": rep.get("gate_pass"),
            "smd_post": rep.get("smd_post")}
        bnd["gens"][base].setdefault("pair_arms", {})[f"{g}|{h}"] = \
            {"ia": ia, "ib": ib}
        print(f"  {symbol} {g}|{h} done", flush=True)
    return bnd


FREEZE_NAME = "FREEZE_v2.json"


def main():
    fp = os.path.join(_PROOT, "rounds", "R02", FREEZE_NAME)
    if os.path.exists(fp):
        raise SystemExit(
            f"WRITE-ONCE: {fp} already exists — a freeze is a seal, "
            "not a draft (R02-L item 2). Aborting without touching it.")
    slot = pa_slots.acquire("r02-freeze")
    try:
        out_dir = os.path.join(_HERE, "_scratch", "frozen_bundles")
        os.makedirs(out_dir, exist_ok=True)
        tables = {}
        bundle_sha = {}
        for sym in SYMS:
            print(f"building {sym}", flush=True)
            bnd = build_symbol(sym)
            bp = os.path.join(out_dir, f"{sym}.pkl")
            with open(bp, "wb") as f:
                pickle.dump(bnd, f, protocol=4)
            bundle_sha[f"_scratch/frozen_bundles/{sym}.pkl"] = \
                _sha256(bp)
            tables[sym] = {g: bnd["gens"][g]["table"] for g in GENS}
            tables[sym]["_pairs"] = bnd["pairs"]

        code_sha = {p: _sha256(os.path.join(_PROOT, p))
                    for p in CODE_FILES}
        anchor = pa_ledger.anchor()
        pa_ledger.append_anchor(note="R02 freeze v2 (R02-L)")
        freeze = {
            "round": "R02", "phase": "arrival-contrasts",
            "utc": datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "supersedes": ("FREEZE.json (v1, VOID — see "
                           "DEVIATION_D40_POSTFREEZE_CODE_EDIT.md)"),
            "split": "DESIGN", "symbols": list(SYMS), "tf": "M5",
            "seed": ae.BOOT_SEED,
            "ledger_anchor": anchor,
            "prereg_sha256": _sha256(
                os.path.join(_PROOT, "rounds", "R02", "PREREG.md")),
            "code_sha256": code_sha,
            "bundle_sha256": bundle_sha,
            "thresholds": THRESHOLDS,
            "tables": tables,
            "claim_paths": {
                "E3": ["line1_cluster x {bounce, continuation}"],
                "E1": "descriptive only (D41a — no generator eligible)",
                "E2": "flagging only"},
        }
        with open(fp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(freeze, f, indent=2, sort_keys=True,
                      default=float)
        print("FROZEN " + fp, flush=True)
    finally:
        pa_slots.release(slot)


if __name__ == "__main__":
    main()
