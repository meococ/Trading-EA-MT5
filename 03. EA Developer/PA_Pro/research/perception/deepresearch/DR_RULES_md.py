"""DR_RULES_md.py — render DR_RULES.md from DR_RULES_summary.json +
DR_RULES_baselines.json.  Read-only wrt everything else; writes only
deepresearch/DR_RULES.md.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "DR_RULES_summary.json")))
FB = json.load(open(os.path.join(HERE, "DR_RULES_baselines.json")))


def f3(x):
    return "NA" if x is None else "%.3f" % x


def f2(x):
    return "NA" if x is None else "%.2f" % x


def ci(b):
    if b["rate"] is None:
        return "n=%d (no evaluable)" % b["n"]
    return "%d/%d = %.3f  [%.2f–%.2f]" % (
        round(b["rate"] * b["n_ev"]), b["n_ev"], b["rate"],
        b["lo"], b["hi"])


def B(rid, rv, fam):
    return S["B"]["|".join((rid, rv, fam))]


def C3(rid, rv, fam):
    return S["C"]["|".join((rid, rv, fam))]


def D(rv):
    return S["D"][rv]


P = []
A = P.append

# ============================ header / method ============================
A("# DR-RULES — do the author's own drawings obey the Owner's rules?")
A("")
A("Ruling 77 §77.3 lane (read-only). Lead 23/09 08:05Z; this report")
A("written 08:56Z same day. Everything below is measured on the TUNE")
A("golden casebook (`golden/draft/BOOK2012_TUNE_v2.jsonl`, 179 scored")
A("panels: 119 boxes, 76 levels, 193 lines) and on the canonical C-3")
A("arm (`uip2_pbbirth@8361fe85e73f9437`, the 623 cached windows of")
A("R75 §75.6). HOLD stayed sealed; the Owner-pack key was never")
A("opened (Part E, ESCALATE).")
A("")
A("## Method in one breath")
A("")
A("- Units: engine EMA25 and ABR20 from each window's cached engine")
A("  (fed bars ≤ τ only), swing-book pivots `e.book.seq`.  All bars are")
A("  M5; width in bars = minutes/5.")
A("- Span of a measure: bars ≤ min(t1, τ); start at drawn t0 (golden)")
A("  or drawn left edge (engine).  Decision time τ per `snapshot.py::")
A("  tau_of` (box/line: build_end/t1; level: t0+10 min).")
A("- Matching: `evalcheck/eval_v2.py` imported, never copied.  Matched")
A("  = live engine object matching a golden whose decision time is τ.")
A("- First-order estimate (Part D): the existing replay path —")
A("  `snapshot.live_records` + `recall_at_k.rank_live`/`score_map` on")
A("  cached pickles, per-family budgets box@1 line@2 level@1 — with each")
A("  rule applied as a pick filter.  Baseline reproduced exactly: hits")
A("  box 16, line 20, level 7, bracket 29; loose live-census 3.89.")
A("- Clutter is reported as the live-at-τ census median")
A("  (objects+marks at golden-decision τ per panel ÷ scorable goldens),")
A("  the selection-only analogue of the published cumulative window")
A("  census (4.33).  Baseline: 3.89, 125/179 panels ≤5.")
A("- Verdict reading (binding letter of §77.3): *“every other family”*")
A("  = families the rule does not target.  In-family hit cost is")
A("  reported (pass_matched, Δhits) but not thresholded — that is the")
A("  Owner's trade-off to weigh.  A strict all-families reading of the")
A("  −1-hit leg is shown as a sensitivity in Part G.")
A("")

# ============================ Part A ============================
A("## A. Book check (notes via `golden/book_loader.py` window only;")
A("paraphrase, quotes ≤15 words)")
A("")
A("| claim | page | verdict |")
A("|---|---|---|")
A("| C1 EMA near object (box) | p54, p136, p153–154 | supports — rallies “from far below EMA25 … breeds doubt”; entries far from EMA refused; flags far from EMA skipped |")
A("| C1 EMA near object (level) | — | silent — levels are swing extremes; the book never asks a level to sit on the EMA |")
A("| C2 EMA not steep | p101, p60/76 | supports — flat-EMA mode reads structure (domes, failed attempts); left-edge slope carries the prior wave |")
A("| C3 no shock bar inside | p109, p141, p211 | supports — oversized/news bars degrade setups; abnormally-long-bar check in RULEBOOK |")
A("| C4 no impulse inside | p20 | partial — break “from far away with acceleration and no buildup” is weak; span crossing a leg not addressed |")
A("| C5 bounded box width | p147–156, 5.3 meas | contradicts the 20-bar form — author boxes measured ≈70 and ≈85 bars; supports only “bounded” weakly |")
A("| C6 cluster edges, no lone wick | p217, p120 | supports — spike low left outside the box to show “the dense character of the block”; ~5-p spike wicks ignored |")
A("| C7 delete zombie levels/lines | p56/66, p89 | mixed/contradicts — broken lines kept for pullbacks; an edge is deleted only when it “stopped making sense” |")
A("| C8 newer extreme supersedes | p154, p170 | partial — consumed/touched levels retire; untested broken level stays a magnet (not superseded) |")
A("| EMA period | p47 | supports — only indicator is EMA25 (18–30 “works”) |")
A("| “daylight” (price far from EMA) | p54, p136, p153–154 | supports (see C1) |")
A("| build-up before break | p20, p78 | supports — buildup should flatten with shrinking bars |")
A("| block size | p153–156 | supports — measured sizes given; no upper bar bound |")
A("| shock/news bars | p109, p141 | supports (see C3) |")
A("| deleting broken levels | p56, p154 | contradicts blanket-deletion — broken-but-untested stays a magnet |")
A("")

# ============================ Part B ============================
A("## B. Author compliance (TUNE golden; Wilson 95% CI)")
A("")
A("n = author's objects of that family; pass-rate with CI.")
A("")
A("| rule | fam | pass |")
A("|---|---|---|")
for v in S["verdicts"]:
    b = B(v["rule"], v["variant"], v["fam"])
    A("| %s | %s | %s |" % (v["variant"], v["fam"], ci(b)))
A("")
A("### Continuous distributions (author, p10/25/50/75/90/95)")
A("")
D_ = S["Bdist"]
for fam, d in D_.items():
    A("**%s**" % fam)
    A("")
    A("| measure | p10 | p25 | p50 | p75 | p90 | p95 |")
    A("|---|---|---|---|---|---|---|")
    for m_, q in d.items():
        A("| %s | %s | %s | %s | %s | %s | %s |" % (
            m_, f2(q["p10"]), f2(q["p25"]), f2(q["p50"]),
            f2(q["p75"]), f2(q["p90"]), f2(q["p95"])))
    A("")
A("Derived thresholds used for q95/q90 variants:")
A("")
A("- C2 steepness s: box q95 %.3f / q90 %.3f; level %.3f / %.3f; line %.3f / %.3f" % (
    S["thresholds"]["C2@box"]["q95"], S["thresholds"]["C2@box"]["q90"],
    S["thresholds"]["C2@level"]["q95"], S["thresholds"]["C2@level"]["q90"],
    S["thresholds"]["C2@line"]["q95"], S["thresholds"]["C2@line"]["q90"]))
A("- C5 width W: drawn q95 %.0f / q90 %.0f bars; containment q95 %.0f / q90 %.0f" % (
    S["thresholds"]["C5@box"]["q95"], S["thresholds"]["C5@box"]["q90"],
    S["thresholds"]["C5w@box"]["q95"], S["thresholds"]["C5w@box"]["q90"]))
A("")
A("### Sensitivities (author)")
A("")
A("| variant | fam | pass |")
A("|---|---|---|")
for key, b in S["B"].items():
    rid, rv, fam = key.split("|")
    if rv.split("@")[0] in ("C3w", "C4w", "C5w", "C6g", "C7s", "C7f", "C8a"):
        A("| %s | %s | %s |" % (rv, fam, ci(b)))
A("")
A("Reading: C3w/C4w/C5w measure the containment window")
A("(build_start..build_end), not the drawn span — the drawn span of an")
A("author box includes the break bar and follow-through, which is why")
A("drawn-span C3/C4 compliance is lower.  C7s/C7f (span/full history)")
A("show the zombie measure the birth window hides: author levels had a")
A("median of 3 close-switches before τ (C7f@2 pass 0.461) — the author")
A("does draw across already-weaved prices.  C6g relaxes the strict")
A("cluster tolerance to the ruler's golden tolerance (label noise):")
A("pass 0.336→0.420, still far below 0.90 — the author draws edges")
A("*inside* the outermost cluster (median 3.7 p, p75 8.6 p off), i.e.")
A("he trims spikes rather than sitting on the cluster extreme.")
A("")

# ============================ Part C ============================
A("## C. C-3 split (canonical 623 windows; pass-rate on matched vs")
A("unmatched live objects)")
A("")
A("matched = engine pick that matches a golden at its τ (hits a gate")
A("would lose); unmatched = false objects the gate could remove.")
A("removal = 1 − pass(unmatched).")
A("")
A("| rule | fam | pass match (n) | pass unmatch (n) | removal |")
A("|---|---|---|---|---|")
for v in S["verdicts"]:
    c = C3(v["rule"], v["variant"], v["fam"])
    A("| %s | %s | %s/%d | %s/%d | %s |" % (
        v["variant"], v["fam"],
        f2(c["pass_matched"]), c["n_matched"],
        f2(c["pass_unmatched"]), c["n_unmatched"],
        f3(c["removal_unmatched"])))
A("")
A("### Sensitivities (engine)")
A("")
A("| variant | fam | pass match (n) | pass unmatch (n) | removal |")
A("|---|---|---|---|---|")
for key, c in S["C"].items():
    rid, rv, fam = key.split("|")
    if rv.split("@")[0] == "C6g":
        continue                       # golden-only variant (tol_g)
    if rv.split("@")[0] in ("C3w", "C4w", "C5w", "C6g", "C7s", "C7f", "C8a"):
        A("| %s | %s | %s/%d | %s/%d | %s |" % (
            rv, fam,
            f2(c["pass_matched"]), c["n_matched"],
            f2(c["pass_unmatched"]), c["n_unmatched"],
            f3(c["removal_unmatched"])))
A("")
A("Reading: engine boxes are far wider than the author's (C5 drawn")
A("removal 0.967 vs author pass 0.950 — the asymmetry is lifetime, not")
A("congestion width: C5w containment removal is only 0.041).  Engine")
A("levels sit far from the EMA (C1@1.0 removal 0.55) while the")
A("author's do too — C1 is a *box* rule in the author's grammar.")
A("Engine zombie exposure (C7s/C7f/C8a) is much larger than the")
A("author's: C7f@2 removes 72.5% of unmatched levels; C8a@1 72.5%")
A("(anchor-based supersession).")
A("")

# ============================ Part D ============================
A("## D. Joint first-order estimate (selection-only; existing replay")
A("path, per-family budgets)")
A("")
A("Baseline hits: box 16, line 20, level 7, bracket 29; live-census")
A("clutter median 3.89.")
A("")
A("| rule | hits after | Δhits | freed fills (matched) | lost picks | clutter med |")
A("|---|---|---|---|---|---|")
def dd(dct):
    return " ".join("%s%+d" % (f[:2], v) if v else "%s%d" % (f[:2], v)
                    for f, v in dct.items())


for k, d in S["D"].items():
    rid, rv = k.split("|")
    if rv.split("@")[0] in ("C3w", "C4w", "C5w", "C6g", "C7s", "C7f", "C8a"):
        continue
    A("| %s | %s | %s | %d (%d) | %d | %.2f |" % (
        rv, dd(d["hits_after"]), dd(d["d_hits"]), d["n_fills"],
        d["fills_matched"], d["lost_picks"], d["clutter_med"]))
A("")
A("Reading: freed slots almost never recover hits (fills_matched ≈ 0)")
A("— the filter drops the pick and the next candidate in line is")
A("unmatched; consistent with R75 §75.2(b) (the right object is not")
A("live at τ; the deficit is on the generation side).  Cross-family")
A("damage: C1 applied to box+level also kills all 7 level hits (the")
A("level family is structurally far-from-EMA); C2@q95 costs 2 line")
A("hits as collateral.")
A("")

# ============================ Part E ============================
A("## E. Owner pack — ESCALATE")
A("")
A("ESCALATE: pack geometry only in keyed file")
A("(`evalcheck/_owner_judge_key/m2_c3_key.json`).  `manifest.jsonl`")
A("holds seq+png only; items are blind PNGs; no non-keyed geometry")
A("exists.  Per §77.3 Part E is skipped; `DR_RULES_pack_features.csv`")
A("is not written.  No OCR, no key inspection.")
A("")

# ============================ Part F ============================
A("## F. PA-ATLAS baselines under the same gates")
A("")
A("Baseline hits reproduce published: bl_tdlines_k2 line@2 %d/%d,"
  " clutter %.2f; bl_donchian_alt level@1 %d/%d, clutter %.2f." % (
    FB["bl_tdlines_k2"]["hits0"], FB["bl_tdlines_k2"]["n_gold"],
    FB["bl_tdlines_k2"]["clutter0"],
    FB["bl_donchian_alt"]["hits0"], FB["bl_donchian_alt"]["n_gold"],
    FB["bl_donchian_alt"]["clutter0"]))
A("")
for name, d in FB.items():
    A("### %s (fam=%s, k=%d, live objects=%d)" % (
        name, d["fam"], d["k"], d["n_live"]))
    A("")
    A("| rule | hits (Δ) | removed live | clutter after |")
    A("|---|---|---|---|")
    for rv, v in d["variants"].items():
        A("| %s | %d (%+d) | %d/%d | %s |" % (
            rv, v["hits"], v["hits"] - d["hits0"], v["removed_live"],
            d["n_live"], f2(v["clutter"])))
    A("")
A("Reading: on donchian levels **C1@1.0 removes 68% of live objects,")
A("keeps all 16 hits, clutter 10.33→2.50** — the single best free")
A("filter in the study (baseline-side; engine matched levels are not")
A("so lucky).  C7/C8 barely touch baselines that already retire or")
A("deduplicate their objects.")
A("")
A("(`clutter after` = filtered cumulative census measured at w1;")
A("`removed live` counts filters at golden-decision τ — the two")
A("windows differ, so clutter can drop with zero τ-removals, e.g.")
A("C7 on tdlines.)")
A("")

# ============================ Part G ============================
A("## G. Verdicts (§77.3, literal reading; in-family hit cost shown)")
A("")
A("| rule | fam | author pass | pass matched | removal | Δhits (all fams) | clutter | verdict |")
A("|---|---|---|---|---|---|---|---|")
for v in S["verdicts"]:
    flag = "  **⚠ in-fam %d**" % v["infam_loss"] if v["infam_loss"] < -1 else ""
    A("| %s | %s | %s | %s | %s | %s | %.2f | %s%s |" % (
        v["variant"], v["fam"],
        f3(v["author_pass"]),
        f2(v["pass_matched"]),
        f3(v["removal_unmatched"]),
        dd(v["d_hits"]), v["clutter"], v["verdict"], flag))
A("")
A("Strict-reading sensitivity (if the −1-hit leg bounded *every*")
A("family including the target): C5@q95 (−14), C8@1 (−4), C8@2 (−2)")
A("would all drop to INFO — zero BUILD-CANDIDATEs.  Reported so the")
A("Lead can re-cut without re-running the lane.")
A("")
A("### What the builder would flag")
A("")
A("- **C8 supersede-gate** (level): kill or retire a level once a")
A("  confirmed same-polarity swing extreme born after it lies ≥1·ABR")
A("  beyond it.  Variants: k=1 (removal .361, keeps 3/7 hits) and k=2")
A("  (removal .232, keeps 5/7).  Parameters: pivot set = engine")
A("  swing-book (confirmed pivots), beyond = (pivot−level)/ABR20 at τ.")
A("  Anchor variant (born after the level's *structural* bar) removes")
A("  72.5% — flagged, not verdicted.  This mirrors the engine's own")
A("  `consumed`/retire semantics, so it is the least foreign rule to")
A("  build.")
A("- **C5 width gate** (box): drawn width ≤75 bars is the author's q95,")
A("  but as a *hard filter* it keeps only 2/16 hits — engine boxes are")
A("  wide because they persist, not because congestion is wide (C5w")
A("  containment removal .04).  A builder should NOT filter the drawn")
A("  box; the equivalent mechanic is **bounded persistence** — retire/")
A("  shrink a box whose drawn age exceeds ~75 bars unless re-anchored.")
A("  Flag name: `box_max_drawn_age`; parameter: 75 bars (q95),")
A("  alternative 56 (q90).")
A("- **C1 daylight** is a *box-shaped* rule in the author's grammar —")
A("  author levels sit 1.25 ABR (median) from the EMA by construction.")
A("  If ever built, restrict to box family only (box pass .824@1.0,")
A("  removal .07) — below the removal bar anyway; TRADER-ONLY stands.")
A("")
A("## Limitations")
A("")
A("- τ for golden levels = t0+10 min, so C7/C8 author windows are ~2")
A("  bars — literal compliance is vacuous (hence C7f/C8a sensitivities).")
A("- Golden box edges are eyeballed ±5 p — C6 strict pass 0.336 is a")
A("  lower bound on the intended definition, not a refutation of")
A("  “edges on clusters”.")
A("- The first-order estimate is selection-only: the engine's birth")
A("  side is untouched, so a rule can never *gain* a hit here, only")
A("  lose or leave them.  fills_matched≈0 is a property of the pool.")
A("- q95/q90 thresholds are author-derived per family (n=76–193),")
A("  so they are calibrated, not universal.")
A("- Part E skipped (keyed geometry); pack-side evidence absent.")
A("")

# ============================ Vietnamese summary ============================
A("## Tóm tắt cho anh (10 dòng, mỗi rule một dòng)")
A("")
A("- Kết luận: 8 rule của anh, tác giả chỉ tuân thủ sạch 3 rule (C2, C7, C8); BUILD-CANDIDATE = C8 (level) và C5@q95 (box).")
A("- C1 EMA-gần: tác giả tuân thủ 77–82% ở box (level chỉ 17–37% — tác giả vẽ level xa EMA sẵn), bỏ được 7–10% box / 55–78% level vật sai của máy.")
A("- C2 EMA-phẳng: tác giả tuân thủ 95% ở ngưỡng q95, bỏ được 2–10% vật sai của máy; mất 2 line-hit vật xui.")
A("- C3 không-bar-sốc: tác giả tuân thủ 70–83%, bỏ được 65–91% vật sai của máy nhưng mất 9–13/16 box-hit.")
A("- C4 không-xung-lực: tác giả tuân thủ 60–90%, bỏ được 71–98% vật sai của máy, mất 7–16 box-hit.")
A("- C5 hộp-hữu-hạn: tác giả tuân thủ 95% ở q95 (75 bar; ~40% hộp tác giả >20 bar nên mốc 20-bar của anh không đúng), bỏ được 97% vật sai nhưng chỉ giữ 2/16 hit.")
A("- C6 cạnh-theo-cụm: tác giả tuân thủ 34–42% (tác giả vẽ mép TRONG cụm cực-trị, cắt wick), bỏ được 99% vật sai của máy, mất 15/16 box-hit.")
A("- C7 xoá-mức-zombie: tác giả tuân thủ 100% theo cửa sổ sinh (nhưng đo cả-đời thì chỉ 46% — tác giả vẽ level qua giá đã đan-xen), bỏ được 10–14% vật sai level của máy.")
A("- C8 mức-bị-thay: tác giả tuân thủ 100%, bỏ được 23–36% vật sai level của máy, giữ 3–5/7 hit — rule khả-dĩ nhất để build.")
A("- Nói gọn: rule đáng build là C8 (xóa level bị swing mới vượt) và C5-dạng-tuổi-hộp; mấy rule khác nên hỏi lại anh cách chú áp dụng, vì tác giả chính ông ấy cũng không vẽ theo kiểu đó.")

with open(os.path.join(HERE, "DR_RULES.md"), "w", encoding="utf8") as fh:
    fh.write("\n".join(P) + "\n")
print("wrote DR_RULES.md (%d lines)" % len(P))
