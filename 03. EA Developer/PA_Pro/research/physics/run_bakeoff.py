"""run_bakeoff — R01 zone-generator physics bake-off driver.

Phases:
  build    DESIGN core symbols, one pass per generator: ARMED fresh-approach
           events + K=5 Addendum-2 controls + counters + coverage sample.
           Writes EVENTS/CONTROLS CSVs with NO outcome column anywhere.
  verify   (post-freeze) resolve outcomes for events and controls and write
           RESOLVED_<SYM>_<GEN>.npz-ready JSON; refuses if FREEZE.json is
           older than the CSV mtimes.
  report   pooled statistics per generator, charter gate + winner rule,
           PHYSICS_RESULTS.md tables, one ledger trial per generator.

Usage:
    python run_bakeoff.py build --symbols EURUSD,GBPUSD,USDJPY,AUDUSD
    python run_bakeoff.py resolve --symbols ...
    python run_bakeoff.py report
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

OUT = os.path.join(HERE, "bakeoff")
ROUNDS = os.path.join(pc.PA_PRO, "rounds", "R01")


def _load_ctx(symbol):
    from data_helpers import load_ctx

    return load_ctx(symbol, max_bars=None)


def _to_num(row, keys):
    for k in keys:
        if k in row and row[k] != "":
            row[k] = float(row[k]) if "." in str(row[k]) or "e" in str(row[k]) \
                else int(row[k])
    return row


FLOAT_EVENT = ("lo", "hi", "w", "near", "far", "m", "strength", "close_prev",
               "close_t")
INT_EVENT = ("zid", "bar_idx", "bar_t", "utc_min", "year", "side", "touches",
             "n_respected", "role_flip", "age_bars", "overlap")
FLOAT_CTRL = ("lo", "hi", "w", "near", "far", "m")
INT_CTRL = ("anchor_i", "anchor_bar_idx", "anchor_zid", "slot", "draw",
            "bar_idx", "bar_t", "side", "tk_dt")


def load_rows(path, floats, ints):
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(_to_num(row, floats + ints))
    return rows


def phase_build(symbols, generators, controls=True):
    import pa_slots
    from phys_source import GenSource
    from phys_controls import RefIndex, extract_controls
    import registry

    os.makedirs(OUT, exist_ok=True)
    names = registry.names() if generators == "all" else generators.split(",")
    summary = {}
    with pa_slots.slot("phys_bakeoff_build", timeout=3600):
        for symbol in symbols:
            ctx = _load_ctx(symbol)
            n = int(ctx.n)
            bars = ctx.bars
            warm = np.asarray(bars.get("warmup", np.zeros(n, bool)), dtype=bool)
            live = np.flatnonzero(~warm)
            sample = live[::48]
            ref = RefIndex(ctx.refs, grid_pips=50.0, bars=bars)
            sym_summary = {}
            for name in names:
                t0 = time.time()
                src = GenSource(name, registry.get(name), ctx).run()
                t_run = time.time() - t0
                ev, ecnt = px.extract_events(src, population="armed")
                px.write_events_csv(ev, os.path.join(OUT, f"EVENTS_{symbol}_{name}.csv"))
                cov = [src.armed_coverage(int(t)) for t in sample]
                cov = [c for c in cov if c == c]
                t_ctrl = 0.0
                ccnt = None
                if controls and ev:
                    t1 = time.time()
                    ctrl, ccnt = extract_controls(ev, src, ref, bars, symbol)
                    from phys_controls import CONTROL_FIELDS

                    cpath = os.path.join(OUT, f"CONTROLS_{symbol}_{name}.csv")
                    with open(cpath, "w", newline="", encoding="utf-8") as f:
                        wr = csv.DictWriter(f, fieldnames=CONTROL_FIELDS)
                        wr.writeheader()
                        for c in ctrl:
                            wr.writerow({k: c.get(k) for k in CONTROL_FIELDS})
                    t_ctrl = time.time() - t1
                sym_summary[name] = {
                    "run_s": round(t_run, 1), "ctrl_s": round(t_ctrl, 1),
                    "extract": ecnt, "controls": ccnt,
                    "coverage_med": float(np.median(cov)) if len(cov) else None,
                    "coverage_mean": float(np.mean(cov)) if len(cov) else None,
                    "n_events": len(ev),
                    "strength_q33_q67": list(px.tercile_bounds(
                        [e["strength"] for e in ev])),
                    "info": src.info(),
                }
                print(f"[{symbol}] {name}: events={len(ev)} "
                      f"(all_live={ecnt['events_all_live']}) "
                      f"controls={(ccnt or {}).get('controls')} run={t_run:.1f}s "
                      f"ctrl={t_ctrl:.1f}s cov={sym_summary[name]['coverage_med']}",
                      flush=True)
            summary[symbol] = sym_summary
            with open(os.path.join(OUT, f"COUNTERS_{symbol}.json"), "w",
                      encoding="utf-8") as f:
                json.dump(sym_summary, f, indent=1, sort_keys=True)
    with open(os.path.join(OUT, "BUILD_SUMMARY.json"), "w", encoding="utf-8") as f:
        json.dump({"utc": pc.utc_now(), "symbols": summary,
                   "zone_code_sha256": pc.dir_code_sha256(pc.ZONES_DIR),
                   "physics_code_sha256": pc.dir_code_sha256(HERE)},
                  f, indent=1, sort_keys=True)
    print("build done", pc.utc_now())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["build", "resolve", "report"])
    ap.add_argument("--symbols", default="EURUSD,GBPUSD,USDJPY,AUDUSD")
    ap.add_argument("--generators", default="all")
    ap.add_argument("--no-controls", action="store_true")
    args = ap.parse_args()
    if args.phase == "build":
        phase_build(args.symbols.split(","), args.generators,
                    controls=not args.no_controls)
    else:
        import phys_analysis

        if args.phase == "resolve":
            phys_analysis.phase_resolve(args.symbols.split(","),
                                        args.generators)
        else:
            phys_analysis.phase_report(args.symbols.split(","),
                                       args.generators)


if __name__ == "__main__":
    main()
