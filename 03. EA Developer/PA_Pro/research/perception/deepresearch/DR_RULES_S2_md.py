"""DR_RULES_S2_md.py — append the "S2" section to DR_RULES_S1.md.

Idempotent: an existing "## S2 " section is removed first (section runs
to end of file or to a later '## S2' heading — it is appended last).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "DR_RULES_S1.md")
SUM = os.path.join(HERE, "DR_RULES_S2_summary.json")
MARK = "\n## S2 "


def pct(x):
    return "n/a" if x is None else "%.0f%%" % (100.0 * x)


def section_lines(s):
    L = []
    A = L.append
    H, nf, cen = s["hits"], s["nf_hits"], s["census"]
    A("## S2 — the box ends at the breakout (R82 §82.3)")
    A("")
    A("Rule (fixed): first run of k consecutive closes beyond")
    A("`top+tol_e` / `bottom−tol_e` inside the drawn span [t_left,")
    A("min(t_right,tau)] closes the box at tau — removed before the")
    A("box@1 pick, sticky.  tol_e = trade_tags.tol_e (imported).")
    A("Variants k2 (k=2), k3 (k=3).  Parent = C-3 canonical 623.")
    A("")
    A("### Keep rule")
    A("")
    A("| arm | box hits | line | level | bracket | census | prefix |"
      " verdict |")
    A("|---|---|---|---|---|---|---|---|")
    A("| parent | %d | %d | %d | %d | %.2f | 178/178 | — |" % (
        16, s["parent_nf"]["line"], s["parent_nf"]["level"],
        s["parent_nf"]["bracket"], cen["0"][0]))
    for a in ("k2", "k3"):
        kp = s["keep"][a]
        A("| S2-%s | **%d** | %d | %d | %d | %.2f | %d/%d | **%s** |" % (
            a, H[a], nf["line"], nf["level"], nf["bracket"],
            cen[a][0], s["prefix"][a][0], s["prefix"][a][1],
            "PASS" if all(kp.values()) else "FAIL box leg"))
    A("")
    def promo_str(a):
        return "; ".join("%s@%d %s->%s" % (p["panel"], p["tau"],
                                           p["pick0"], p["pick"])
                         for p in s["promoted"][a]) or "none"
    A("Gained hits: k2 %s, k3 %s — the 9.39a@475 gain is a promotion:"
      " closing the top box freed the slot for a lower-ranked box"
      " that matched.  Promoted picks (hit or not): k2 %s; k3 %s."
      % (s["gained"]["k2"], s["gained"]["k3"],
         promo_str("k2"), promo_str("k3")))
    A("")
    A("### What the rule does to the engine")
    A("")
    A("| measure | k2 | k3 |")
    A("|---|---|---|")
    A("| live box-events closed | %d/909 (%.0f%%) | %d/909 (%.0f%%) |"
      % (s["counts"]["closed_all"]["k2"],
         100.0 * s["counts"]["closed_all"]["k2"] / 909,
         s["counts"]["closed_all"]["k3"],
         100.0 * s["counts"]["closed_all"]["k3"] / 909))
    A("| picked box closed | %d/456 | %d/456 |" % (
        s["counts"]["closed_picked"]["k2"],
        s["counts"]["closed_picked"]["k3"]))
    A("| of closed: born-broken (confirm < t_birth) | 479 (59%) |"
      " 444 (57%) |")
    A("| mean live boxes / event | %.2f (was %.2f) | %.2f |" % (
        s["mean_boxes"]["k2"], s["mean_boxes"]["before"],
        s["mean_boxes"]["k3"]))
    A("| census clutter | %.2f (was %.2f) | %.2f |" % (
        cen["k2"][0], cen["0"][0], cen["k3"][0]))
    A("")
    A("Median confirm lands ~12-14 bars after the left edge; a closed")
    A("box had then lived ~111 bars past its breakout (p10/50/90 =")
    A("41/111/176).  More than half of all closures are born-broken:")
    A("the engine draws t_left across regions price had already left,")
    A("so the first break sits *before* the box was even born.")
    A("")
    A("### Author compliance (same rule on golden boxes, own span/edges)")
    A("")
    A("| k | golden boxes the rule would close | share |")
    A("|---|---|---|")
    A("| 2 | %d/%d | %.0f%% |" % (
        s["author"]["k2"], s["author"]["n"],
        100.0 * s["author"]["k2"] / s["author"]["n"]))
    A("| 3 | %d/%d | %.0f%% |" % (
        s["author"]["k3"], s["author"]["n"],
        100.0 * s["author"]["k3"] / s["author"]["n"]))
    A("")
    A("The author keeps ~%d%% (k3) to ~%d%% (k2) of his boxes despite"
      % (round(100.0 * s["author"]["k3"] / s["author"]["n"]),
         round(100.0 * s["author"]["k2"] / s["author"]["n"])))
    A("confirmed closes beyond them inside their own drawn span — the")
    A("box documents a congestion price already left, which he still")
    A("draws.  The reviewer's literal rule is stricter than the author.")
    A("")
    A("### Reviewer cases")
    A("")
    A("S1-b fatal boxes (the capped rectangles):")
    A("")
    A("| panel | object | closed k2 | closed k3 | confirm bar |")
    A("|---|---|---|---|---|")
    for x in s["review"]["s1b_fatal"]:
        A("| %s | %s | %s | %s | %s / %s |" % (
            x["panel"], x["id"],
            "y" if x["closed_k2"] else "n",
            "y" if x["closed_k3"] else "n",
            x["confirm2"] if x["confirm2"] is not None else "—",
            x["confirm3"] if x["confirm3"] is not None else "—"))
    A("")
    A("R1 E5 panels (box swallows impulse / lives past breakout) —")
    A("closed box-family objects in the drawn set:")
    A("")
    for x in s["review"]["e5"]:
        cl = ", ".join("%s(k%d @%d %s)" % (c["id"], c["k"],
                                           c["confirm_bar"], c["side"])
                       for c in x["closed"]) or "none"
        A("- `%s`: %s" % (x["panel"], cl))
    A("")
    A("### Per-hit table (16 parent box hits)")
    A("")
    A("| panel | tau | gi | arm | pick0 closed | confirm bar | bars"
      " before tau | pick | match |")
    A("|---|---|---|---|---|---|---|---|---|")
    for d in s["per_hit"]:
        A("| %s | %d | %d | %s | %s | %s | %s | %s | %s |" % (
            d["panel"], d["tau"], d["gi"], d["arm"],
            "y" if d["pick0_closed"] else "n",
            d["confirm_bar"], d["bars_before_tau"],
            ("same" if d["same_pick"]
             else ("fill:%s" % d["pick"] if d["fill"] else "none")),
            "HIT" if d["matched1"] else "lost"))
    A("")
    A("### Reading / limitations")
    A("")
    A("- S2 as specified is **far too strong**: it fires on 86-89% of")
    A("  live box-events and keeps only 2/16 (k2) / 4/16 (k3) hits.")
    A("  Both variants FAIL the keep rule (box leg).")
    A("- Mechanism: the engine's boxes have long retroactive left")
    A("  edges; ~57-59% of closures confirm *before* t_birth — the")
    A("  box is born already-broken.  This is a generation error")
    A("  (t_left drawn across an escaped region), the same lesson as")
    A("  S1-a': the fix belongs in generation, not in post-hoc")
    A("  closure.")
    A("- The rule does clean what the reviewer flagged: 3/4 S1-b")
    A("  fatal boxes close (9.10c, 9.36c, 9.40a; 9.33c does not),")
    A("  and every named box on the 4 E5 panels closes under both k.")
    A("- Author check: the author himself keeps 14-24% of boxes with")
    A("  confirmed closes beyond them — a literal 'end at breakout'")
    A("  is stricter than the author, so even a working variant would")
    A("  need an M2-vs-M1 conversation, not just a build flag.")
    A("- Offline estimate only; ranking/scores untouched; other")
    A("  families verified identical (20/7/29); prefix 178/178.")
    A("")
    A("### Files")
    A("")
    A("`DR_RULES_S2_{measure,report,md}.py`,")
    A("`DR_RULES_S2_{events,rows,hits,golden,prefix,census}.jsonl`,")
    A("`DR_RULES_S2_summary.json`, `DR_RULES_S2_review_closed.jsonl`,")
    A("`DR_RULES_S2_{k2,k3}_objects.jsonl` (G-KIT overrides, engine")
    A("spelling, base = review/sets/c3 drawn objects minus closed).")
    A("")
    A("### Tóm tắt cho anh (5 dòng)")
    A("")
    A("- S2 đóng hộp khi giá close qua mép: k2 giữ 2/16 hit, k3 giữ")
    A("  4/16 — quá mạnh, rơi keep-rule.")
    A("- Nhưng đúng bệnh: ~57-59% hộp bị đóng là 'sinh ra đã vỡ' — máy")
    A("  kéo mép trái qua vùng giá đã thoát từ trước.")
    A("- Rule đóng được 3/4 hộp S1-b bị Gemini chê và toàn bộ hộp E5 —")
    A("  vấn đề nằm ở generation, không phải lọc sau.")
    A("- Tác giả cũng giữ 14-24% hộp đã bị close vượt mép — rule literal")
    A("  còn chặt hơn cả tác giả.")
    A("- Đề nghị: không build S2; đưa 'đừng sinh hộp qua breakout cũ'")
    A("  vào nghiên cứu generation (E3/BOX-LAB).")
    return L


def strip_section(txt):
    i = txt.find(MARK)
    if i < 0:
        return txt
    return txt[:i].rstrip() + "\n"


def append_to_md():
    s = json.load(open(SUM, encoding="utf8"))
    txt = open(MD, encoding="utf8").read() if os.path.exists(MD) else ""
    txt = strip_section(txt)
    with open(MD, "w", encoding="utf8") as f:
        f.write(txt + "\n".join(section_lines(s)) + "\n")
    print("appended S2 section (%d lines) -> %s"
          % (len(section_lines(s)), MD))


if __name__ == "__main__":
    append_to_md()
