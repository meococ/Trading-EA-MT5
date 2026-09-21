"""arrival_sens — w_g/anchor sensitivity, sharing GenSource per generator.

    python -B arrival_sens.py EURUSD line1_cluster,ref_levels
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import arrival_common as ac  # noqa: E402


def main():
    symbol, gens = sys.argv[1], sys.argv[2].split(",")
    wscales = [float(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3
                                 else ["0.75", "1.0", "1.5"])]
    anchors = (sys.argv[4].split(",") if len(sys.argv) > 4
               else ["open", "prevclose"])
    from data_helpers import load_ctx
    import registry
    from phys_source import GenSource

    ctx = load_ctx(symbol, max_bars=None)
    bars = ctx.bars
    o = np.asarray(bars["o"], dtype=np.float64)
    c = np.asarray(bars["c"], dtype=np.float64)
    segs = ac.day_segments(bars)
    for g in gens:
        src = GenSource(g, registry.get(g), ctx).run()
        u_atr, _ = ac.armed_width_atr(src, step=288)
        for ws in wscales:
            for anch in anchors:
                grids = []
                for di, (d0, d1) in enumerate(segs):
                    a = ctx.a(d0)
                    an = float(o[d0]) if anch == "open" else (
                        float(c[d0 - 1]) if d0 > 0 else float("nan"))
                    bands, w_p = ac.build_day_grid(an, a, u_atr, ws)
                    grids.append((bands, w_p, di, an, a) if bands else None)
                ev, cnt = ac.arrival_events(bars, ctx, grids)
                arms, diag = ac.tag_arms(ev, src, ac.MARGINS)
                row = {"symbol": symbol, "generator": g, "wscale": ws,
                       "anchor": anch, "u_atr": u_atr,
                       "n_events": len(ev), "bands": cnt["bands"]}
                for m, tag in arms.items():
                    tr, ct = tag["treated"], tag["control"]
                    sup = ac.common_support(ev, tr, ct)
                    row[f"m{m}"] = {"T": len(tr), "C": len(ct),
                                    "X": len(tag["excluded"]),
                                    "supT": sup["support_T"],
                                    "supC": sup["support_C"]}
                print("JSON " + json.dumps(row, default=float), flush=True)


if __name__ == "__main__":
    main()
