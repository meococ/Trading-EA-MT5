"""VPA-DR3 census — cadence, funnel, feature distributions, burned-set diagnostic.

Prereg: research/VPA-DR3_FROZEN_PREREG.md (SHA A61F06BA...). No outcome fields
(F7/E4). The 60 burned cases are DIAGNOSTIC-ONLY (E3). D2 verdict per F6.

Outputs: PLAN/census_dr3/CENSUS_DR3_SUMMARY.md, CENSUS_DR3.json,
CANDIDATES_DR3.csv (evaluated candidates = warmup+session+direction passing).
"""

import collections
import csv
import json
import os
import statistics
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "census_dr3")
GRADING = os.path.join(PKG, "PLAN", "grading")

from vpa_data import load_m5_bars  # noqa: E402
from vpa_dr1 import run_dr1, DR3_CFG, DR3_HARD_GATES  # noqa: E402
from vpa_trace import classify_cases  # noqa: E402

HARD = list(DR3_HARD_GATES)


def med_iqr(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None
    xs = sorted(xs)
    return statistics.median(xs), (xs[int(0.75 * (len(xs) - 1))] - xs[int(0.25 * (len(xs) - 1))])


def feat_of(rec):
    g = rec.get("gates") or {}
    bu = (g.get("buildup", {}).get("value") or {})
    room = (g.get("room", {}).get("value") or {})
    chop = (g.get("chop", {}).get("value") or {})
    adv = (g.get("adverse", {}).get("value") or {})
    anti = (g.get("anti_chase", {}).get("value") or {})
    v2 = bu.get("v2of4") or {}
    vt = bu.get("vtight") or {}
    rr = room.get("room_r")
    return {
        "bar_idx": rec["bar_idx"], "trigger_idx": rec.get("trigger_idx"),
        "side": rec["side"], "session": rec.get("session"), "setup": rec.get("setup"),
        "executable": int(bool(rec.get("executable"))), "first_fail": rec.get("skip_reason"),
        "n": bu.get("n"), "band_closes": bu.get("band_closes"), "buildup_touches": bu.get("touches"),
        "overlap": bu.get("overlap"), "contraction": bu.get("contraction"),
        "conditions_passed": bu.get("conditions_passed"), "squeeze": int(bool(bu.get("squeeze"))),
        "v2of4_n": v2.get("n"), "vtight_n": vt.get("n"),
        "chop_legacy": int(bool(chop.get("chop"))), "chop_window": (int(bool(chop["chop_window"])) if chop.get("chop_window") is not None else None),
        "room_r": (None if rr is None or rr == float("inf") else rr),
        "room_inf": int(rr == float("inf")) if rr is not None else None,
        "obstacle_type": (room.get("obstacle") or {}).get("type"),
        "adverse": int(bool(adv)), "entry_b_atr": anti.get("entry_b_atr"),
        "range_atr": anti.get("range_atr"), "ema_dist_atr": anti.get("ema_dist_atr"),
        "pressure": int(bool(rec.get("pressure"))), "bars_since_pressure": rec.get("bars_since_pressure"),
        "lunch": int(bool(rec.get("lunch"))), "rho": rec.get("rho"),
        "atr": rec.get("atr"), "level": rec.get("level"),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    bars = load_m5_bars("EURUSD")
    pip = bars["pip"]
    cfg = dict(DR3_CFG, round_grid_price=50.0 * pip, collect_gates=True)
    recs, cnt = run_dr1(bars, cfg=cfg)
    weeks = (bars["t"][-1] - bars["t"][0]) / 604800.0
    ex = [r for r in recs if r.get("executable")]
    # evaluated = warmup + session + direction pass (F5's rejected universe)
    ev = []
    for r in recs:
        g = r.get("gates") or {}
        if (g.get("warmup", {}).get("pass") and g.get("session", {}).get("pass")
                and g.get("direction", {}).get("pass")):
            ev.append(r)
    acc = [r for r in ev if r.get("executable")]
    rej = [r for r in ev if not r.get("executable")]

    # cadence
    per_year = collections.Counter()
    per_session = collections.Counter()
    for r in ex:
        y = datetime.datetime.utcfromtimestamp(int(bars["t"][r["bar_idx"]])).year
        per_year[y] += 1
        per_session[r.get("session")] += 1
    cad = {"exec_total": len(ex), "weeks": round(weeks, 1), "per_week": round(len(ex) / weeks, 3),
           "per_year": dict(sorted(per_year.items())), "per_session": dict(per_session)}
    verdict = ("NORMAL" if cad["per_week"] >= 10 else "LOW_CADENCE" if cad["per_week"] >= 3 else "STOP")

    # funnel (first fail over the hard gates)
    funnel = collections.Counter()
    for r in ev:
        funnel[r.get("skip_reason") or "executable"] += 1
    counters = {k: v for k, v in sorted(cnt.items()) if k.startswith(("skip_", "signal_", "barrier_", "chop_", "executable"))}

    # features accepted vs rejected
    fa = [feat_of(r) for r in acc]
    fr = [feat_of(r) for r in rej]
    FEATS = ["n", "band_closes", "buildup_touches", "overlap", "contraction", "conditions_passed",
             "v2of4_n", "vtight_n", "room_r", "entry_b_atr", "range_atr", "ema_dist_atr",
             "bars_since_pressure", "rho", "atr"]
    dist = {}
    for f in FEATS:
        ma, ia = med_iqr([x[f] for x in fa])
        mr, ir = med_iqr([x[f] for x in fr])
        dist[f] = {"acc_med": ma, "acc_iqr": ia, "rej_med": mr, "rej_iqr": ir}
    rates = {}
    for f in ("squeeze", "chop_legacy", "chop_window", "adverse", "pressure", "lunch", "room_inf"):
        ra = [x[f] for x in fa if x[f] is not None]
        rr_ = [x[f] for x in fr if x[f] is not None]
        rates[f] = {"acc": round(sum(ra) / len(ra), 4) if ra else None,
                    "rej": round(sum(rr_) / len(rr_), 4) if rr_ else None}

    # burned-set diagnostic (E3: DIAGNOSTIC-ONLY)
    key = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "KEY_HIDDEN.csv"), encoding="utf-8"))}
    lead = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "GRADES_LEAD_BLIND.csv"), encoding="utf-8"))}
    cases = []
    for cid, k in key.items():
        if cid not in lead:
            continue
        cases.append({"case_id": cid, "lead_grade": lead[cid]["grade"].strip().upper(),
                      "group": k.get("sample_group"), "setup_v1": k.get("setup"),
                      "bar_idx": int(k["bar_idx"]), "side": int(k["side"]),
                      "barrier_level": float(k["barrier_level"]) if k.get("barrier_level") else None,
                      "atr": float(k["atr"]) if k.get("atr") else None})
    cases.sort(key=lambda c: c["case_id"])
    d, rows, _ = classify_cases(bars, cases, half=12, cfg=cfg)
    ab = [r for r in rows if r["lead_grade"] in ("A", "B")]
    cc = [r for r in rows if r["lead_grade"] == "C"]
    diag = {"evaluated": {"AB": sum(1 for r in ab if r["category"].startswith(("(iii", "(iv"))),
                                   "C": sum(1 for r in cc if r["category"].startswith(("(iii", "(iv")))},
            "accepted": {"AB": sum(1 for r in ab if r["category"].startswith("(iv")),
                         "C": sum(1 for r in cc if r["category"].startswith("(iv"))},
            "integrity_fail": {"AB": sum(1 for r in ab if "integrity" in (r["fail_set"] or "").split(";")),
                               "C": sum(1 for r in cc if "integrity" in (r["fail_set"] or "").split(";"))},
            "trend_fail": {"AB": sum(1 for r in ab if "trend" in (r["fail_set"] or "").split(";")),
                           "C": sum(1 for r in cc if "trend" in (r["fail_set"] or "").split(";"))},
            "hard_first_fail": {}}
    hff = collections.Counter()
    for r in rows:
        if r["first_fail"] in ("skip_" + h for h in HARD):
            hff[(r["lead_grade"] in ("A", "B"), r["first_fail"])] += 1
    diag["hard_first_fail"] = {f"{'AB' if k[0] else 'C'}:{k[1]}": v for k, v in sorted(hff.items())}

    # write candidates csv
    fields = list(fa[0].keys()) if fa else list(feat_of(ev[0]).keys())
    with open(os.path.join(OUT, "CANDIDATES_DR3.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ev:
            w.writerow(feat_of(r))

    summary = {"config": "DR3_CFG", "prereg_sha256": "A61F06BA776BD0D74A94FBFD243ECFFC9C880988832BAEC789F50DAA675E05A2",
               "bars": len(bars["t"]), "records": len(recs), "evaluated": len(ev),
               "accepted": len(acc), "rejected": len(rej), "cadence": cad,
               "d2_verdict": verdict, "funnel": dict(funnel), "counters": counters,
               "feature_dist": dist, "feature_rates": rates, "burned_diagnostic": diag}
    with open(os.path.join(OUT, "CENSUS_DR3.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, default=str)

    md = ["# CENSUS_DR3 — trend-primary + integrity (prereg SHA A61F06BA…)", "",
          f"DESIGN EURUSD 2016-2021: {len(bars['t'])} bars, {weeks:.1f} weeks. "
          f"records {len(recs)}, evaluated {len(ev)}, accepted {len(acc)}, rejected {len(rej)}.", "",
          "## 1. Cadence (F6/D2)", "",
          f"**accepted {len(ex)} = {cad['per_week']}/week → {verdict}** "
          "(>=10 NORMAL, 3-<10 LOW_CADENCE, <3 STOP)", "",
          "| year | " + " | ".join(str(y) for y in sorted(per_year)) + " |",
          "|---|" + "---|" * len(per_year),
          "| accepted | " + " | ".join(str(per_year[y]) for y in sorted(per_year)) + " |", "",
          f"per session: {dict(per_session)}", "",
          "## 2. Funnel (first fail over the hard gates)", "",
          "| first_fail | n |", "|---|---|"]
    for k, v in funnel.most_common():
        md.append(f"| {k} | {v} |")
    md += ["", "counters: `" + json.dumps(counters, sort_keys=True) + "`", "",
           "## 3. Features (median [IQR]) accepted vs rejected", "",
           "| feature | accepted | rejected |", "|---|---|---|"]
    for f in FEATS:
        x = dist[f]
        md.append(f"| {f} | {x['acc_med']} [{x['acc_iqr']}] | {x['rej_med']} [{x['rej_iqr']}] |")
    md += ["", "| rate | accepted | rejected |", "|---|---|---|"]
    for f, v in rates.items():
        md.append(f"| {f} | {v['acc']} | {v['rej']} |")
    md += ["", "## 4. Burned-set diagnostic (E3: DIAGNOSTIC-ONLY, never fidelity)", "",
           f"- evaluated: A/B {diag['evaluated']['AB']}/16, C {diag['evaluated']['C']}/44",
           f"- accepted (iv): A/B {diag['accepted']['AB']}, C {diag['accepted']['C']}",
           f"- integrity fail: A/B {diag['integrity_fail']['AB']}, C {diag['integrity_fail']['C']} (F2c)",
           f"- trend fail: A/B {diag['trend_fail']['AB']}, C {diag['trend_fail']['C']}",
           f"- first hard fail by grade: `{json.dumps(diag['hard_first_fail'], sort_keys=True)}`", "",
           "No outcome fields anywhere (F7/E4)."]
    with open(os.path.join(OUT, "CENSUS_DR3_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"records {len(recs)} evaluated {len(ev)} accepted {len(acc)} rejected {len(rej)}")
    print(f"cadence {len(ex)} = {cad['per_week']}/week -> {verdict}")
    print("funnel:", dict(funnel))
    print("per_year:", dict(per_year), "per_session:", dict(per_session))
    print("burned:", json.dumps(diag, sort_keys=True))
    print("[write]", OUT)


if __name__ == "__main__":
    main()
