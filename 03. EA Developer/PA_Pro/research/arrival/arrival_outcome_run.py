"""arrival_outcome_run — R02 post-FREEZE outcome runner (R02-K §4,
hardened per R02-L item 3).

RUNS ONLY AFTER rounds/R02/FREEZE_v2.json exists.  Loads the blind
frozen bundles from `_scratch/frozen_bundles/`, resolves outcomes
through the R01 frozen resolver (`arrival_outcome.resolve_arrivals`),
computes the pinned estimates — per-cell weighted ATT + bootstrap CI/p,
and the pooled per-claim-unit bootstrap (D39c) — and appends ONE ledger
trial per claim unit (generator-or-pair x endpoint, D39b).

R02-L hardening:
 (a) each unit's result JSON is written to `_scratch/r02_outcomes/`
     THE MOMENT the unit finishes — no end-of-run single write;
 (b) one timestamped log line per unit start/finish, plus a heartbeat
     at least every 10 min inside long units (bootstrap `progress`
     callback);
 (c) at startup every sha256 in the freeze (code_sha256 AND
     bundle_sha256) is recomputed and any mismatch aborts the run;
 (d) `--units` is an explicit ORDERED unit list — e.g.
     `--units e3:line1_cluster` runs the single claim path first.
     Bare family names expand to all members in canonical order;
 (e) write_reports() stamps RESULTS.md/ROUND_REPORT.md with
     pa_ledger.anchor_md and records the anchor via append_anchor.

    python -B arrival_outcome_run.py \
        --units e3:line1_cluster,e3:fractal_h1,e1resid:all,e1raw:all,e2:all \
        --freeze FREEZE_v2.json

Slot-guarded (pa_slots).  Never touches bars beyond DESIGN events in
the frozen bundles.
"""

import argparse
import hashlib
import itertools
import json
import os
import pickle
import sys
import time
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
import arrival_outcome as ao                   # noqa: E402
import phys_resolve as pr                      # noqa: E402

GENS = ("line1_cluster", "fractal_h1", "kde_swing",
        "profile_va", "sd_base", "ref_levels")
SYMS = ("EURUSD", "GBPUSD", "AUDUSD", "USDJPY")
BUNDLE_DIR = os.path.join(_HERE, "_scratch", "frozen_bundles")
OUT_DIR = os.path.join(_HERE, "_scratch", "r02_outcomes")
ENDPOINTS = ("bounce", "continuation")
EP_KEY = {"bounce": "bounce", "continuation": "cont"}
PAIRS = [f"{g}|{h}" for g, h in itertools.combinations(GENS, 2)]
UNIT_DEFAULT = ",".join(
    ["e3:" + g for g in GENS] +
    ["e1resid:" + g for g in GENS] +
    ["e1raw:" + g for g in GENS] +
    ["e2:" + p for p in PAIRS])

B = ae.BOOT_B
SEED = ae.BOOT_SEED


def _ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg):
    print(f"[{_ts()}] {msg}", flush=True)


class _Heartbeat:
    """Prints a heartbeat line at most every 600 s (R02-L item 3b)."""

    def __init__(self, label):
        self.label = label
        self.t0 = time.time()

    def __call__(self, i):
        dt = time.time() - self.t0
        if not hasattr(self, "_last"):
            self._last = self.t0
        if time.time() - self._last >= 600:
            _log(f"heartbeat {self.label}: replicate {i}, "
                 f"{dt / 60.0:.1f} min elapsed")
            self._last = time.time()


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _verify_freeze(freeze):
    """R02-L item 3c: recompute every sha256 sealed in the freeze and
    abort on ANY mismatch — code files AND the four data bundles."""
    bad = []
    for group in ("code_sha256", "bundle_sha256"):
        for rel, want in freeze.get(group, {}).items():
            fp = os.path.join(_HERE, rel) \
                if rel.startswith("_scratch/") else \
                os.path.join(_PROOT, rel)
            got = _sha256(fp) if os.path.exists(fp) else "MISSING"
            if got != want:
                bad.append((rel, want, got))
    if bad:
        for rel, want, got in bad:
            _log(f"HASH MISMATCH {rel}: sealed {want[:16]}… "
                 f"on-disk {str(got)[:16]}…")
        raise SystemExit(
            f"freeze integrity check FAILED ({len(bad)} mismatch(es)) "
            "— refusing to run outcomes against unsealed inputs.")
    _log(f"freeze integrity OK: "
         f"{len(freeze.get('code_sha256', {}))} code files + "
         f"{len(freeze.get('bundle_sha256', {}))} bundles verified")


def _expand_units(spec):
    """Ordered unit list (R02-L item 3d).  Tokens: e3:<gen>,
    e1resid:<gen>, e1raw:<gen>, e2:<g|h>, or bare family name / 'all'."""
    out = []
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        fam, _, arg = tok.partition(":")
        if not arg or arg == "all":
            members = (GENS if fam in ("e3", "e1resid", "e1raw")
                       else PAIRS if fam == "e2" else ())
            if not members:
                raise SystemExit(f"unknown unit token: {tok}")
            out.extend(f"{fam}:{m}" for m in members)
        else:
            out.append(f"{fam}:{arg}")
    return out


def _resolve_symbol(sym, bnd):
    """Attach outcome values to every event; returns values dicts."""
    from data_helpers import load_ctx
    ctx = load_ctx(sym, max_bars=None)
    out = {}
    for g, gb in bnd["gens"].items():
        res, _cnt = ao.resolve_arrivals(gb["events"], ctx.bars)
        vb = {i: pr.bounce_cond(res, i) for i in range(len(res))}
        vc = {i: pr.cont_cond(res, i) for i in range(len(res))}
        stall = sum(1 for r in res if r["outcome"] == "NONE")
        out[g] = {"bounce": vb, "cont": vc, "n_none": stall,
                  "n_events": len(res)}
    return out


def _e3_contrib(sym, table):
    e3 = table["e3"]
    return (not e3.get("degenerate")) and e3.get("gate_pass") is True


def _e3_stamp(table):
    return (table["e3"].get("cap_share_stale") is not None and
            table["e3"]["cap_share_stale"] == table["e3"]
            ["cap_share_stale"] and
            table["e3"]["cap_share_stale"] > 0.50)


def run_e3(bundles, vals, gen):
    """E3 unit: generator x endpoint.  Returns unit dict."""
    hb = _Heartbeat(f"e3:{gen}")
    cells, per_cell = [], {}
    for sym in SYMS:
        gb = bundles[sym]["gens"][gen]
        tb = gb["table"]
        if not _e3_contrib(sym, tb):
            per_cell[sym] = {"status": "not-contributing",
                             "gate_pass": tb["e3"].get("gate_pass"),
                             "cap_s": tb["e3"].get("cap_share_stale")}
            continue
        ev, tr = gb["events"], gb["treated"]
        for ep in ENDPOINTS:
            v = vals[sym][gen][EP_KEY[ep]]
            d = ae.e3_D(ev, v, tr)
            r = ae.bootstrap_e3(ev, v, tr, B=B, seed=SEED,
                                progress=hb)
            per_cell.setdefault(sym, {})[ep] = {
                "D": d, "lo": r["lo"], "hi": r["hi"], "p": r["p"],
                "n_boot": r["n_boot"], "n_recent": tb["e3"]["n_recent"],
                "n_stale": tb["e3"]["n_stale"],
                "cap_s": tb["e3"]["cap_share_stale"]}
        cells.append((sym, gb))
    units = {}
    for ep in ENDPOINTS:
        cl = [{"events": gb["events"], "values": vals[sym][gen][EP_KEY[ep]],
               "treated": gb["treated"], "w": float(len(gb["treated"]))}
              for sym, gb in cells]
        pooled = ae.bootstrap_pooled(cl, "e3", B=B, seed=SEED,
                                     progress=hb)
        wsum = sum(c["w"] for c in cl)
        num = sum(c["w"] * per_cell[sym][ep]["D"]
                  for (sym, *_), c in zip(cells, cl)
                  if np.isfinite(per_cell[sym][ep]["D"]))
        units[ep] = {"D_pooled": num / wsum if wsum else float("nan"),
                     "pooled": pooled,
                     "contributing": [s for s, _ in cells]}
    return {"per_cell": per_cell, "units": units,
            "eligible": len(cells) >= 3}


def run_e1resid(bundles, vals, gen):
    hb = _Heartbeat(f"e1resid:{gen}")
    cells, per_cell = [], {}
    for sym in SYMS:
        gb = bundles[sym]["gens"][gen]
        tb = gb["table"]
        ok = (tb["resid"].get("gate_pass") is True and
              tb["resid"].get("recency", {}).get("gate_pass") is True)
        if not ok:
            per_cell[sym] = {"status": "not-contributing"}
            continue
        ev, tr = gb["events"], gb["treated"]
        for ep in ENDPOINTS:
            v = vals[sym][gen][EP_KEY[ep]]
            d = ae.resid_D(ev, v, tr)
            r = ae.bootstrap_resid(ev, v, tr, B=B, seed=SEED,
                                   progress=hb)
            per_cell.setdefault(sym, {})[ep] = {
                "D": d, "lo": r["lo"], "hi": r["hi"], "p": r["p"],
                "n_boot": r["n_boot"], "r2": tb["resid"]["r2"],
                "n_top": tb["resid"]["n_top"],
                "n_bot": tb["resid"]["n_bot"]}
        cells.append((sym, gb))
    units = {}
    for ep in ENDPOINTS:
        cl = [{"events": gb["events"], "values": vals[sym][gen][EP_KEY[ep]],
               "treated": gb["treated"], "w": float(len(gb["treated"]))}
              for sym, gb in cells]
        pooled = ae.bootstrap_pooled(cl, "resid", B=B, seed=SEED,
                                     progress=hb)
        wsum = sum(c["w"] for c in cl)
        num = sum(c["w"] * per_cell[sym][ep]["D"]
                  for (sym, *_), c in zip(cells, cl)
                  if np.isfinite(per_cell[sym][ep]["D"]))
        units[ep] = {"D_pooled": num / wsum if wsum else float("nan"),
                     "pooled": pooled,
                     "contributing": [s for s, _ in cells]}
    return {"per_cell": per_cell, "units": units,
            "eligible": len(cells) >= 3}


def run_e1raw(bundles, vals, gen):
    hb = _Heartbeat(f"e1raw:{gen}")
    per_cell = {}
    for sym in SYMS:
        gb = bundles[sym]["gens"][gen]
        tb = gb["table"]
        if tb["e1"].get("gate_pass") is not True:
            per_cell[sym] = {"status": "not-contributing"}
            continue
        ev = gb["events"]
        e1 = cc.e1_arms(ev, gb["treated"], tb["e1_bounds"])
        for ep in ENDPOINTS:
            v = vals[sym][gen][EP_KEY[ep]]
            est = ae.att_weighted(ev, v, e1["top"], e1["bot"])
            r = ae.bootstrap_weighted(ev, v, e1["top"], e1["bot"],
                                      B=B, seed=SEED, progress=hb)
            per_cell.setdefault(sym, {})[ep] = {
                "D": est["D"], "lo": r["lo"], "hi": r["hi"],
                "p": r["p"], "n_boot": r["n_boot"],
                "n_top": len(e1["top"]), "n_bot": len(e1["bot"]),
                "recency_pass": tb["e1"]["recency"].get("gate_pass")}
    return {"per_cell": per_cell}


def run_e2(bundles, vals, pair):
    hb = _Heartbeat(f"e2:{pair}")
    g, h = pair.split("|")
    cells, per_cell = [], {}
    for sym in SYMS:
        pt = bundles[sym]["pairs"][pair]
        base = pt["grid"]
        gb = bundles[sym]["gens"][base]
        arms = gb.get("pair_arms", {}).get(pair)
        if arms is None or pt.get("gate_pass") is not True:
            per_cell[sym] = {"status": "not-contributing",
                             "gate_pass": pt.get("gate_pass")}
            continue
        ev = gb["events"]
        ia, ib = arms["ia"], arms["ib"]
        for ep in ENDPOINTS:
            v = vals[sym][base][EP_KEY[ep]]
            est = ae.att_weighted(ev, v, ia, ib)
            per_cell.setdefault(sym, {})[ep] = {
                "D": est["D"], "n_a": len(ia), "n_b": len(ib)}
        idx_all = list(ia) + list(ib)
        cells.append((sym, ev, idx_all,
                      np.asarray([True] * len(ia) + [False] * len(ib)),
                      float(len(ia))))
    units = {}
    for ep in ENDPOINTS:
        cl = [{"events": ev, "values": vals[sym][base][EP_KEY[ep]],
               "idx_all": ia_, "is_a": m, "w": w}
              for sym, ev, ia_, m, w in cells]
        pooled = ae.bootstrap_pooled(cl, "pair", B=B, seed=SEED,
                                     progress=hb)
        wsum = sum(c["w"] for c in cl)
        num = sum(c["w"] * per_cell[sym][ep]["D"]
                  for (sym, *_), c in zip(cells, cl)
                  if np.isfinite(per_cell[sym][ep]["D"]))
        units[ep] = {"D_pooled": num / wsum if wsum else float("nan"),
                     "pooled": pooled,
                     "contributing": [s for s, *_ in cells]}
    return {"per_cell": per_cell, "units": units,
            "eligible": len(cells) >= 2}


def _append_trial(family, unit_name, ep, res, freeze_sha):
    metrics = {}
    u = res.get("units", {}).get(ep)
    if u:
        metrics = {"D_pooled": u["D_pooled"],
                   "lo": u["pooled"]["lo"], "hi": u["pooled"]["hi"],
                   "p": u["pooled"]["p"], "n_boot": u["pooled"]["n_boot"],
                   "contributing": u["contributing"]}
    else:
        d = {s: c[ep] for s, c in res.get("per_cell", {}).items()
             if isinstance(c, dict) and ep in c}
        metrics = {"per_cell_D": d}
    return pa_ledger.append(
        {"round": "R02", "family": family, "spec_sha256": freeze_sha,
         "params": {"unit": unit_name, "endpoint": ep,
                    "freeze_sha256": freeze_sha},
         "split": "DESIGN", "symbols": list(SYMS), "tf": "M5",
         "metrics": metrics})


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer, np.floating)):
        return o.item()
    return float(o)


def _write_unit(unit_key, res):
    """R02-L item 3a: persist THIS unit the moment it finishes."""
    os.makedirs(OUT_DIR, exist_ok=True)
    fp = os.path.join(OUT_DIR, unit_key.replace("/", "__")
                      .replace("|", "_") + ".json")
    with open(fp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, default=_json_default)
        f.flush()
        os.fsync(f.fileno())
    return fp


def _run_unit(tok, bundles, vals, fsha):
    """Dispatch one ordered unit token; returns (key, result)."""
    fam, _, arg = tok.partition(":")
    if fam == "e3":
        r = run_e3(bundles, vals, arg)
        key = f"E3/{arg}"
        for ep in ENDPOINTS:
            tid = _append_trial("E3", arg, ep, r, fsha)
            r["units"][ep]["trial_id"] = tid
        return key, r
    if fam == "e1resid":
        r = run_e1resid(bundles, vals, arg)
        key = f"E1R/{arg}"
        for ep in ENDPOINTS:
            tid = _append_trial("E1R", arg, ep, r, fsha)
            r["units"][ep]["trial_id"] = tid
        return key, r
    if fam == "e1raw":
        return f"E1RAW/{arg}", run_e1raw(bundles, vals, arg)
    if fam == "e2":
        r = run_e2(bundles, vals, arg)
        key = f"E2/{arg}"
        for ep in ENDPOINTS:
            tid = _append_trial("E2", arg, ep, r, fsha)
            r["units"][ep]["trial_id"] = tid
        return key, r
    raise SystemExit(f"unknown unit family: {fam}")


def write_reports(results, freeze, freeze_sha, out_dir=None):
    """R02-L item 3e: RESULTS.md + ROUND_REPORT.md, anchored.

    Numbers are tabulated verbatim from the unit results; verdict text
    is the pre-declared language only.  The ledger anchor line is
    embedded via pa_ledger.anchor_md and recorded via append_anchor."""
    rdir = out_dir or os.path.join(_PROOT, "rounds", "R02")
    anchor_line = pa_ledger.anchor_md()
    pa_ledger.append_anchor(note="R02 RESULTS/ROUND_REPORT (R02-L)")
    rows = []
    for uk, r in results.items():
        for ep in ENDPOINTS:
            u = r.get("units", {}).get(ep)
            if not u:
                continue
            p = u["pooled"]
            rows.append((uk, ep, u["D_pooled"], p["lo"], p["hi"],
                         p["p"], p["n_boot"], u["contributing"],
                         u.get("trial_id")))
    tbl = ["| unit | endpoint | D_pooled | lo | hi | p | n_boot | "
           "contributing | trial |",
           "|---|---|---|---|---|---|---|---|"]
    for uk, ep, d, lo, hi, p, nb, contr, tid in rows:
        tbl.append(f"| {uk} | {ep} | {d:.6f} | {lo:.6f} | {hi:.6f} | "
                   f"{p:.6f} | {nb} | {','.join(contr)} | {tid} |")
    body = "\n".join(tbl)
    hdr = (f"# R02 — outcome results\n\nFreeze: FREEZE_v2.json sha256 "
           f"`{freeze_sha}`\nPrereg sha256 "
           f"`{freeze.get('prereg_sha256')}`\n{anchor_line}\n\n"
           "Verdict language is pre-declared in PREREG.md §6/§8; this "
           "file reports numbers only.\n\n")
    res_p = os.path.join(rdir, "RESULTS.md")
    rep_p = os.path.join(rdir, "ROUND_REPORT.md")
    with open(res_p, "w", encoding="utf-8", newline="\n") as f:
        f.write(hdr + body + "\n")
    with open(rep_p, "w", encoding="utf-8", newline="\n") as f:
        f.write("# R02 — round report\n\n" + hdr + body + "\n")
    return res_p, rep_p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", default=UNIT_DEFAULT)
    ap.add_argument("--freeze", default="FREEZE_v2.json")
    a = ap.parse_args()
    slot = pa_slots.acquire("r02-outcomes")
    try:
        freeze_p = os.path.join(_PROOT, "rounds", "R02", a.freeze)
        freeze = json.load(open(freeze_p))
        _verify_freeze(freeze)
        fsha = _sha256(freeze_p)
        bundles = {s: pickle.load(open(
            os.path.join(BUNDLE_DIR, f"{s}.pkl"), "rb"))
            for s in SYMS}
        vals = {}
        for sym in SYMS:
            _log(f"resolving {sym}")
            vals[sym] = _resolve_symbol(sym, bundles[sym])
        results = {}
        for tok in _expand_units(a.units):
            _log(f"unit {tok} START")
            key, r = _run_unit(tok, bundles, vals, fsha)
            fp = _write_unit(key, r)
            results[key] = r
            _log(f"unit {tok} DONE -> {fp}")
        _log("all requested units complete")
    finally:
        pa_slots.release(slot)


if __name__ == "__main__":
    main()
