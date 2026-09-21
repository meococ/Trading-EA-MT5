"""run_counts — OUTCOME-BLIND event census for the physics bake-off (Phase A2).

Runs every registered ZONE-1 generator on one symbol, extracts fresh-approach
events (counts + strata only, no forward prices), and optionally draws the K=5
controls for one generator to measure the realized K distribution.  Nothing in
this script reads an outcome; it is safe to run before FREEZE.json.

Usage:
    python run_counts.py --symbols EURUSD,GBPUSD,USDJPY,AUDUSD \
        --out counts --controls-for line1_cluster
"""

import argparse
import csv
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import phys_common as pc  # noqa: E402
import phys_extract as px  # noqa: E402


def _load(symbol, max_bars=None):
    from data_helpers import load_ctx
    import registry

    return load_ctx(symbol, max_bars=max_bars), registry


def census(events):
    out = {"n": len(events),
           "by_tercile": _counts_by(events, "tercile"),
           "by_kind": _counts_by(events, "kind"),
           "by_year": _counts_by(events, "year"),
           "by_session": _counts_by(events, "session"),
           "by_symbol": _counts_by(events, "symbol"),
           "by_overlap": _counts_by(events, "overlap"),
           "strength_q": None}
    s = np.asarray([e["strength"] for e in events], dtype=np.float64)
    if s.size:
        out["strength_q"] = [float(np.percentile(s, q))
                             for q in (0, 25, 33.333, 50, 66.667, 75, 100)]
    return out


def _counts_by(events, key):
    d = {}
    for e in events:
        k = str(e.get(key, "?"))
        d[k] = d.get(k, 0) + 1
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="EURUSD")
    ap.add_argument("--generators", default="all")
    ap.add_argument("--out", default=os.path.join(HERE, "counts"))
    ap.add_argument("--controls-for", default="")
    ap.add_argument("--max-bars", type=int, default=None)
    ap.add_argument("--r5-cap", type=int, default=1)
    args = ap.parse_args()

    import pa_slots

    os.makedirs(args.out, exist_ok=True)
    report = {"utc": pc.utc_now(), "seed": pc.SEED, "r5_cap": bool(args.r5_cap),
              "zone_code_sha256": pc.dir_code_sha256(pc.ZONES_DIR),
              "generators": {}, "symbols": {}}
    with pa_slots.slot("phys_counts", timeout=1800):
        for symbol in args.symbols.split(","):
            ctx, registry = _load(symbol, args.max_bars)
            names = registry.names() if args.generators == "all" else args.generators.split(",")
            sym_info = {"n_m5": int(ctx.n), "generators": {}}
            srcs = {}
            t0 = time.time()
            for name in names:
                ts = time.time()
                from phys_source import GenSource

                src = GenSource(name, registry.get(name), ctx).run()
                run_s = time.time() - ts
                ev, cnt = px.extract_events(src)
                csv_path = os.path.join(args.out, f"EVENTS_{symbol}_{name}.csv")
                px.write_events_csv(ev, csv_path)
                bounds = px.tercile_bounds([e["strength"] for e in ev])
                for e in ev:
                    e["tercile"] = px.tercile_of(e["strength"], *bounds)
                srcs[name] = src
                sym_info["generators"][name] = {
                    "run_seconds": round(run_s, 1),
                    "counters": cnt,
                    "census": census(ev),
                    "tercile_bounds": list(bounds),
                    "info": src.info(),
                    "events_csv": csv_path,
                }
                report["generators"].setdefault(name, src.info())
                print(f"[{symbol}] {name}: run {run_s:.1f}s events={cnt['events']} "
                      f"zones={cnt['zones_total']} -> {csv_path}", flush=True)
            sym_info["total_seconds"] = round(time.time() - t0, 1)

            if args.controls_for:
                name = args.controls_for
                if name in srcs:
                    from phys_controls import RefIndex, extract_controls
                    from phys_extract import read_events_csv

                    t1 = time.time()
                    ref = RefIndex(ctx.refs, grid_pips=50.0, bars=ctx.bars)
                    ev = px.read_events_csv(
                        os.path.join(args.out, f"EVENTS_{symbol}_{name}.csv"))
                    for e in ev:
                        e["bar_idx"] = int(e["bar_idx"])
                        e["side"] = int(e["side"])
                        for k in ("lo", "hi", "w", "near", "far", "m", "close_prev"):
                            e[k] = float(e[k])
                    # R02-A F10: Addendum-2 signature (events, src, ref, bars, symbol)
                    ctrl, ccnt = extract_controls(ev, srcs[name], ref, ctx.bars,
                                                  symbol)
                    cpath = os.path.join(args.out, f"CONTROLS_{symbol}_{name}.csv")
                    from phys_controls import CONTROL_FIELDS
                    with open(cpath, "w", newline="", encoding="utf-8") as f:
                        wr = csv.DictWriter(f, fieldnames=CONTROL_FIELDS)
                        wr.writeheader()
                        for c in ctrl:
                            wr.writerow({k: c.get(k) for k in CONTROL_FIELDS})
                    sym_info["controls_pilot"] = {
                        "generator": name, "counters": ccnt,
                        "mean_k": (ccnt["controls"] / ccnt["events"]
                                   if ccnt["events"] else None),
                        "seconds": round(time.time() - t1, 1), "csv": cpath,
                    }
                    print(f"[{symbol}] controls {name}: {ccnt}", flush=True)
            report["symbols"][symbol] = sym_info
    with open(os.path.join(args.out, "COUNTS.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
    print("wrote", os.path.join(args.out, "COUNTS.json"))


if __name__ == "__main__":
    main()
