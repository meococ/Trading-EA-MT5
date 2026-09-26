"""DR_RULES_S1_md.py — render DR_RULES_S1.md from
DR_RULES_S1_summary.json.  Writes only deepresearch/DR_RULES_S1.md.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "DR_RULES_S1_summary.json")))


def f2(x):
    return "NA" if x is None else "%.2f" % x


def f1(x):
    return "NA" if x is None else "%.1f" % x


P = []
A = P.append

A("# DR-RULES-S1 — box shape transforms (R78 §78.4(2))")
A("")
A("Read-only estimate on the canonical C-3 arm (`uip2_pbbirth")
A("@8361fe85e73f9437`, 623 windows, 456 golden-decision τ events).")
A("Same replay path as DR-RULES Part D: `snapshot.live_records` +")
A("`recall_at_k.rank_live` on cached pickles, per-family budgets")
A("(box@1 line@2 level@1 bracket@1).  Every live BOX object at every")
A("golden-decision τ gets the transform; the transformed object sits")
A("in the same pick slot; ranking/scores untouched.  Written 09:33Z.")
A("")
A("## Arms (fixed, no tuning)")
A("")
A("- **S1-a left-edge reset.** t_left → first bar after the last")
A("  impulse run (≥4·ABR20 net move within ≤6 consecutive")
A("  same-direction bars) or shock bar (range ≥3·ABR20) inside the")
A("  drawn span [t_left, τ].  Edges unchanged.  If fewer than 3 bars")
A("  remain, the object is dropped (freed slot refilled by the")
A("  next-ranked box).")
A("- **S1-b age cap.** t_left → max(t_left, τ − 75 bars) — the")
A("  author's drawn-width q95 from DR-RULES (75.4 bars ≈ 377 min,")
A("  applied as 375 min).  Edges unchanged; never drops.")
A("")
A("Both transforms use bars ≤ τ only.  Prefix invariance: %d/%d "
  "identical reset points when computed on the τ-clipped pickle vs"
  " the full-window pickle truncated to τ (20 panels)." % (
    S["prefix"]["same"], S["prefix"]["n"]))
A("")
A("## 1. Hits and keep rule")
A("")
A("| arm | box hits | line | level | bracket | clutter (census) | keep rule |")
A("|---|---|---|---|---|---|---|")
A("| parent | 16 | 20 | 7 | 29 | %.2f | — |" % S["census"]["0"][0])
ka = "FAIL (box 15<16)" if S["hits"]["a"] < 16 else "pass"
kb = "PASS" if (S["hits"]["b"] >= 16 and S["census"]["b"][0] <= 5.0) \
    else "FAIL"
A("| S1-a reset | %d (−%d, +%d) | 20 | 7 | 29 | %.2f | %s |" % (
    S["hits"]["a"], S["lost"]["a"], S["gained"]["a"],
    S["census"]["a"][0], ka))
A("| S1-b age cap | %d (−%d, +%d) | 20 | 7 | 29 | %.2f | %s |" % (
    S["hits"]["b"], S["lost"]["b"], S["gained"]["b"],
    S["census"]["b"][0], kb))
A("")
A("Non-box hits were recomputed, not assumed: line 20, level 7,")
A("bracket 29 under both arms (only box records are transformed,")
A("per-family budgets make the rest identical by construction).")
A("Clutter = published census (objects visible in window ÷ scorable")
A("goldens, panel median).  S1-b never drops → 4.33; S1-a drops %d"
  " object-events (%d live-box-events scanned, %.1f%%) across %d"
  " events; %d objects are dropped at every τ where live (census"
  " effect nil at the median)." % (
    S["drops"]["obj_events"], S["drops"]["box_events"],
    100.0 * S["drops"]["obj_events"] / S["drops"]["box_events"],
    S["drops"]["events"], S["drops"]["full_drop_objs"]))
A("")
A("## 2. Owner-clean rate on C-3 box picks")
A("")
A("Fraction of box@1 picks passing each Owner rule, before vs after")
A("(hits = the 16 parent-matched picks; non-hits = %d unmatched"
  " picks).  For S1-a the after-set has %d picks (drops refill from"
  " lower-ranked boxes; a pick slot is empty only if every live box"
  " dropped)." % (440, S["clean_pick"]["na"]))
A("")
A("| rule | hits 0 | hits S1-a | hits S1-b | non-hits 0 | non-hits a | non-hits b |")
A("|---|---|---|---|---|---|---|")
for rule in ("C1@1.0", "C3w@3.0", "C4w@4", "C6g", "C5@q95"):
    r = []
    for arm in ("0", "a", "b"):
        h = S["clean_pick"][arm]["hit|%s" % rule]
        r.append("%d/%d" % (h[0], h[1]))
    for arm in ("0", "a", "b"):
        h = S["clean_pick"][arm]["nonhit|%s" % rule]
        r.append("%d/%d" % (h[0], h[1]))
    A("| %s | %s | %s | %s | %s | %s | %s |" % ((rule,) + tuple(r)))
A("")
A("C6g tolerance = 3 pips (mid-ruler ±3 p edge tolerance; engine")
A("objects carry no golden label tolerance).  C1 is unaffected by")
A("left-edge moves (same band, same τ).")
A("")
A("All live boxes (not only picks), non-hit+hit pooled:")
A("")
A("| rule | 0 | S1-a | S1-b |")
A("|---|---|---|---|")
for rule in ("C1@1.0", "C3w@3.0", "C4w@4", "C6g", "C5@q95"):
    v0 = S["clean_all"]["0"][rule]
    va = S["clean_all"]["a"][rule]
    vb = S["clean_all"]["b"][rule]
    A("| %s | %d/%d | %d/%d | %d/%d |" % (
        rule, v0[0], v0[1], va[0], va[1], vb[0], vb[1]))
A("")
A("(S1-a evaluates only the %d non-dropped object-events.)"
  % S["clean_all"]["n_a_eval"])
A("")
A("## 3. Per-hit table (16 parent hits)")
A("")
A("| panel | golden | arm | IoU 0→1 | coverage 0→1 | d_lo | d_hi | result |")
A("|---|---|---|---|---|---|---|---|")
for d in S["per_hit"]:
    A("| %s | gi%d | %s | %s→%s | %s→%s | %s | %s | %s |" % (
        d["panel"], d["gi"], d["arm"],
        f2(d["iou0"]), f2(d["iou1"]),
        f2(d["cov0"]), f2(d["cov1"]),
        f1(d["dlo"]), f1(d["dhi"]), d["why"]))
A("")
A("Match mechanics (why hits survive): C-3 boxes carry no recorded")
A("build window, so the ruler scores them by the coverage route —")
A("golden containment window ≥50% covered by the drawn span, plus")
A("edges within label tolerance.  Both transforms move only the")
A("drawn LEFT edge; coverage survives while the new edge stays")
A("before the golden window.  IoU (shown for shape, not the match")
A("route) jumps ~0→0.4–0.97 under S1-a: the span actually tightens")
A("to the congestion.  The single loss (S1-a, 9.58a) is a drop, not")
A("an edge/IoU failure.")
A("")
A("## 4. How the author's boxes start (refutation check)")
A("")
A("Of %d golden box-family objects: %d have no impulse run/shock bar "
  "at all before t0 in the day's fed bars; of the %d that do, the "
  "t0-to-event gap is <=2 bars for %d (%.1f%%), <=3 for %d, <=5 for "
  "%d; median %d bars, p90 %.0f." % (
    S["golden_starts"]["n"], S["golden_starts"]["no_event"],
    S["golden_starts"]["n_ev"], S["golden_starts"]["gap_le2"],
    100.0 * S["golden_starts"]["gap_le2"] / S["golden_starts"]["n_ev"],
    S["golden_starts"]["gap_le3"], S["golden_starts"]["gap_le5"],
    S["golden_starts"]["median"], S["golden_starts"]["p90"]))
A("")
A("Reading: the author does NOT typically start a box right after an")
A("extreme event — he starts in the buildup that forms later.  S1-a")
A("reaches a similar *shape* (the span avoids legs/shocks) by")
A("truncation, a different mechanism.  The reset idea is supported")
A("only as an engine-side repair, not as a model of the author's")
A("process.")
A("")
A("## 5. Limitations")
A("")
A("- Selection-only estimate: the engine's birth/shape code is")
A("  untouched; on-chart, a left-edge reset could also change later")
A("  engine behaviour (re-anchoring, edge rewrites) which this replay")
A("  cannot see.")
A("- S1-a's reset point depends on the impulse/shock definitions")
A("  (≥4·ABR in ≤6 same-direction bars; ≥3·ABR range) — thresholds")
A("  fixed by the contract, not tuned.")
A("- Coverage-route matching means moving the left edge can only")
A("  lose hits via drops or by crossing the golden window's start;")
A("  gains are possible only through refilled picks.")
A("- C6g uses a fixed 3-pip tolerance on engine objects (they have")
A("  no label tolerance); the strict tol_e variant is in the JSONL.")
A("- The golden-start check uses the extreme thresholds, so it")
A("  refutes only 'starts right after big legs', not 'starts after")
A("  the last swing break' in general.")
A("")
A("## Tóm tắt cho anh (6 dòng)")
A("")
A("- S1-a (cắt mép trái sau cú sốc/impulse cuối): box-hit 16→15 (mất 1 hit do object bị xoá), nên FAIL keep-rule; nhưng vật sai của máy sạch hẳn: không-shock 37→100%, không-impulse 30→100%, hộp ≤75bar 4→65%.")
A("- S1-b (nắp tuổi 75 bar): box-hit giữ nguyên 16/16, clutter 4.33, các họ khác y nguyên → PASS keep-rule (estimate).")
A("- Sau S1-b: hộp ≤75bar 4→100%, không-shock 37→54%, không-impulse 30→58% — sạch một phần, không hết.")
A("- Hai arm đều không làm mất hit vì ruler chấm bằng độ-phủ của cửa-sổ vàng — mép trái dời phải vẫn chứa vùng congestion.")
A("- Tác giả KHÔNG bắt đầu hộp ngay sau cú sốc/impulse (chỉ 5% trong ≤2 bar, median 36 bar) — reset là cơ chế sửa của máy, không phải cách tác giả vẽ.")
A("- Đề nghị: S1-b an-toàn để build thành flag box_max_drawn_age; S1-a cần giảm drop trước khi build (ví dụ giữ object ở dạng thu-nhỏ thay vì xoá).")

with open(os.path.join(HERE, "DR_RULES_S1.md"), "w",
          encoding="utf8") as fh:
    fh.write("\n".join(P) + "\n")
print("wrote DR_RULES_S1.md (%d lines)" % len(P))

# keep the S1-a' / S2 sections when regenerating (R81 s81.4, R82 s82.3)
if os.path.exists(os.path.join(HERE, "DR_RULES_S1ap_summary.json")):
    import DR_RULES_S1ap_md
    DR_RULES_S1ap_md.append_to_md()
if os.path.exists(os.path.join(HERE, "DR_RULES_S2_summary.json")):
    import DR_RULES_S2_md
    DR_RULES_S2_md.append_to_md()
