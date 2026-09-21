"""arrival_run — R02 feasibility driver (OUTCOME-BLIND).

Usage:
    python -B arrival_run.py EURUSD line1_cluster,ref_levels [--wscale 1.0]
           [--anchor open|prevclose] [--max-bars N]

Prints one JSON line per (symbol, generator, w_scale, anchor) with event
counts, per-margin treated/control/excluded counts, feature summaries and
common-support shares.  Computes NO outcome column.
"""

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import arrival_common as ac  # noqa: E402


def run_one(symbol, gen_name, w_scale=1.0, anchor="open", max_bars=None,
            margins=ac.MARGINS):
    from data_helpers import load_ctx
    import registry
    from phys_source import GenSource

    ctx = load_ctx(symbol, max_bars=max_bars)
    bars = ctx.bars
    src = GenSource(gen_name, registry.get(gen_name), ctx).run()

    u_atr, n_samp = ac.armed_width_atr(src, step=288)
    segs = ac.day_segments(bars)
    o = np.asarray(bars["o"], dtype=np.float64)
    c = np.asarray(bars["c"], dtype=np.float64)
    grids = []
    for di, (d0, d1) in enumerate(segs):
        a = ctx.a(d0)
        anch = float(o[d0]) if anchor == "open" else (
            float(c[d0 - 1]) if d0 > 0 else float("nan"))
        bands, w_p = ac.build_day_grid(anch, a, u_atr, w_scale)
        grids.append((bands, w_p, di, anch, a) if bands else None)

    events, cnt = ac.arrival_events(bars, ctx, grids)
    arms, diag = ac.tag_arms(events, src, margins)

    out = {
        "symbol": symbol, "generator": gen_name, "w_scale": w_scale,
        "anchor": anchor, "u_atr": u_atr, "u_samples": n_samp,
        "counters": cnt, "n_events": len(events), "diag": diag,
        "margins": {},
    }
    for m, tag in arms.items():
        tr, ct = tag["treated"], tag["control"]
        sup = ac.common_support(events, tr, ct)
        # nearness-restricted control: |mid - c[t-1]| <= 2.5 x A(t) (D6)
        near_ct = [i for i in ct if events[i]["dist_cp"] <= 2.5]
        sup_near = ac.common_support(events, tr, near_ct)
        out["margins"][str(m)] = {
            "treated": len(tr), "control": len(ct),
            "excluded": len(tag["excluded"]),
            "control_near": len(near_ct),
            "sum_T": ac.dist_summary(events, tr),
            "sum_C": ac.dist_summary(events, ct),
            "sum_Cn": ac.dist_summary(events, near_ct),
            "support": sup, "support_near": sup_near,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("generators")
    ap.add_argument("--wscale", default="1.0")
    ap.add_argument("--anchor", default="open")
    ap.add_argument("--max-bars", type=int, default=None)
    a = ap.parse_args()
    for ws in [float(x) for x in a.wscale.split(",")]:
        for anch in a.anchor.split(","):
            for g in a.generators.split(","):
                r = run_one(a.symbol, g, w_scale=ws, anchor=anch,
                            max_bars=a.max_bars)
                print("JSON " + json.dumps(r, default=float), flush=True)


if __name__ == "__main__":
    main()
