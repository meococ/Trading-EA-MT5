"""DR_RULES_S1ap_md.py — append the "S1-a'" section to DR_RULES_S1.md.

Idempotent: an existing "## S1-a'" section is removed first, so both
standalone appends and regeneration via DR_RULES_S1_md.py stay clean.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "DR_RULES_S1.md")
SUM = os.path.join(HERE, "DR_RULES_S1ap_summary.json")
MARK = "\n## S1-a'"


def pct(x):
    return "n/a" if x is None else "%.0f%%" % (100.0 * x)


def section_lines(s):
    L = []
    A = L.append
    t = s["transform"]
    A("## S1-a' — no-drop left-edge reset (R81 §81.4)")
    A("")
    A("Identical to S1-a, except: when the reset would leave fewer than")
    A("3 bars, `t_left` is set to `tau − 2 bars` (the last 3 bars are")
    A("kept) instead of dropping the object.  Causality: bars <= tau.")
    A("")
    A("### Keep rule")
    A("")
    A("| arm | box hits | line | level | bracket | clutter | verdict |")
    A("|---|---|---|---|---|---|---|")
    A("| parent | %d | %d | %d | %d | %.2f | — |" % (
        s["hits"]["parent"], s["parent_nf"]["line"],
        s["parent_nf"]["level"], s["parent_nf"]["bracket"],
        s["clutter"]["median_ratio"]))
    A("| S1-a | 15 | 20 | 7 | 29 | %.2f | FAIL box leg (drop) |"
      % s["clutter"]["median_ratio"])
    A("| S1-b | 16 | 20 | 7 | 29 | %.2f | PASS (estimate) |"
      % s["clutter"]["median_ratio"])
    kr = s["keep_rule"]
    A("| **S1-a'** | **%d** | **%d** | **%d** | **%d** | **%.2f** | "
      "**%s** |" % (
          s["hits"]["ap"], s["nf_hits"]["line"], s["nf_hits"]["level"],
          s["nf_hits"]["bracket"], s["clutter"]["median_ratio"],
          "PASS (estimate)" if all(kr.values()) else "FAIL box leg"))
    A("")
    A("Gained hits: none.  Lost hits: %d — the same golden as under"
      " S1-a (`%s` tau=%d): the pick is clamped to the last 3 bars and"
      " the golden window is no longer covered (cov %.2f).  The clamp"
      " keeps the object on the chart but cannot rescue the hit."
      % (len(s["lost"]),
         s["lost"][0]["panel"] if s["lost"] else "-",
         s["lost"][0]["tau"] if s["lost"] else 0,
         s["lost"][0]["cov1"] if s["lost"] else 0.0))
    A("")
    A("### Transform accounting (909 live box-events)")
    A("")
    A("| kind | n | meaning |")
    A("|---|---|---|")
    A("| reset | %d | same as S1-a (>=3 bars remain) |" % t["reset"])
    A("| clamp3 | %d | S1-a would have dropped; kept as 3-bar box |"
      % t["clamp3"])
    A("| none | %d | no impulse/shock inside span |" % t["none"])
    A("")
    A("Events with >=1 clamped box: %d; objects whose left edge moved"
      " earlier than drawn (j1-2 < j0): %d." % (t["evs_with_clamp3"],
                                                t["extended"]))
    A("")
    A("### Owner-clean rates (live box-events)")
    A("")
    A("| group | rule | before | after |")
    A("|---|---|---|---|")

    def row(name, key, g0, g1):
        b = s["clean"][g0][key]
        a = s["clean"][g1][key]
        A("| %s | %s | %s (%d/%d) | %s (%d/%d) |" % (
            name, key, pct(b[2]), b[0], b[1],
            pct(a[2]), a[0], a[1]))

    for k in ("C3w@3.0", "C4w@4", "C5@q95", "C1@1.0", "C6g"):
        row("matched/picked", k, "hit_before", "hit_after")
    for k in ("C3w@3.0", "C4w@4", "C5@q95", "C1@1.0", "C6g"):
        row("other live boxes", k, "nonhit_before", "nonhit_after")
    A("")
    A("The kept slivers are not all clean: 45 of the %d clamp3 boxes"
      " still contain their triggering event bar(s) (43 a shock bar,"
      " 11 an impulse leg, 9 both) — when the event ends inside the"
      " last 2 bars, tau-2 still covers it.  S1-a reached 100%%"
      " C3w/C4w by deleting these objects; S1-a' reaches ~%s (matched)"
      " / ~%s (other) by shrinking them." % (
          t["clamp3"],
          pct(s["clean"]["hit_after"]["C3w@3.0"][2]),
          pct(s["clean"]["nonhit_after"]["C3w@3.0"][2])))
    A("")
    A("### Per-hit table (16 parent hits under S1-a')")
    A("")
    A("| panel | tau | gi | kind | same pick | cov0 | cov1 | iou0 |"
      " iou1 | match |")
    A("|---|---|---|---|---|---|---|---|---|")
    for d in s["per_hit"]:
        A("| %s | %d | %d | %s | %s | %.2f | %s | %.2f | %s | %s |" % (
            d["panel"], d["tau"], d["gi"], d["kind0"],
            "y" if d["same"] else "n", d["cov0"],
            "%.2f" % d["cov1"] if d["cov1"] is not None else "—",
            d["iou0"],
            "%.2f" % d["iou1"] if d["iou1"] is not None else "—",
            "HIT" if d["matched1"] else "lost"))
    A("")
    A("Prefix invariance: %d/%d identical (truncated vs full-window"
      " pickles, 20 panels)." % (s["prefix"]["same"], s["prefix"]["n"]))
    A("")
    A("### Reading")
    A("")
    A("- S1-a' fixes the drop mechanism but **not** the hit loss: the")
    A("  lost golden needs a box that still covers its window; a 3-bar")
    A("  sliver cannot.  The failure is not the drop rule — it is that")
    A("  this engine box is drawn over a shock the author would never")
    A("  have boxed across.")
    A("- Net vs S1-a: identical hits (15), identical non-box hits,")
    A("  clutter unchanged at %.2f (nothing is dropped), but 54"
      % s["clutter"]["median_ratio"])
    A("  objects stay on the chart as 3-bar slivers, of which 45"
      "  still contain their triggering event (the event ends inside")
    A("  the last 2 bars, so tau-2 still covers it).")
    A("  For G-REVIEW that may look worse than S1-a's empty space.")
    A("- Verdict: **INFO / fails the keep rule** (box 15 < 16).  S1-b")
    A("  remains the only arm passing M1; S1-a' is still the only arm")
    A("  that keeps ~94-97% of the E5 cleaning without deleting")
    A("  objects — useful evidence that the loss is a generation")
    A("  problem (wrong box born), not a shape-fixable one.")
    A("")
    A("### Files")
    A("")
    A("`DR_RULES_S1ap_{measure,report,md}.py`,")
    A("`DR_RULES_S1ap_{events,rows,hits,prefix}.jsonl`,")
    A("`DR_RULES_S1ap_summary.json`,")
    A("`DR_RULES_S1{ap,a,b}_objects.jsonl` (engine-spelling overrides")
    A("for the 12 review panels; G-KIT `--override`).")
    A("")
    A("### Tóm tắt cho anh (4 dòng)")
    A("")
    A("- S1-a' giữ vật trên chart (không xóa), nhưng vẫn mất đúng 1 hit")
    A("  như S1-a: hộp 3 bar không phủ được cửa sổ vàng → vẫn 15/16.")
    A("- 54 vật S1-a xóa được giữ lại thành hộp 3 bar; 45 vật vẫn chứa"
      "  nến shock/impulse gây ra reset nên có thể vẫn bị Gemini chê.")
    A("- Kết luận: lỗi nằm ở chỗ máy sinh hộp sai (vẽ qua shock), không")
    A("  phải ở quy tắc xóa — S1-b vẫn là nhánh duy nhất qua keep-rule.")
    return L


def strip_section(txt):
    i = txt.find(MARK)
    if i < 0:
        return txt
    j = txt.find("\n## ", i + len(MARK))
    tail = "" if j < 0 else txt[j:]
    return (txt[:i].rstrip() + "\n" + tail.lstrip("\n")).rstrip() + "\n"


def append_to_md():
    s = json.load(open(SUM, encoding="utf8"))
    txt = open(MD, encoding="utf8").read() if os.path.exists(MD) else ""
    txt = strip_section(txt)
    with open(MD, "w", encoding="utf8") as f:
        f.write(txt + "\n".join(section_lines(s)) + "\n")
    print("appended S1-a' section (%d lines) -> %s"
          % (len(section_lines(s)), MD))


if __name__ == "__main__":
    append_to_md()
