"""_gate_pack_c1.py — build GATE_PACK_C1_<hash>.md for the C-round-1
freeze (R40 §40.x queue item 7, R42 §42.5/§42.8).

Takes the build lane's declared STABLE hash + cache variant (or live
disk state) and emits the pack: M1 table vs v0 with paired day-boot
CIs, clutter median + distribution, the six diagnostic rows, the
verified keep verdicts, and a one-screen status.

Everything is measured by this lane's own scorer (m1_row.py) — the
build lane's _m1.py is never the verdict source.

Usage:
  python evalcheck/_gate_pack_c1.py --hash <full16> --variant <v>
  python evalcheck/_gate_pack_c1.py --live
"""
import argparse
import datetime
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import funnel as F                              # noqa: E402
import m1_row as M                              # noqa: E402
import pa_slots                                 # noqa: E402


def md_fam(res, v0, rng):
    rows = []
    for fam, k in M.M1 + M.EXTRA:
        h, g = M.fam_recall(res["tau"], fam, k)
        v = h / g if g else 0.0
        hv, gv = M.fam_recall(v0["tau"], fam, k)
        vv = hv / gv if gv else 0.0
        dd = M.day_diff_ci(res["tau"], v0["tau"], fam, k, rng)
        ci = "[%+.3f..%+.3f]" % (dd[1], dd[2]) if dd else ""
        rows.append((fam, k, v, h, g, vv, hv, gv,
                     (dd[0] if dd else None), ci))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash", default="")
    ap.add_argument("--variant", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--extra-arm", action="append", default=[],
                    help="'hash:variant:label' extra rows (e.g. the "
                         "fam-OFF fallback from §42.5)")
    args = ap.parse_args()

    recs = C.load_tune()
    import random
    rng = random.Random(M.SEED)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")

    with pa_slots.slot("evalcheck-gatepack-c1", timeout=1800):
        h0 = F.code_hash(F.V0_FILES)
        v0 = M.measure(h0, "m1_v0", recs)
        if len(v0["tau"]) < 400:
            v0 = M.measure(h0, "", recs)
        cand = M.measure(args.hash, args.variant, recs)
        extras = []
        for spec in args.extra_arm:
            hh, vv, ll = spec.split(":")
            extras.append((ll, hh, vv, M.measure(hh, vv, recs)))

    d_c = M.diag_line(cand["diag"])
    d_0 = M.diag_line(v0["diag"])
    rows = md_fam(cand, v0, rng)

    L = []
    A = L.append
    A("# GATE_PACK_C1 — C-round-1 freeze pack (EVAL-AUDIT)")
    A("")
    A("Generated %s by EVAL-AUDIT's own scorer (m1_row.py), TUNE 198 "
      "panels, ruler `50e11fd5a2ab7974`." % now)
    A("")
    A("Candidate: `%s` variant=`%s` (%s)" % (
        args.hash or "live", args.variant or "(disk defaults)",
        args.label or "build-lane STABLE"))
    A("")
    A("## M1 — per-family recall at the author's budget")
    A("")
    A("| arm | box@1 | level@1 | line@2 | bracket@1 † |")
    A("|---|---|---|---|---|")
    h, g = M.fam_recall(v0["tau"], "box", 1)
    hl, gl = M.fam_recall(v0["tau"], "level", 1)
    hn, gn = M.fam_recall(v0["tau"], "line", 2)
    hb, gb = M.fam_recall(v0["tau"], "bracket", 1)
    A("| v0 `%s` | %.3f (%d/%d) | %.3f (%d/%d) | %.3f (%d/%d) | "
      "%.3f (%d/%d) |" % (h0[:8], h / g, h, g, hl / gl, hl, gl,
                          hn / gn, hn, gn, hb / gb, hb, gb))
    parts = {fam: (v, hh2, gg2, dd if dd is not None else 0.0, ci)
             for fam, k, v, hh2, gg2, vv, hv, gv, dd, ci in rows}
    A("| candidate | %.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s | "
      "%.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s |" % (
          parts["box"][0], parts["box"][1], parts["box"][2],
          parts["box"][3], parts["box"][4],
          parts["level"][0], parts["level"][1], parts["level"][2],
          parts["level"][3], parts["level"][4],
          parts["line"][0], parts["line"][1], parts["line"][2],
          parts["line"][3], parts["line"][4],
          parts["bracket"][0], parts["bracket"][1], parts["bracket"][2],
          parts["bracket"][3], parts["bracket"][4]))
    for ll, hh2, vv2, res in extras:
        r2 = md_fam(res, v0, rng)
        p2 = {fam: (v, hh3, gg3, dd if dd is not None else 0.0, ci)
              for fam, k, v, hh3, gg3, hv, gv, dd, ci in r2}
        A("| %s `%s` | %.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s | "
          "%.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s |" % (
              ll, hh2[:8], p2["box"][0], p2["box"][1], p2["box"][2],
              p2["box"][3], p2["box"][4],
              p2["level"][0], p2["level"][1], p2["level"][2],
              p2["level"][3], p2["level"][4],
              p2["line"][0], p2["line"][1], p2["line"][2],
              p2["line"][3], p2["line"][4],
              p2["bracket"][0], p2["bracket"][1], p2["bracket"][2],
              p2["bracket"][3], p2["bracket"][4]))
    A("")
    A("† bracket@1 reported, not part of M1 (no price check, "
      "R30 §30.3). CIs are paired day-bootstrap of (arm − v0), "
      "seed 20260921, 1000 resamples.")
    A("")
    A("## Clutter + diagnostics (candidate)")
    A("")
    A("- clutter ratio median (eng/gold per panel): **%.2f** "
      "(v0 %.2f); %d/%d scored panels ≤ 5.0" % (
          d_c["clutter_med"], d_0["clutter_med"],
          sum(1 for x in d_c["ratios"] if x <= 5.0),
          len(d_c["ratios"])))
    A("- BOX recall %.3f | BOX precision %.3f | PATTERN_LINE recall "
      "%.3f | LEVEL_CARRIED recall %.3f | LABEL_TF agreement %d/%d | "
      "clutter ratio med %.2f" % (
          d_c["BOX_rec"], d_c["BOX_prec"], d_c["PL_rec"],
          d_c["LC_rec"], d_c["tf"][0], d_c["tf"][1],
          d_c["clutter_med"]))
    A("")
    A("## Keep verdicts (EVAL-AUDIT independent, own scorer)")
    A("")
    A("- K1 line.lab_score @afba83c5: CONFIRMED (+2 line hits, "
      "OFF-id 1728/1728 vs STABLE parent)")
    A("- K2 defended_origin+def_mini_off @e62f2dc9: CONFIRMED "
      "(+2 level, −1/−1 allowed, OFF-id 1728/1728 cross-hash)")
    A("- K3 bxcombo @dd96c5fe: CONFIRMED (+1 box, +2 line, clutter "
      "5.00, OFF-id 1728/1728 cross-hash)")
    A("- K4 box_score_pick arm A @cfb862d4: CONFIRMED (+4 box, "
      "OFF-id 1728/1728); arm B rejection CONFIRMED (−2 box)")
    A("- K5 line.slope_floor=0.25 @75a9650c: CONFIRMED (+1 line, "
      "clutter 5.00 thin margin 90/179, OFF-id 1728/1728)")
    A("- K6 box.cong_trigger k5.5/N6 @df79ade3: CONFIRMED (+2 box "
      "9.4b+9.48b miss→hit, zero losses, clutter 5.00, OFF-id "
      "1728/1728 post-§45.2 fix, suite 65/72 same-7). §46.1 noise "
      "note: +2/119 is within noise — the claim is that the "
      "mechanism is real (fresh congestion boxes outrank stale "
      "envelopes at τ), not that box fidelity improved "
      "significantly. Robustness: k 4.0–5.5 and N 6–8 hold the +2; "
      "k 3.0 loses it.")
    A("- box_prio (§42.4, 4 forms): all FAIL keep-rule on own scorer "
      "— v1 cd14f5fc lvl −3 cl 6.33; v2 cd00d0be box +1 lvl −4 cl "
      "6.00 (+OFF-id broken: 3 obj + 1107 cand_log diffs); v3 "
      "afe99034 box +2 lvl −2 cl 6.33; v4 box_tau_prio c14060cb box "
      "−3 cl 5.00. Suite on v2-ON config 72/72 (fixes the 7 fixtures) "
      "but M1 cost stands — correctly rejected.")
    A("- fam_context (§44.2, 2 forms): FAIL — plain @88438120 lvl −2 "
      "cl 5.67 box flat; +ctxbirths-off @4dcc44d7 box +1 lvl −2 line "
      "−2 cl 5.67. Suite 72/72 both but M1 cost stands.")
    A("- joint_struct v2 (§43.4.2, structure-only): FAIL both caps "
      "@69cda24a — cap4 lvl −4/line −4 cl 5.33; cap3 lvl −3/line −4/"
      "brk −7 cl 5.33. famctx+jstruct (§45.3.2): FAIL both caps "
      "@df79ade3 — cap4 .076/.026/.083 brk −9 cl 5.67 (suite 72/72); "
      "cap3 .076/.066/.088 brk −15 cl 5.67 (suite 71/72).")
    A("- §42.5 choice rows (own scorer): kept (K1–K5 pre-K6) "
      ".059/.079/.104 cl 5.00; famoff_on .067/.053/.067 cl 5.67 "
      "(line below v0); famoff_nosup .042/.053/.073 cl 5.00 — kept "
      "config is M1-best; §45.4 froze the choice to K1–K6.")
    A("- Suite leg (R42 §42.3, unmodified fixtures, each keep's own "
      "config): K1 72/72, K2 72/72, K3 65/72, K4 65/72, K5 65/72, "
      "K6 65/72 — "
      "the same 7 theory fixtures fail once fam_budget+fam_caps hold "
      "(CONTEXT_RANGE occupies the box-family slot); box_prio ON or "
      "fam flags OFF each restore 72/72.")
    A("")
    A("## Known spec violation carried into the freeze (R45 §45.4)")
    A("")
    A("- Under `fam_budget`, a CONTEXT_RANGE can hold the box "
      "family's single live slot, so the book's BOX is not drawn in "
      "the textbook patterns of Fig 3.1, 3.8 and 3.9. The frozen "
      "suite runs unmodified: 65/72, with the seven named fixtures "
      "failing (pullback-end box birth, double-top box, false-break "
      "wick, break-close, tease-vs-proper, TF relabel, re-anchor "
      "double-top).")
    A("- Every suite-curing arm measured this round costs M1 "
      "(box_prio 4 forms, fam_context 2 forms, famoff 2 forms); "
      "none passes §34.5/§41.3. This defect is first on the next "
      "round's list (fam_context + structure-only cap).")
    A("")
    A("## Tested and rejected this round (EVAL-AUDIT own scorer)")
    A("")
    A("| arm | hash | box@1 | level@1 | line@2 | clutter | why |")
    A("|---|---|---|---|---|---|---|")
    for r in [
        ("level_touch_rec", "22888182", ".025", ".013", ".088", "5.00",
         "level −5"),
        ("line_dedup_merge", "22888182", ".025", ".079", ".098", "5.00",
         "zero-delta"),
        ("box_score_pick_prio (arm B)", "cfb862d4", ".042", ".092",
         ".098", "5.00", "box −2 vs arm A"),
        ("fam_total_live=4/3/2", "10c34e28/fbb3a173",
         ".050/.042/.042", ".026/.066/.026", ".057/.062/.057",
         "3.00/2.33/1.50", "cap counts transient annots; M1 losses"),
        ("famcap_bracket=2", "10c34e28", ".059", ".079", ".098",
         "5.00", "bracket −1, no gain"),
        ("line.steep_pick", "75a9650c", ".059", ".079", ".088",
         "5.00", "line −2"),
        ("box_prio v1 birth-path", "cd14f5fc", ".059", ".039",
         ".098", "6.33", "level −3, clutter"),
        ("box_prio v2 +τ-rank", "cd00d0be", ".067", ".026", ".098",
         "6.00", "level −4, clutter, OFF-id leak"),
        ("box_prio v3 RO-excl", "afe99034", ".076", ".053", ".098",
         "6.33", "level −2, clutter"),
        ("box_tau_prio", "c14060cb", ".034", ".079", ".104", "5.00",
         "box −3 target down"),
        ("famoff (§42.5 row)", "a7f35026/e1edc511", ".067", ".053",
         ".067", "5.67", "level+line below v0, clutter"),
        ("famoff_nosup (§42.5 row)", "e1edc511", ".042", ".053",
         ".073", "5.00", "worse than kept on box+line"),
        ("fam_context", "88438120", ".059", ".053", ".098", "5.67",
         "level −2, clutter (suite 72/72)"),
        ("famctx + CR births off", "4dcc44d7", ".067", ".053",
         ".093", "5.67", "level −2, line −2, clutter"),
        ("joint_struct cap4/cap3", "69cda24a", ".059/.059",
         ".026/.039", ".083/.083", "5.33/5.33",
         "cap churn burns levels/lines"),
        ("famctx+jstruct cap4/cap3", "df79ade3", ".076/.076",
         ".026/.066", ".083/.088", "5.67/5.67",
         "churn; cap3 also breaks pierce fixture (71/72)"),
        ("box.level_edges", "9d76b883/e1edc511", ".059/.050",
         ".079/.079", ".104/.104", "5.00/5.00", "zero-delta / −1"),
        ("cong_density (peaks)", "0a100806", ".076", ".079", ".104",
         "5.00", "inert — 0 dens births, same winners"),
        ("cong_density q-mode", "13b3f53d", ".059", ".092", ".104",
         "5.00", "box −2 vs K6 (trims the edges that matched)"),
        ("cong_subband", "5928a0e2", ".076", ".079", ".104", "5.33",
         "flat box, clutter +0.33, 1123 cands 0 born"),
    ]:
        A("| %s | %s | %s | %s | %s | %s | %s |" % r)
    A("")
    A("## Leak ledger (R45 §45.2 / R46 §46.1, brief)")
    A("")
    A("- The `_propose_window` narrowing + unconditional "
      "`congestion_scan` cand_log writes leaked into every hash "
      "between `cd00d0be` and `30486c39` inclusive. Object footprint: "
      "one `why` label flip (cluster_range→congestion_scan) on "
      "2012-04-04 (panels 9.25a/b/c); cand_log diffs on ~1107 runs.")
    A("- Clean hashes: ≤ `cd14f5fc` and ≥ `df79ade3`. Every keep "
      "(K1–K6) was verified on clean code; every leaky-hash verdict "
      "is a FAIL or zero-delta whose margin (≥2 hits) exceeds the "
      "leak's footprint, and both arms shared it — rejections stand.")
    A("")
    A("## Residual coverage — the no-edge class (R48 §48.1)")
    A("")
    A("- 51 no-edge box goldens shrank to 38 under K6 (congestion "
      "proposals now carry matching edges for 13). BOX-LAB's causal "
      "census: a union of sources (10-pip rounds, pivots, buildup "
      "close extremes, 6h session hi/lo, prior-day hi/lo) reaches "
      "both edges of 27/38; 11 sit on no standard structure.")
    A("- **Null caveat (Lead's):** at 1.5–5 pip tolerance a 10-pip "
      "grid covers much of the price range by chance; R39 found the "
      "author's levels no rounder than chance (9% vs 8% null). Each "
      "source's share must be re-measured against a shuffled-edge "
      "null before building on it — next-round item (§48.3: "
      "old-structure edges inside qualified congestion runs, "
      "null-first).")
    A("")
    A("## Status")
    A("")
    A("_status block filled at freeze._")
    A("")

    out = os.path.join(HERE, "GATE_PACK_C1_%s.md"
                       % ((args.hash or "live")[:8]))
    open(out, "w", encoding="utf8").write("\n".join(L))
    print("wrote %s" % out)
    try:
        print("\n".join(L[:40]))
    except UnicodeEncodeError:
        print("(preview suppressed: console codepage)")


if __name__ == "__main__":
    main()
