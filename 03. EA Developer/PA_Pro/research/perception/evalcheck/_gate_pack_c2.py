"""_gate_pack_c2.py — build GATE_PACK_C2_<hash>.md for the C-round-2
close (PLAYBOOK_C2 E6; R56 context: freeze withdrawn, pack documents
the C-2 end state = K1..K9 + F1).

M1 table vs v0 with paired day-boot CIs, clutter median + margin, the
six diagnostics, K7-K9 verdicts with flipped goldens, the rejected-arm
table, fixture-debt pointer, F1 note, and a one-screen status.

Everything is measured by this lane's own scorer (m1_row.py).

Usage:
  python evalcheck/_gate_pack_c2.py
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import funnel as F                              # noqa: E402
import m1_row as M                              # noqa: E402
import pa_slots                                 # noqa: E402

STABLE = "4c2df34d7a2a8ee3"
K9_HASH = "ee2cbf1202db47b6"
K9_VARIANT = "c1r_p_base"


def main():
    recs = C.load_tune()
    import random
    rng = random.Random(M.SEED)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")

    with pa_slots.slot("evalcheck-gatepack-c2", timeout=1800):
        h0 = F.code_hash(F.V0_FILES)
        v0 = M.measure(h0, "m1_v0", recs)
        if len(v0["tau"]) < 400:
            v0 = M.measure(h0, "", recs)
        cand = M.measure(K9_HASH, K9_VARIANT, recs)

    d_c = M.diag_line(cand["diag"])
    d_0 = M.diag_line(v0["diag"])

    import _gate_pack_c1 as G
    rows = G.md_fam(cand, v0, rng)

    L = []
    A = L.append
    A("# GATE_PACK_C2 — C-round-2 close pack (EVAL-AUDIT)")
    A("")
    A("Generated %s by EVAL-AUDIT's own scorer (m1_row.py), TUNE 198 "
      "panels, ruler `50e11fd5a2ab7974`." % now)
    A("")
    A("STABLE C-2: `%s` = C1 `9acaa206` + K7 + K8 + K9 + F1. F1 is "
      "behaviour-neutral (TUNE 1728/1728 byte-identical, verified), so "
      "the measured row below is the K9 state — `c1r_p_base@%s`, "
      "byte-identical to the merged engine's canonical output." % (
          STABLE, K9_HASH[:8]))
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
    A("| STABLE C-2 | %.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s | "
      "%.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s |" % (
          parts["box"][0], parts["box"][1], parts["box"][2],
          parts["box"][3], parts["box"][4],
          parts["level"][0], parts["level"][1], parts["level"][2],
          parts["level"][3], parts["level"][4],
          parts["line"][0], parts["line"][1], parts["line"][2],
          parts["line"][3], parts["line"][4],
          parts["bracket"][0], parts["bracket"][1], parts["bracket"][2],
          parts["bracket"][3], parts["bracket"][4]))
    A("")
    A("† bracket@1 reported, not part of M1 (no price check, "
      "R30 §30.3). CIs are paired day-bootstrap of (arm − v0), "
      "seed 20260921, 1000 resamples.")
    A("")
    A("## Clutter + diagnostics (STABLE C-2)")
    A("")
    A("- clutter ratio median (eng/gold per panel): **%.2f** "
      "(v0 %.2f); %d/%d scored panels <= 5.0" % (
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
    A("## Keep verdicts (C-2, EVAL-AUDIT independent, own scorer)")
    A("")
    A("- K7 marker.off @66f596dc (ctxy_off vs bmoff_on): CONFIRMED, "
      "ink-only rule. M1 level 6->7 (+1), box/line/bracket flat; "
      "clutter 5.00->4.67; margin 90->103 (+13>=+5); OFF-id vs "
      "m1_v1@9acaa206 1728/1728 obj+cand_log+events; suite 65/72 "
      "named-seven. Flipped golden: +1 miss->hit = 9.64c MINI_LEVEL "
      "t1010-1025 @1.25277; zero hit->miss.")
    A("- K8 box.cong_pivedge @81f7503f (pedg_off vs pedg_on; defaults "
      "be4eea26): CONFIRMED, generation rule. box 9->10 (+1), level "
      "7->8 (+1), line/bracket flat; clutter 4.67=; margin 103->101 "
      "(-2 allowed under generation rule); OFF-id vs both parent "
      "references 1728/1728; suite 65/72 named-seven. Flipped "
      "goldens: +2 miss->hit = 9.2b BOX t580-810 @1.3261, 9.49a "
      "LEVEL_CARRIED t591-630 @1.3027; zero hit->miss.")
    A("- K9 salience.rate_label_tf=2/day @759d9036 (ltfcap_off vs "
      "ltfcap_on; defaults ee2cbf12): CONFIRMED, ink-only rule. M1 "
      "all flat; clutter 4.67->4.33; margin 101->114 (+13>=+5); "
      "OFF-id 1728/1728; suite 65/72 named-seven. Zero flipped "
      "goldens (pure ink reduction).")
    A("- F1 perf patch (engine.py+swings.py): CONFIRMED "
      "behaviour-neutral — TUNE 1728/1728 canonical identity incl. "
      "cand_log+events, 35-day DESIGN continuous identical, suite "
      "65/72 same-seven; crossover ~day 20 (patched faster on long "
      "runs: d24 189v131, d27 188v141, d33 179v140 bars/s). Merged "
      "as STABLE C-2 4c2df34d — on-disk hash recomputes exact, "
      "engine.py+swings.py == _scratch/perf/v2, 5-panel spot check "
      "byte-identical to K9 cache.")
    A("")
    A("## Tested and rejected this round (EVAL-AUDIT own scorer)")
    A("")
    A("| arm | hash | box@1 | level@1 | line@2 | clutter | margin | "
      "why |")
    A("|---|---|---|---|---|---|---|---|")
    for r in [
        ("bmday marker.day_extreme_only", "66f596dc",
         ".076 =", ".079 =", ".104 =", "5.00", "94 (+4)",
         "margin +4 < +5 (ink-only needs +5)"),
        ("ctcv loose (ctx_convert overlap)", "084caa52",
         ".101 +2", ".053 -4", ".088 -3", "5.00", "-",
         "level -4 > -1; suite 72/72 cannot rescue"),
        ("ctcv wraps (contains+<=2xw)", "3ca9097b",
         ".092 +1", ".092 -1", ".093 -2", "5.00", "-",
         "level -1 edge + line -2; suite 72/72"),
        ("lnsf42 line.slope_floor .25->.42", "ee2cbf12",
         ".084 =", ".092 -1", ".083 -4", "4.00", "120 (+6)",
         "line -4 on target fam; margin cannot rescue"),
        ("p_wick / wick_birth (BOX-LAB probe)", "81f7503f",
         "flat", "-", "-", "-", "-",
         "log_only bucket does not convert (orc .407, box@1 8/119, "
         "born/pan 1.52) — not pooled"),
        ("CONTEXT_LINE-while-PL-live (sim)", "-",
         "-", "-3", "-", "+8 margin sim", "-",
         "skipped: -3 hits in simulation"),
        ("LEVEL_CARRIED nearest-ahead (sim)", "-",
         "-", "-3", "-", "+3 margin sim", "-",
         "skipped: -3 hits in simulation"),
    ]:
        A("| %s | %s | %s | %s | %s | %s | %s | %s |" % r)
    A("")
    A("## Fixture debt carried (spec-vs-author conflict)")
    A("")
    A("- Suite 65/72 — the same seven named fixtures fail under "
      "fam_budget (CONTEXT_RANGE occupies the box-family live slot): "
      "pullback_end_box_birth, range_box_double_top, "
      "false_break_wick_keeps_edge, break_close_beyond_edge, "
      "tease_vs_proper_break_class, tf_relabel, "
      "reanchor_on_new_double_top. Documented in "
      "FIXTURE_CONFLICT.md; ctcv conversion-in-place cured all seven "
      "but cost level -4 (rejected). Decision is the Owner's.")
    A("")
    A("## Box gap — why C-2 ends 6 hits short of v0")
    A("")
    A("- BOX-LAB R1 census (119 box goldens): 10 hit, 16 below-min "
      "score, 11 outranked, 8 rate-limited, 2 expired, 10 log-only, "
      "62 no coverage. The dominant class is no-coverage, then "
      "selection losses (score/outrank/rate).")
    A("- R1 hypothesis table (107 wrong-pick pairs, label-shuffle "
      "nulls, seeds 56+777 identical): KEEP H5 recency (+14.4, but "
      "uses post-tau author t1_drawn — needs a causal proxy), H4 "
      "prior-leg +0.59, H10 tall +1.19, H6 height-ratio +0.014; "
      "thin: H1 press, H3 probes; DROP: H2 flat-EMA (reversed), H7 "
      "overlap, H8 wick-tip, H9 round-50.")
    A("- Density-matched null review (_null_review_c2.py): pivot "
      "coverage .711 does NOT beat null p95 .763 on the 38 no-edge "
      "goldens; trigger-window close-extremes .368 vs p95 .528 "
      "(drop). The C1 pivot-source claim does not survive the "
      "stronger null.")
    A("")
    A("## Status")
    A("")
    A("C-round 2 closed STABLE `%s` at ~15:01Z. Ruling 56 withdrew "
      "the freeze: 'Owner: machine is wrong on boxes -> research a "
      "different approach'. C-3 is a box research round; this pack "
      "records the C-2 end state as the new research parent. All "
      "numbers above are independently measured; the suite's seven "
      "failures are a spec-vs-author conflict pending the Owner." %
      STABLE)
    A("")

    out = os.path.join(HERE, "GATE_PACK_C2_%s.md" % STABLE[:8])
    open(out, "w", encoding="utf8").write("\n".join(L))
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
