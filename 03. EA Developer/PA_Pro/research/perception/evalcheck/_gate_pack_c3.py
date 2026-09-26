"""_gate_pack_c3.py — build GATE_PACK_C3_<hash>.md for the C-round-3
close (R68 s.68.4 / R70 s.70.2): STABLE C-3 1a5502129b4c1554 = C-2 +
keep uip2_pbbirth (folded to params_v1_1.json defaults).

M1 table vs v0 with paired day-boot CIs, clutter median + margin,
option-C live-at-tau rows, suite of record, flip lists, keep chain,
and a one-screen status.  Everything measured by this lane's own
scorer (m1_row.py) off the A/B cache.

Usage:
  python evalcheck/_gate_pack_c3.py
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

STABLE = "1a5502129b4c1554"
ARM_H = "8361fe85e73f9437"
ARM_V = "uip2_pbbirth"
PARENT = "4c2df34d7a2a8ee3"
PARENT_H = "ee2cbf1202db47b6"
PARENT_V = "c1r_p_base"


def main():
    recs = C.load_tune()
    import random
    rng = random.Random(M.SEED)
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%MZ")

    with pa_slots.slot("evalcheck-gatepack-c3", timeout=1800):
        h0 = F.code_hash(F.V0_FILES)
        v0 = M.measure(h0, "m1_v0", recs)
        cand = M.measure(ARM_H, ARM_V, recs)
        par = M.measure(PARENT_H, PARENT_V, recs)

    d_c = M.diag_line(cand["diag"])
    d_p = M.diag_line(par["diag"])
    d_0 = M.diag_line(v0["diag"])

    import _gate_pack_c1 as G
    rows = G.md_fam(cand, v0, rng)

    L = []
    A = L.append
    A("# GATE_PACK_C3 — C-round-3 close pack (EVAL-AUDIT)")
    A("")
    A("Generated %s by EVAL-AUDIT's own scorer (m1_row.py), TUNE 198 "
      "panels, ruler `50e11fd5a2ab7974`." % now)
    A("")
    A("STABLE C-3: `%s` = STABLE C-2 `%s` + keep `uip2_pbbirth` "
      "(folded into params_v1_1.json defaults: salience.ev_uip, "
      "ev_uip_persist, ev_uip_lvfree, ev_uip_pb_birth = True; "
      "pb_write/buildstart/box_v0_family stay OFF). The measured row "
      "below is `uip2_pbbirth@%s`; the folded default engine was "
      "verified byte-identical to it on all 198 TUNE panels "
      "(objects+cand_log+events, evalcheck/_c3_freeze_check.py)." % (
          STABLE, PARENT[:8], ARM_H[:8]))
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
    A("| STABLE C-3 | %.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s | "
      "%.3f (%d/%d) %+.3f %s | %.3f (%d/%d) %+.3f %s |" % (
          parts["box"][0], parts["box"][1], parts["box"][2],
          parts["box"][3], parts["box"][4],
          parts["level"][0], parts["level"][1], parts["level"][2],
          parts["level"][3], parts["level"][4],
          parts["line"][0], parts["line"][1], parts["line"][2],
          parts["line"][3], parts["line"][4],
          parts["bracket"][0], parts["bracket"][1], parts["bracket"][2],
          parts["bracket"][3], parts["bracket"][4]))
    pr = {fam: (v, hh2, gg2) for fam, k, v, hh2, gg2, vv, hv, gv, dd,
          ci in G.md_fam(par, v0, rng)}
    A("| C-2 parent | %.3f (%d/%d) | %.3f (%d/%d) | %.3f (%d/%d) | "
      "%.3f (%d/%d) |" % (
          pr["box"][0], pr["box"][1], pr["box"][2],
          pr["level"][0], pr["level"][1], pr["level"][2],
          pr["line"][0], pr["line"][1], pr["line"][2],
          pr["bracket"][0], pr["bracket"][1], pr["bracket"][2]))
    A("")
    A("† bracket@1 reported, not part of M1. CIs are paired "
      "day-bootstrap of (arm − v0), seed %d, 1000 resamples." % M.SEED)
    A("")
    A("## Clutter + diagnostics (STABLE C-3)")
    A("")
    A("- today's def (window census): clutter ratio median **%.2f** "
      "(parent %.2f, v0 %.2f); %d/%d scored panels <= 5.0 "
      "(parent %d)" % (
          d_c["clutter_med"], d_p["clutter_med"], d_0["clutter_med"],
          sum(1 for x in d_c["ratios"] if x <= 5.0),
          len(d_c["ratios"]),
          sum(1 for x in d_p["ratios"] if x <= 5.0)))
    A("- BOX recall %.3f | BOX precision %.3f | PATTERN_LINE recall "
      "%.3f | LEVEL_CARRIED recall %.3f | LABEL_TF agreement %d/%d" % (
          d_c["BOX_rec"], d_c["BOX_prec"], d_c["PL_rec"],
          d_c["LC_rec"], d_c["tf"][0], d_c["tf"][1]))
    A("- event-route births: exactly 1.0/panel | live box-family "
      "objects at window end: med 2.0 (parent 1.0)")
    A("")
    A("## Option-C row (information only; ruler unchanged)")
    A("")
    A("Live-at-τ clutter (_live_clutter_c3.py; STRICT = ACTIVE at τ, "
      "LOOSE = not-DELETED):")
    A("")
    A("| arm | strict med | strict margin | loose med | loose margin |")
    A("|---|---|---|---|---|")
    A("| C-2 parent | 2.00 | 166/179 | 3.50 | 128/179 |")
    A("| v0 | 2.67 | 150/179 | 6.83 | 53/179 |")
    A("| hybrid v1+v0box | 2.00 | 167/179 | 4.25 | 111/179 |")
    A("| **STABLE C-3 (uip2_pbbirth)** | **2.33** | **163/179** | "
      "**3.89** | **125/179** |")
    A("")
    A("## Suite of record (unmodified research/perception/tests/, "
      "72 collected)")
    A("")
    A("- **STABLE C-3 params: 72/72 PASS** — `test_pullback_end_"
      "box_birth` cured (pb candidate births the UIP object at v0's "
      "route gate idx−t0a≥3); the six other named fixtures stay cured "
      "by the lvfree decoupling.")
    A("- C-2 parent params at same tree: 65/72 (the named seven).")
    A("- Build's earlier \"67/67\" was a wrong-directory collection "
      "(PA_Pro/tests/, EA-exec suite), corrected by build 03:56Z; the "
      "72-test perception suite is the suite of record (R68 s.68.2).")
    A("")
    A("## Flipped box-family goldens vs C-2 parent (rank-1 hit)")
    A("")
    A("- gained 15: 9.11a(CONTEXT_RANGE) 9.13a 9.15b(t900) 9.17a "
      "9.18a 9.27a 9.32a(t478) 9.32a(t510) 9.34a 9.41b 9.44b "
      "9.45a(t350) 9.58a 9.61b 9.7b")
    A("- lost 9: 9.14a(RANGE_OPEN) 9.15b(t895) 9.25b 9.2b 9.36b "
      "9.39a 9.45b 9.48b 9.4b")
    A("- level flips vs parent: +1 (9.5c) / −2 (9.49a, 9.56b) = net −1")
    A("")
    A("## Keep chain + identity")
    A("")
    A("- C-3 = C-2 (9acaa206 + K7 + K8 + K9 + F1) + uip2_pbbirth. "
      "OFF-identity evb_off@8361fe85 vs c1r_p_base@ee2cbf12: "
      "1728/1728 objects+cand_log+events canonical identical "
      "(141 unshared rows).")
    A("- Snapshot `_scratch/freeze_candidates/1a5502129b4c1554/` "
      "recomputes to the stable hash exactly (kernel.py excluded — it "
      "postdates the fold, added to V1_FILES during ARCH migration "
      "A1).")
    A("- Post-freeze ARCH migration A1 (kernel.py extraction, "
      "18ea3147+) verified identity-clean on all 198 TUNE panels vs "
      "the measured arm — same pass that confirmed the params fold.")
    A("")
    A("## Status")
    A("")
    A("C-round 3 closed STABLE `%s` at ~04:17Z. First config in the "
      "programme meeting M1 on all three families at the author's "
      "ink (box ties v0 exactly — zero box margin). The suite of "
      "record is fully green. Pending: Owner's Decision-C next steps "
      "(human-ceiling kit, M2 blind-precision pack on this STABLE); "
      "ARCH Phase A refactor proceeds step-by-step under OFF≡parent "
      "identity checks; BOX-LAB §67.4 reach channel; DR-LINE essence "
      "research (R69)." % STABLE)
    A("")

    out = os.path.join(HERE, "GATE_PACK_C3_%s.md" % STABLE[:8])
    open(out, "w", encoding="utf8").write("\n".join(L))
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
