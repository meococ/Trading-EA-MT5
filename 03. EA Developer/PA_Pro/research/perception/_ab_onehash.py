"""_ab_onehash.py — paired A/B at ONE engine hash (R24 §24.3).

Arms are module-level subclasses of PerceptionEngine that override params
in __init__ — no file edits, so both arms share code_hash(V1_FILES).
Classes must be module-level so CA.run pickles stay loadable.
Cache separation uses the `variant` key in cache.run (R14 §14.2).

Usage:
  python _ab_onehash.py tail      # tail_off vs tail_on
  python _ab_onehash.py marker    # marker_off vs marker_on vs marker_anchor

Report per arm: per-family matched counts (cumulative), snapshot recall,
LABEL_TF agreement n/N, live clutter @tau median, clutter ratio, births.
"""
import collections
import sys

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, _HERE)

import numpy as np

import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
import funnel as F
import engine as ENG
from snapshot import tau_of, live_records


_BASE = None


def _p(**overrides):
    # R36 §36.7: params are frozen per process — the file is read once,
    # never mid-run (a mid-invocation params flip contaminated
    # BOX-LAB's sweep with mixed hashes).
    global _BASE
    if _BASE is None:
        _BASE = ENG.load_params()
    import copy
    p = copy.deepcopy(_BASE)
    for path, v in overrides.items():
        node = p
        ks = path.split(".")
        for k in ks[:-1]:
            node = node[k]
        node[ks[-1]] = v
    return p


# Arm factories: zero-arg callables returning a plain PerceptionEngine
# (EV.run_engine calls cls()).  The returned object pickles as
# engine.PerceptionEngine, so caches stay loadable by any process —
# subclasses would pickle as __main__.X when run as a script.


def tail_off():
    return ENG.PerceptionEngine(params=_p())


def tail_on():
    return ENG.PerceptionEngine(params=_p(**{"box.tail_bars": 12}))


def marker_off():
    return ENG.PerceptionEngine(params=_p())


def marker_on():
    return ENG.PerceptionEngine(params=_p(
        **{"marker.day_extreme_only": True}))


def marker_anchor():
    return ENG.PerceptionEngine(params=_p(
        **{"marker.day_extreme_only": True,
           "marker.day_extreme_live_anchor_ok": True}))


def famledger_off():
    return ENG.PerceptionEngine(params=_p())


def famledger_on():
    return ENG.PerceptionEngine(params=_p(
        **{"salience.fam_ledger": True}))


def revive_on():
    return ENG.PerceptionEngine(params=_p(
        **{"salience.revive_exempt": True}))


def fambudget_off():
    return ENG.PerceptionEngine(params=_p())


def fambudget_on():
    return ENG.PerceptionEngine(params=_p(
        **{"salience.fam_budget": True}))


def labscore_off():
    return ENG.PerceptionEngine(params=_p())


def labscore_on():
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True}))


def lcpick_off():
    # parent = latest kept state (lab_score ON after the afba83c5 A/B)
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "salience.lc_score_pick": False}))


def lcpick_on():
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "salience.lc_score_pick": True}))


def boxrank_off():
    # parent = kept state (lab_score ON)
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "salience.box_prom_rank": False}))


def boxrank_on():
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "salience.box_prom_rank": True}))


def boxlab_off():
    # parent = kept state (lab_score ON)
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "box.rank_score": False,
           "salience.box_lab_score_use": False}))


def boxlab_on():
    # BOX-LAB hand-off: emit box_rank + use it as the box score.
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "box.rank_score": True,
           "salience.box_lab_score_use": True}))


def deforig_off():
    # parent = kept state (lab_score ON)
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "level.defended_origin": False,
           "level.def_mini_off": False}))


def deforig_on():
    # R37 §37.4: defended-origin LC route ON + defended MINIs off.
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "level.defended_origin": True,
           "level.def_mini_off": True}))


def lcpick2_off():
    # parent = kept state (lab_score + defended_origin + def_mini_off)
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "level.defended_origin": True,
           "level.def_mini_off": True, "salience.lc_score_pick": False}))


def lcpick2_on():
    # R37 §37.4: lc_score_pick on top of the defended-origin config.
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "level.defended_origin": True,
           "level.def_mini_off": True, "salience.lc_score_pick": True}))


_KEPT = {"line.lab_score": True, "level.defended_origin": True,
         "level.def_mini_off": True, "box.wick_edges": True,
         "box.dedup_iou": True, "box.rank_score": True,
         "salience.box_lab_score_use": True,
         "salience.fam_budget": True, "salience.fam_caps": True,
         "salience.box_score_pick": True, "line.slope_floor": 0.25,
         "box.cong_trigger": True, "box.cong_h_abr": 5.5,
         "marker.off": True, "box.cong_pivedge": True,
         "salience.rate_label_tf": 2}


def jointbud_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_total_live": 0}))


def jointbud_on():
    # R41 §41.4: step-down end point — author's joint live p90 = 2.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_total_live": 2}))


def jointbud3_on():
    # R41 §41.4: cap 3.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_total_live": 3}))


def jointbud4_on():
    # R41 §41.4: cap 4 — step down from the engine's current median.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_total_live": 4}))


def brcap_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.famcap_bracket": 0}))


def brcap_on():
    # R41 §41.4: BRACKET birth cap 2/panel (author p99; rate 0.44/panel
    # vs engine 1.77). CONTEXT_LINE already at its author max = 1 via
    # famcap_context_line.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.famcap_bracket": 2}))


def lnfloor_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.slope_floor": 0.0}))


def lnfloor_on():
    # R41 §41.4: slope floor 0.25 pips/bar = 3 p/hr on M5.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.slope_floor": 0.25}))


def lnsteep_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.steep_pick": False}))


def lnsteep_on():
    # R41 §41.4: steeper swing pair at equal touch score.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.steep_pick": True}))


def bxprio_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_prio": False}))


def bxprio_on():
    # R42 §42.4: spec's box priority inside the box family.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_prio": True}))


def bxtauprio_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_tau_prio": False}))


def bxtauprio_on():
    # R42 §42.4 narrowed: spec priority in the exposed tau ranking
    # only (no birth-path changes).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_tau_prio": True}))


def famoff_on():
    # R42 §42.5 fallback row: the kept config minus fam_budget +
    # fam_caps, measured at the same hash for the freeze choice.
    k = dict(_KEPT)
    k["salience.fam_budget"] = False
    k["salience.fam_caps"] = False
    return ENG.PerceptionEngine(params=_p(**k))


def famctx_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_context": False}))


def famctx_on():
    # R44 §44.2: CONTEXT_* as their own family, live budget 1.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_context": True}))


def famctx_nocr_on():
    # R44 §44.2 fallback: fam_context + CONTEXT_RANGE births OFF
    # (author ~0.08/day; v0 hit 0/6 at @1).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_context": True,
                    "salience.famcap_context_range": -1}))


def jstruct4_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.joint_struct": 0}))


def jstruct4_on():
    # R43 §43.4.2: structure-only joint cap = 4.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.joint_struct": 4}))


def jstruct3_on():
    # R43 §43.4.2: structure-only joint cap = 3.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.joint_struct": 3}))


def cong_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"box.cong_trigger": False}))


def cong_on():
    # R44 §44.3 hand-off at BOX-LAB's recommended k=5.5.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"box.cong_trigger": True, "box.cong_h_abr": 5.5}))


def cong40_on():
    # same hand-off at the default k=4.0.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"box.cong_trigger": True, "box.cong_h_abr": 4.0}))


def fcjs4_off():
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def fcjs4_on():
    # R45 §45.3.2: fam_context cures the box slot; joint cap 4 takes
    # the context ink back (context dropped first, reverse §5).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_context": True,
                    "salience.joint_struct": 4}))


def fcjs3_on():
    # R45 §45.3.2: same combo at cap 3.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_context": True,
                    "salience.joint_struct": 3}))


def ctxy_off():
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def ctxy_on():
    # R49 §49.4.2: yield not evict — standalone ctx_yield keeps
    # context inside the box family (shared live slot, no parallel
    # birth lane); the context incumbent hides for a prio-1 box.
    # REJECTED @fcd56aaf/99249af2: box +2 but level -3, clutter 5.67 —
    # score-blind yield unmasks suppressed box-cand demand (+282 BOX
    # births/60 panels via yield->birth->outrank->rebirth cycles).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ctx_yield": True}))


def ctxyf_on():
    # R49 §49.4.2 variant A (measured FAIL at a3742b16: level -3,
    # clutter 5.67): fam_context gives context a parallel lane.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.fam_context": True,
                    "salience.ctx_yield": True}))


def bmoff_on():
    # R50 §50.2 ink-only arm: BAR_MARKER fully suppressed — the
    # biggest zero-M1-hit ink on marginal panels (117 objs / 34
    # panels); removal sim: panels<=5.0 90->126.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"marker.off": True}))


def bmday_on():
    # R50 §50.2 gentler variant: markers only on named day extremes
    # (R22 lever, previously rejected on the old metric at PL -2).
    # REJECTED @66f596dc: +4 panels <=5.0 (94 vs 90) < +5, M1 flat.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"marker.day_extreme_only": True}))


def pedg_off():
    # R50 §50.2.4 headroom parent: kept defaults incl. marker.off.
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def pedg_on():
    # R50 §50.2.4: BOX-LAB hand-off on the headroom parent — best arm
    # is the implementation defaults (npairs=6, top-4 clusters,
    # emit-on-change memo).  Failed §34.5 leg 3 on the old parent
    # (clutter 5.33); headroom parent starts at 4.67.
    # KEPT @be4eea26: box +1, level +1, clutter 4.67 unchanged.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"box.cong_pivedge": True}))


def ctcv_off():
    # R51 §51.4.2 parent: kept defaults (marker.off + cong_pivedge).
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def ctcv_on():
    # R51 §51.4.2 conversion-in-place: a CONTEXT_RANGE meeting a
    # priority-1 box candidate becomes that box (asia_convert
    # precedent) — zero net births, unlike the rejected ctx_yield
    # hide/restore cycle.
    # REJECTED twice (stop rule 3.7): loose gate level-4/line-3,
    # wraps gate level-1/line-2, both @84/3ca9.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ctx_convert": True}))


def ltfcap_off():
    # B3(i) parent: kept defaults (marker.off + cong_pivedge).
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def lnsf42_off():
    # B.S(a) parent: kept defaults incl. rate_label_tf.
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def lnsf42_on():
    # B.S(a) line-slope realism: raise slope_floor 0.25 -> 0.42 p/bar
    # (5 pips/h; author median 9.2 p/h vs engine 5.24).  Value stated
    # pre-A/B per s.3.6: ~54% of the author median, above engine p25.
    # Post-hoc sim removes flat lines without refilling slots, so its
    # -8 hits is the pessimistic bound; live births re-spend the slot.
    k = dict(_KEPT); k["line.slope_floor"] = 0.42
    return ENG.PerceptionEngine(params=_p(**k))


def lvs_off():
    # R56 A1 parent: kept defaults (K1-K9 + F1 perf).
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def lvs_on():
    # R56 §56.4 A1 hand-off (BOX-LAB spec in REQUESTS.md): a BOX cand
    # may take the slot only if current — cand.t1 >= now-30 bars.
    # Stale cands stay in the pool, just ineligible.  Score order
    # unchanged among current cands.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_live_scope": 30}))


def yng_off():
    # A1v2 parent: kept defaults.
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def yng_on():
    # R56 A1 variant-2 (dataset counterfactual 15/119): within the
    # box family's own birth-order positions, the youngest cand
    # (max t0, tiebreak touches) leads.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_young_first": True}))


def lvb_on():
    # R56 A3-rule arm: BOX cand births only while close is inside its
    # band or within 0.5*ABR of an edge (liveness gate at birth).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_live_at_birth": True}))


def a4_on():
    # R58 §58.3 A4: box-family slot admits by liveness order — a
    # CURRENT (K=30 via box_live_scope) + LIVE (in-band/edge 0.5 ABR)
    # BOX cand evicts a NON-LIVE box-family incumbent, no margin/dwell.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_live_birth": True}))


def a4b_on():
    # A4v2: asymmetric liveness — cand qualifies by close_at_box
    # (inside or edge<=0.5 ABR); incumbent defends only while price is
    # AT its edge.  Targets the 80/115 CONTEXT_RANGE-held cells: an
    # envelope merely containing price mid-band is not interaction.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_edge_birth": True}))


def evb_on():
    # R61 s.61.4 event-route port, BOX-LAB spec default: on each
    # confirmed SwingBook pivot, v0's two routes (ev_range_double_*
    # preferred, then ev_pullback_end) PROPOSE a BOX into the pool -
    # v1's budget/lifecycle admits and governs it (no v0 governing
    # veto); the best-SCORING live event box takes box-family rank-1
    # (+100 exposed); incumbent CONTEXT_RANGE stays live as the
    # level/line carrier.  MEASURED @65c8f635: INERT (0 born - the
    # admission funnel kills event cands identically to right cands).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_route_box": True}))


def evb2_on():
    # Variant 2 (route restriction): pullback_end OFF, double-only.
    # MEASURED @b07b8af4 under the pre-spec direct-birth design:
    # box 7/119 (-3), clutter 5.67, margin 80/179, flips +6/-8 -> FAIL.
    # (Under the spec-default code it would now mean double-only
    # PROPOSALS into the pool; not re-run - mechanism closed s.3.7.)
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_route_box": True,
                    "salience.ev_route_pullback": False}))


def uip_on():
    # R62 s.62.4 T1/UIP-rd (BOX-LAB spec REQUESTS.md s.19): throttled
    # event birth - the event family holds ONE live object; the first
    # non-shadowed route cand births it directly; later
    # range_double_* cands rewrite (lo,hi,t0) in place; pullback_end
    # never writes.  WIN 600, MIN_SEP 8, PB_SEP 8, DTOL 2.0p,
    # envelope 6-34p, dedup max(1p,.25*ABR), cooldown 10b at birth.
    # MEASURED @6d955783: box 7/119(-3) level 4/76(-4) line 22/193(+2)
    # clutter 4.50, births 1.0/panel, suite 71/72 -> FAIL 3.1a
    # (object outranked ~6 bars post-birth; family spent -> near-inert
    # coverage but span ink still charged).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_uip": True}))


def uip2_on():
    # R62 s.62.4 T1 variant 2 (sim-faithful reading): the ONE event
    # object is exempt from every kill path (close veto) so the
    # range_double_* rewrite stream keeps mutating its edges - the
    # economy BOX-LAB's offline tally assumed (5/15 on final edges).
    # MEASURED @6d955783: box 16/119(+6=V0 PARITY .134) level 4/76(-4)
    # line 23/193(+3) clutter 4.67 margin95/179 births1.0/panel
    # live9.0@tau flips+19/-14 suite71/72 -> FAIL 3.1b (level -4).
    # First arm to reach v0 box parity at ink-1; the cost moved to
    # joint-cap crowding (permanent box slot -> CR births 189v195 ->
    # level carriers die early).  Frontier is now box<->level.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_uip": True,
                    "salience.ev_uip_persist": True}))


def uip2_lvfree():
    # R66 s.66.3 V1: uip2_on + level decoupling - the UIP object's
    # edges never seed level cands (levels.spawn lvfree_seed_veto) and
    # it is exempt from every shared/joint cap or slot that can block
    # or evict a level (class budget, budget_hard, fam_total_live,
    # joint_struct incl. victim pick).  Box ink only.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_uip": True,
                    "salience.ev_uip_persist": True,
                    "salience.ev_uip_lvfree": True}))


def uip2_lvfree_pb():
    # R66 s.66.3 V2: V1 + UIP-all - pullback_end cands also rewrite
    # the ONE object's (lo,hi,t0).  DR-BOX: +2 edge-exact vs rd-only;
    # expected to cure test_pullback_end_box_birth.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_uip": True,
                    "salience.ev_uip_persist": True,
                    "salience.ev_uip_lvfree": True,
                    "salience.ev_uip_pb_write": True}))


def uip2_pbbirth():
    # R68 s.68.3 V3: uip2_lvfree + pullback_end cand may BIRTH the UIP
    # object at v0's route gate (idx - t0a >= 3) while the panel has
    # none; rewrites stay rd-only after birth.  Targets the one
    # blocking fixture test_pullback_end_box_birth.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_uip": True,
                    "salience.ev_uip_persist": True,
                    "salience.ev_uip_lvfree": True,
                    "salience.ev_uip_pb_birth": True}))


def uip2_bs():
    # R66 s.66.4: uip2_lvfree_pb + episode-anchored meta_build_start on
    # the UIP object (walk-back over band-overlapping bars from cand t0,
    # capped at bar_of(w0); recomputed at every rewrite; drawn span
    # unchanged).  Spec expects +0..+5 box on rule-hit cells.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.ev_uip": True,
                    "salience.ev_uip_persist": True,
                    "salience.ev_uip_lvfree": True,
                    "salience.ev_uip_pb_write": True,
                    "salience.ev_uip_buildstart": True}))


def l1_close():
    # R73 s.73.2 L-1 V1: defended-veto relaxes to close-only (wick pokes
    # are teases; only an in-span close > tol*omul beyond the line
    # rejects) + young_a ordering at both selection points.  C-3
    # defaults otherwise.  Target: line@2 >= 21/193.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.over_veto_mode": "close_only",
                    "line.rank": "young_a"}))


def l1_soft():
    # R73 s.73.2 L-1 V2: defended-veto removed at birth (overshoot
    # remains a lab_score penalty, nt - 0.5*over_all/tol) + young_a
    # ordering at both selection points.  Target: line@2 >= 21/193.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.over_veto_mode": "soft",
                    "line.rank": "young_a"}))


def l3_ink():
    # R73 s.73.2 L-3 V1: qualifying re-anchor closes the incumbent
    # (residual ink) and the challenger births as a sibling - revision
    # is new ink, not silent mutation.  Target: line up, clutter <=5.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.reanchor_ink": True}))


def l3_revise():
    # R73 s.73.2 L-3 V2: in-place re-anchor kept + explicit 'revise'
    # event carrying old+new geometry.  INFO - objects unchanged.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.reanchor_log": "revise"}))


def l4_snap():
    # R73 s.73.2 L-4 V1 (INFO): anchor prices snapped to 0.5*tol grid
    # before pairing.  Value is stability (M3), not M1 recall.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"line.anchor_snap": 0.5}))


def l4_promsnap():
    # R73 s.73.2 L-4 V2 (INFO): prominence on snapped prices upstream -
    # touches swings boxes also use; report all three families.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"swing.prom_snap": True}))


def l2_near():
    # R73 s.73.2 L-2 V1: level births only from the NEAREST same-side
    # n_def>=2 defended origin to the close.  Target: level@1 >= 8/76.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"level.def_nearest": True}))


def l2_near_ret24():
    # R73 s.73.2 L-2 V2: V1 + a defence touch within def_ret24_bars=24
    # is required (the defended edge must be freshly defended).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"level.def_nearest": True,
                    "level.def_ret24_req": True}))


def v0box_on():
    # R63 s.63.4 option-B (PREPARED only - DO NOT RUN until the Owner
    # picks option B; R64 defers the choice pending DR-BOX).  A verbatim
    # engine_v0 sub-engine runs alongside on the same bar stream and
    # supplies the whole box family (BOX + RANGE_OPEN births, v0
    # lifecycle, v0 ranking); its objects are mirrored into e.objects
    # without _act registration, and v1's own box-kind cands are
    # suppressed in salience.round.  Equivalent to the R60 hybrid
    # (box 16/119 level 8/76 line 20/193 clutter 5.67) but in-engine.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_v0_family": True}))


def ltfcap_on():
    # B3(i) ink-only arm: LABEL_TF day-window cap.  marker.off emptied
    # the annot lane -> labels flooded 189->616 (golden marks p90=1,
    # max 3 per panel).  Cap 2 per context_window_bars, set by golden
    # density + the rate_context=2/day precedent (stated pre-A/B,
    # s.3.6).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.rate_label_tf": 2}))


def famoff_nosup_on():
    # R42 §42.5: famoff row without K4 — the supersede lives in the
    # rate-blocked branch, so its contribution is measured both ways.
    k = dict(_KEPT)
    k["salience.fam_budget"] = False
    k["salience.fam_caps"] = False
    k["salience.box_score_pick"] = False
    return ENG.PerceptionEngine(params=_p(**k))


def bxpair_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"box.wick_edges": False, "box.dedup_iou": False}))


def bxpair_on():
    # R38 §38.3 hand-off: wick_edges + dedup_iou as ONE coverage pair.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"box.wick_edges": True, "box.dedup_iou": True}))


def bxcombo_off():
    return ENG.PerceptionEngine(params=_p(**_KEPT))


def bxcombo_on():
    # R38 §38.4: coverage pair + best box selector (lab rank) +
    # fam_budget family segregation so box_rank cannot evict levels.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"box.wick_edges": True, "box.dedup_iou": True,
                    "box.rank_score": True,
                    "salience.box_lab_score_use": True,
                    "salience.fam_budget": True,
                    "salience.fam_caps": True}))


def lvltr_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.level_touch_rec": False}))


def lvltr_on():
    # R38 §38.5: touches x recency level score on kept parent.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.level_touch_rec": True}))


def lndedup_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.line_dedup_merge": False}))


def lndedup_on():
    # R38 §38.5: merge duplicate lines before the line budget.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.line_dedup_merge": True}))


def bxsup_off():
    # parent = kept state (defaults at 22888182 carry all keeps)
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_score_pick": False,
                    "salience.box_score_pick_prio": False}))


def bxsup_on():
    # R40 §40.3 arm A: box supersede on score alone.
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_score_pick": True,
                    "salience.box_score_pick_prio": False}))


def bxsupp_off():
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_score_pick": True,
                    "salience.box_score_pick_prio": False}))


def bxsupp_on():
    # R40 §40.3 arm B: + spec priority-1 gate (contains price vs left).
    return ENG.PerceptionEngine(params=_p(
        **_KEPT, **{"salience.box_score_pick": True,
                    "salience.box_score_pick_prio": True}))


def _boxarm(flag, val):
    # BOX-LAB hand-off pairs (boxlab/REQUESTS.md) on the kept parent.
    def f():
        o = {"line.lab_score": True, "level.defended_origin": True,
             "level.def_mini_off": True, "box." + flag: val}
        return ENG.PerceptionEngine(params=_p(**o))
    return f


def famv2_off():
    # parent = kept state (lab_score ON)
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True}))


def famv2_on():
    # R36 §36.3: fam_budget + per-panel caps at the author's own
    # TUNE count for the returning kinds.
    return ENG.PerceptionEngine(params=_p(
        **{"line.lab_score": True, "salience.fam_budget": True,
           "salience.fam_caps": True}))


ARMS = {"tail_off": tail_off, "tail_on": tail_on,
        "marker_off": marker_off, "marker_on": marker_on,
        "marker_anchor": marker_anchor,
        "famledger_off": famledger_off, "famledger_on": famledger_on,
        "revive_on": revive_on,
        "fambudget_off": fambudget_off, "fambudget_on": fambudget_on,
        "labscore_off": labscore_off, "labscore_on": labscore_on,
        "lcpick_off": lcpick_off, "lcpick_on": lcpick_on,
        "boxrank_off": boxrank_off, "boxrank_on": boxrank_on,
        "famv2_off": famv2_off, "famv2_on": famv2_on,
        "boxlab_off": boxlab_off, "boxlab_on": boxlab_on,
        "deforig_off": deforig_off, "deforig_on": deforig_on,
        "lcpick2_off": lcpick2_off, "lcpick2_on": lcpick2_on,
        "bxleg_off": _boxarm("leg_edges", False),
        "bxleg_on": _boxarm("leg_edges", True),
        "bxwick_off": _boxarm("wick_edges", False),
        "bxwick_on": _boxarm("wick_edges", True),
        "bxdense_off": _boxarm("dense_anchors", False),
        "bxdense_on": _boxarm("dense_anchors", True),
        "bxdedup_off": _boxarm("dedup_iou", False),
        "bxdedup_on": _boxarm("dedup_iou", True),
        "bxwatch_off": _boxarm("watch_birth", False),
        "bxwatch_on": _boxarm("watch_birth", True),
        "bxtail_off": _boxarm("tail_bars", 0),
        "bxtail_on": _boxarm("tail_bars", 12),
        "bxpair_off": bxpair_off, "bxpair_on": bxpair_on,
        "bxcombo_off": bxcombo_off, "bxcombo_on": bxcombo_on,
        "lvltr_off": lvltr_off, "lvltr_on": lvltr_on,
        "lndedup_off": lndedup_off, "lndedup_on": lndedup_on,
        "bxsup_off": bxsup_off, "bxsup_on": bxsup_on,
        "bxsupp_off": bxsupp_off, "bxsupp_on": bxsupp_on,
        "jointbud_off": jointbud_off, "jointbud_on": jointbud_on,
        "jointbud3_on": jointbud3_on, "jointbud4_on": jointbud4_on,
        "brcap_off": brcap_off, "brcap_on": brcap_on,
        "lnfloor_off": lnfloor_off, "lnfloor_on": lnfloor_on,
        "lnsteep_off": lnsteep_off, "lnsteep_on": lnsteep_on,
        "bxprio_off": bxprio_off, "bxprio_on": bxprio_on,
        "bxtauprio_off": bxtauprio_off, "bxtauprio_on": bxtauprio_on,
        "famoff_on": famoff_on, "famoff_nosup_on": famoff_nosup_on,
        "famctx_off": famctx_off, "famctx_on": famctx_on,
        "famctx_nocr_on": famctx_nocr_on,
        "jstruct4_off": jstruct4_off, "jstruct4_on": jstruct4_on,
        "jstruct3_on": jstruct3_on,
        "cong_off": cong_off, "cong_on": cong_on,
        "cong40_on": cong40_on,
        "fcjs4_off": fcjs4_off, "fcjs4_on": fcjs4_on,
        "fcjs3_on": fcjs3_on,
        "ctxy_off": ctxy_off, "ctxy_on": ctxy_on,
        "ctxyf_on": ctxyf_on,
        "bmoff_on": bmoff_on, "bmday_on": bmday_on,
        "pedg_off": pedg_off, "pedg_on": pedg_on,
        "ctcv_off": ctcv_off, "ctcv_on": ctcv_on,
        "ltfcap_off": ltfcap_off, "ltfcap_on": ltfcap_on,
        "lnsf42_off": lnsf42_off, "lnsf42_on": lnsf42_on,
        "lvs_off": lvs_off, "lvs_on": lvs_on,
        "yng_off": yng_off, "yng_on": yng_on,
        "lvb_off": yng_off, "lvb_on": lvb_on,
        "a4_off": yng_off, "a4_on": a4_on,
        "a4b_off": yng_off, "a4b_on": a4b_on,
        "evb_off": yng_off, "evb_on": evb_on,
        "evb2_on": evb2_on, "uip_on": uip_on, "uip2_on": uip2_on,
        "v0box_off": yng_off, "v0box_on": v0box_on,
        "uip2_lvfree": uip2_lvfree, "uip2_lvfree_pb": uip2_lvfree_pb,
        "uip2_bs": uip2_bs, "uip2_pbbirth": uip2_pbbirth,
        "l1_close": l1_close, "l1_soft": l1_soft,
        "l2_near": l2_near, "l2_near_ret24": l2_near_ret24,
        "l3_ink": l3_ink, "l3_revise": l3_revise,
        "l4_snap": l4_snap, "l4_promsnap": l4_promsnap}


def measure(eng_hash, cls, variant):
    recs = C.load_tune()
    hit_g = collections.Counter()
    gold_n = collections.Counter()
    eng_n = collections.Counter()
    born_kind = collections.Counter()
    clutter = []
    ratio = []
    ll_cands = []   # R73 s.73.2: line+level cands entering salience / panel
    snap_g = collections.Counter()
    snap_h = collections.Counter()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec, variant=variant)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        pairs, _mp = C.match_panel(g2, eboxes, [], [], m,
                                   V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        for gi, g in enumerate(g2):
            gold_n[g["spec_type"]] += 1
            hit_g[g["spec_type"]] += gi in hg
        for er in eboxes:
            eng_n[er["type"]] += 1
        n_ll = 0
        for cd in e.cand_log or []:
            if cd.get("outcome") == "born":
                born_kind[cd["kind"]] += 1
            if cd.get("kind") in ("PATTERN_LINE", "CONTEXT_LINE",
                                  "LEVEL_CARRIED", "MINI_LEVEL"):
                n_ll += 1
        ll_cands.append(n_ll)
        if g2:
            ratio.append(len(eboxes) / len(g2))
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            by_tau[min(tau, w1)].append(g)
        for gm in gmarks:
            if gm.get("t") is not None and w0 <= gm["t"] <= w1:
                by_tau[gm["t"]].append(gm)
        for tau, gs in by_tau.items():
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t, variant=variant)
            eboxes_t, emarks_t = live_records(e_t, m, w0, tau)
            clutter.append(len(eboxes_t))
            for g in gs:
                if g.get("spec_type") is None:      # mark record
                    snap_g["LABEL_TF"] += 1
                    snap_h["LABEL_TF"] += any(
                        V2.match_mark(g, em) for em in emarks_t)
                    continue
                st = g["spec_type"]
                snap_g[st] += 1
                snap_h[st] += any(V2.match(g, er, m) for er in eboxes_t)
    return {"hit_g": hit_g, "gold_n": gold_n, "eng_n": eng_n,
            "born": born_kind, "clutter": clutter, "ratio": ratio,
            "ll_cands": ll_cands,
            "snap_g": snap_g, "snap_h": snap_h}


def report(tag, r):
    print("\n=== arm %s ===" % tag)
    for st in sorted(r["gold_n"]):
        g, h = r["gold_n"][st], r["hit_g"][st]
        sg, sh = r["snap_g"][st], r["snap_h"][st]
        print("  %-14s cum %3d/%-3d = %.3f   snap %3d/%-3d = %.3f"
              % (st, h, g, h / g if g else 0,
                 sh, sg, sh / sg if sg else 0))
    sg, sh = r["snap_g"]["LABEL_TF"], r["snap_h"]["LABEL_TF"]
    print("  LABEL_TF agreement %d/%d" % (sh, sg))
    print("  births:", dict(r["born"].most_common()))
    print("  engine objs:", dict(r["eng_n"].most_common()))
    print("  live clutter@tau med %.2f | ratio med %.3f p90 %.3f"
          % (np.median(r["clutter"]), np.median(r["ratio"]),
             np.percentile(r["ratio"], 90)))
    print("  line+level cands/panel (pre-salience): med %d max %d"
          % (np.median(r["ll_cands"]), max(r["ll_cands"])))


def main():
    eng_hash = F.code_hash(F.V1_FILES)
    print("engine hash %s (one hash for every arm)" % eng_hash)
    which = sys.argv[1] if len(sys.argv) > 1 else "tail"
    if which == "tail":
        names = ["tail_off", "tail_on"]
    elif which == "marker":
        names = ["marker_off", "marker_on", "marker_anchor"]
    elif which == "famledger":
        names = ["famledger_off", "famledger_on"]
    elif which == "uip":
        names = ["evb_off", "uip_on", "uip2_on"]
    elif which == "v0box":
        # R63 s.63.4 option-B: prepared only - run ONLY on the
        # Owner's explicit option-B authorization (R64 defers choice).
        names = ["v0box_off", "v0box_on"]
    elif which == "lvfree":
        # R66 s.66.3: level decoupling on the uip2 base - off parent,
        # the uip2_on base (for the delta), V1 and V2.
        names = ["evb_off", "uip2_on", "uip2_lvfree", "uip2_lvfree_pb"]
    elif which == "bs":
        # R66 s.66.4: episode-anchored meta_build_start on top of the
        # lvfree_pb arm - parent + the immediate base for the delta.
        names = ["evb_off", "uip2_lvfree_pb", "uip2_bs"]
    elif which == "pbbirth":
        # R68 s.68.3 V3: pb-cand may birth the UIP object at v0's route
        # gate.  Parent + the V1 base (the arm V3 modifies).
        names = ["evb_off", "uip2_lvfree", "uip2_pbbirth"]
    elif which == "l1":
        # R73 s.73.2 L-1: defended-veto modes + young_a ordering.
        # evb_off = C-3 parent row (defaults), then V1 and V2.
        names = ["evb_off", "l1_close", "l1_soft"]
    elif which == "l2":
        # R73 s.73.2 L-2: nearest-defended-origin level births.
        names = ["evb_off", "l2_near", "l2_near_ret24"]
    elif which == "l3":
        # R73 s.73.2 L-3: revision as ink (V1) + revise event (V2,
        # INFO - objects unchanged by design).
        names = ["evb_off", "l3_ink", "l3_revise"]
    elif which == "l4":
        # R73 s.73.2 L-4: zone-stable anchors.  INFO only (M3 pending).
        names = ["evb_off", "l4_snap", "l4_promsnap"]
    else:
        names = ["tail_off"]
    for nm in names:
        print("arm %s ..." % nm, flush=True)
        report(nm, measure(eng_hash, ARMS[nm], nm))


if __name__ == "__main__":
    main()
