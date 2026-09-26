"""ab_engine.py — paired engine-level A/B (R19 §19.3 item 2).

Arm OFF: PerceptionEngine with shipped params (level.defended_origin
=false).  Arm ON: identical params except the flag.  Same code state,
same 198 TUNE panels, ruler eval_v2 (50e11fd5).

Per arm:
  * born recall / precision per level family, plus trusted subset;
  * births per panel (level family and all objects);
  * clutter ratio = engine objects born in-window / golden objects;
  * live level objects at golden tau (median) — live clutter;
  * snapshot recall at tau = t0 + 10;
  * recall@k k=1,2,3 per family: live objects at tau ranked by the
    birth score recorded in cand_log ('born' outcome);
  * flicker: live level-set (LC+MINI ids) changes per hour on the bar
    grid inside [w0,w1].

--scoreboard flag_off|flag_on appends the canonical SCOREBOARD row
through evalcheck/scoreboard.measure (its own tau-truncated reruns).

Usage:
  python ab_engine.py [--limit N] [--save out.json]
  python ab_engine.py --scoreboard flag_on
"""

import argparse
import collections
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "linelab"))
sys.path.insert(0, _HERE)

import bars_cache  # noqa: E402
import eval as EV  # noqa: E402
import eval_v2 as E2  # noqa: E402
import common as C  # noqa: E402
import engine as ENG  # noqa: E402
import funnel as F  # noqa: E402

from anatomy_levels import TIER_A  # noqa: E402

LTYPES = E2.LEVEL_TYPES
LVSET = ("LEVEL_CARRIED", "MINI_LEVEL")


class FlagOn(ENG.PerceptionEngine):
    """Identical engine, level.defended_origin=True.  Flag OFF arm is
    the unmodified shipped default."""

    def __init__(self):
        p = ENG.load_params()
        p["level"]["defended_origin"] = True
        super().__init__(params=p)


class FlagV2(ENG.PerceptionEngine):
    """v2 (R24 §24.2): defended_origin ON + def_mini_off ON —
    defended LC births only; defended MINIs are skipped at typing."""

    def __init__(self):
        p = ENG.load_params()
        p["level"]["defended_origin"] = True
        p["level"]["def_mini_off"] = True
        super().__init__(params=p)


class FlagV2b(ENG.PerceptionEngine):
    """v2b (post-L10): defended_origin ON + def_all_lc ON — every
    defended birth is typed LEVEL_CARRIED; young-origin triggers still
    birth (as LC) instead of being skipped as in v2."""

    def __init__(self):
        p = ENG.load_params()
        p["level"]["defended_origin"] = True
        p["level"]["def_all_lc"] = True
        super().__init__(params=p)


class FamLedger(ENG.PerceptionEngine):
    """R25 §25.5 arm (b): per-family rate ledger only
    (salience.fam_ledger=True), level routes untouched."""

    def __init__(self):
        p = ENG.load_params()
        p["salience"]["fam_ledger"] = True
        super().__init__(params=p)


class FamLedgerV2(ENG.PerceptionEngine):
    """R25 §25.5 arm (c): per-family ledger + defended-origin LC-only
    (defended_origin + def_mini_off).  The zero-sum test winner."""

    def __init__(self):
        p = ENG.load_params()
        p["salience"]["fam_ledger"] = True
        p["level"]["defended_origin"] = True
        p["level"]["def_mini_off"] = True
        super().__init__(params=p)


class FamLedgerV2Lc2(ENG.PerceptionEngine):
    """Ceiling test (ROUND_L12 arm d2): famledger_v2 + the second LC
    slot — rate_level_carried=2 AND fam_rate_level_carried=2.  The
    per-kind cap binds first; the fam share alone changes nothing."""

    def __init__(self):
        p = ENG.load_params()
        p["salience"]["fam_ledger"] = True
        p["salience"]["fam_rate_level_carried"] = 2
        p["salience"]["rate_level_carried"] = 2
        p["level"]["defended_origin"] = True
        p["level"]["def_mini_off"] = True
        super().__init__(params=p)


ARMS = {"flag_on": FlagOn, "v2": FlagV2, "v2b": FlagV2b,
        "fam_ledger": FamLedger, "famledger_v2": FamLedgerV2,
        "lcshare2": FamLedgerV2Lc2}


def born_scores(e, m):
    """(kind, price, birth-minute) -> salience score from cand_log."""
    out = {}
    for cd in e.cand_log or []:
        if cd.get("outcome") != "born" or cd.get("price") is None:
            continue
        key = (cd["kind"], round(cd["price"], 1),
               int(m[min(cd["idx"], len(m) - 1)]))
        out[key] = cd.get("score", 0.0)
    return out


def obj_score(o, bs):
    """Birth score for an eng_objects record; 0 when unmatched."""
    return bs.get((o["type"], round(o.get("price", -9e9), 1),
                   o["t_birth"]), 0.0)


def eval_arm(cls, recs, days):
    rows = []
    for k, rec in enumerate(recs):
        day = days[rec["date"]]
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        e = EV.run_engine(cls, day["m"], day["t"], day["o"], day["h"],
                          day["l"], day["c"], w1)
        gobjs, _, _ = EV.gold_objects(rec)
        for g in gobjs:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
        g2 = [g for g in gobjs if E2.scorable(g, w0, w1)]
        eo2 = E2.eng_objects(e, day["m"], w0, w1)
        p2, _ = C.match_panel(g2, eo2, [], [], day["m"],
                              E2.match, E2.match_mark, E2.score)
        rows.append({"id": rec["id"], "date": rec["date"],
                     "w0": w0, "w1": w1, "gobjs": gobjs, "g2": g2,
                     "eo2": eo2, "p2": p2, "m": day["m"],
                     "bs": born_scores(e, day["m"]),
                     "cands": e.cand_log or []})
        if (k + 1) % 50 == 0:
            print("    %d/%d" % (k + 1, len(recs)), flush=True)
    return rows


def trusted_mask(r):
    """Golden object index -> trusted flag (V1 Tier-A excluded)."""
    out = []
    for g in r["g2"]:
        try:
            oi = r["gobjs"].index(g)
        except ValueError:
            oi = -1
        out.append(("%s#%d" % (r["id"], oi)) not in TIER_A)
    return out


def arm_stats(rows):
    """All arm metrics, per family and pooled."""
    res = {"born": collections.Counter(), "tot_born": [],
           "clutter_ratio": [], "live_tau": collections.defaultdict(list),
           "flicker": [], "snap": collections.Counter(),
           "snap_g": collections.Counter(),
           "fam_hit": collections.Counter(), "fam_g": collections.Counter(),
           "def_out": collections.Counter()}
    fam = {t: {"g": 0, "hit": 0, "tr_g": 0, "tr_hit": 0,
               "e": 0, "hit_e": 0,
               "rk": {k: [0, 0] for k in (1, 2, 3)},
               "rk_tr": {k: [0, 0] for k in (1, 2, 3)},
               "dayhit": collections.defaultdict(lambda: [0, 0]),
               "day": collections.defaultdict(lambda:
                                              {k: [0, 0]
                                               for k in (1, 2, 3)})}
           for t in LVSET}
    for r in rows:
        tr = trusted_mask(r)
        hg = {gi for gi, _ in r["p2"]}
        he = {ei for _, ei in r["p2"]}
        for gi, g in enumerate(r["g2"]):
            res["fam_g"][g["spec_type"]] += 1
            res["fam_hit"][g["spec_type"]] += gi in hg
        for cd in r["cands"]:
            if cd.get("route") == "defended_origin":
                res["def_out"][cd.get("outcome")] += 1
        n_born_in = sum(1 for o in r["eo2"]
                        if r["w0"] <= o["t_birth"] <= r["w1"])
        res["tot_born"].append(n_born_in)
        res["clutter_ratio"].append(n_born_in / len(r["g2"])
                                    if r["g2"] else np.nan)
        # flicker: live level-set changes per hour on the bar grid
        grid = [x for x in r["m"] if r["w0"] <= x <= r["w1"]]
        lev = [o for o in r["eo2"] if o["type"] in LVSET]
        prev, changes = None, 0
        for mm in grid:
            live = tuple(sorted(o["id"] for o in lev
                                if o["t_birth"] <= mm <= o["t1"]))
            if prev is not None and live != prev:
                changes += 1
            prev = live
        hours = max((r["w1"] - r["w0"]) / 60.0, 1e-9)
        res["flicker"].append(changes / hours)
        for o in r["eo2"]:
            if o["type"] in LVSET and r["w0"] <= o["t_birth"] <= r["w1"]:
                res["born"][o["type"]] += 1
        for ei, o in enumerate(r["eo2"]):
            if o["type"] in LVSET:
                fam[o["type"]]["e"] += 1
                fam[o["type"]]["hit_e"] += ei in he
        for gi, g in enumerate(r["g2"]):
            st = g["spec_type"]
            if st not in LVSET:
                continue
            F_ = fam[st]
            F_["g"] += 1
            F_["hit"] += gi in hg
            F_["dayhit"][r["date"]][0] += gi in hg
            F_["dayhit"][r["date"]][1] += 1
            if tr[gi]:
                F_["tr_g"] += 1
                F_["tr_hit"] += gi in hg
            if g.get("price") is None:
                continue
            tau = g["t0"] + 10
            gp = g["price"] * 1e4
            tol = E2.tol_px(g)
            live = [o for o in r["eo2"] if o["type"] == st
                    and o["t_birth"] <= tau <= o["t1"]]
            res["live_tau"][st].append(len(live))
            res["snap_g"][st] += 1
            res["snap"][st] += any(
                abs(o.get("price", -9e9) - gp) <= tol for o in live)
            order = sorted(live, key=lambda o: obj_score(o, r["bs"]),
                           reverse=True)
            for kk in (1, 2, 3):
                hit = any(abs(o.get("price", -9e9) - gp) <= tol
                          for o in order[:kk])
                F_["rk"][kk][0] += hit
                F_["rk"][kk][1] += 1
                F_["day"][r["date"]][kk][0] += hit
                F_["day"][r["date"]][kk][1] += 1
                if tr[gi]:
                    F_["rk_tr"][kk][0] += hit
                    F_["rk_tr"][kk][1] += 1
    return res, fam


def wilson(h, n, z=1.96):
    import math
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = h / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, ctr - half), min(1.0, ctr + half))


def report(tag, res, fam, npan):
    print("\n=== arm %s ===" % tag)
    print("births/panel: LC %.2f  MINI %.2f  all %.1f   clutter ratio"
          " med %.2f   flicker med %.2f ch/h"
          % (res["born"]["LEVEL_CARRIED"] / npan,
             res["born"]["MINI_LEVEL"] / npan,
             float(np.median(res["tot_born"])),
             float(np.nanmedian(res["clutter_ratio"])),
             float(np.median(res["flicker"]))))
    for typ in LVSET:
        f = fam[typ]
        p_, lo, hi = wilson(f["hit"], f["g"])
        prec = f["hit_e"] / f["e"] if f["e"] else 0
        tr = "%d/%d=%.3f" % (f["tr_hit"], f["tr_g"],
                             f["tr_hit"] / f["tr_g"] if f["tr_g"] else 0)
        print(" %-13s born recall %.3f [%.2f-%.2f] (%d/%d)  prec %.3f"
              "  trusted %s" % (typ, p_, lo, hi, f["hit"], f["g"],
                                prec, tr))
        lt = res["live_tau"][typ]
        sn = res["snap"][typ]
        sg = res["snap_g"][typ]
        print("   snapshot %.3f (%d/%d)   live@tau med %.1f"
              % (sn / sg if sg else 0, sn, sg,
                 float(np.median(lt)) if lt else 0))
        row = []
        for kk in (1, 2, 3):
            h, n = f["rk"][kk]
            p_, lo, hi = wilson(h, n)
            h2, n2 = f["rk_tr"][kk]
            p2, _, _ = wilson(h2, n2)
            row.append("k%d %.3f[%.2f-%.2f] tr %.3f"
                       % (kk, p_, lo, hi, p2))
        print("   recall@k: " + "  ".join(row))
    if res["def_out"]:
        tot = sum(res["def_out"].values())
        print(" defended_origin cand outcomes (%d):" % tot)
        for k_, v in sorted(res["def_out"].items(),
                            key=lambda kv: -kv[1]):
            print("   %-18s %d" % (k_, v))


def boot_ci(diffs):
    diffs = np.array(diffs)
    if not len(diffs):
        return None
    rng = np.random.default_rng(7)
    bs = [rng.choice(diffs, len(diffs)).mean() for _ in range(10000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(diffs.mean()), float(lo), float(hi), len(diffs)


def paired_diff(fam_a, fam_b, typ="LEVEL_CARRIED", kk=2, born=False):
    """Paired day-level diff (a - b) with a day bootstrap CI.
    born=True diffs the charter born-recall; else recall@k."""
    da = fam_a[typ]["dayhit"] if born else fam_a[typ]["day"]
    db = fam_b[typ]["dayhit"] if born else fam_b[typ]["day"]
    days = sorted(set(da) & set(db))
    diffs = []
    for d in days:
        if born:
            ha, na = da[d]
            hb, nb = db[d]
        else:
            ha, na = da[d][kk]
            hb, nb = db[d][kk]
        if na and nb:
            diffs.append(ha / na - hb / nb)
    return boot_ci(diffs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--save", default="")
    ap.add_argument("--scoreboard",
                    choices=["flag_off", "flag_on", "v2", "v2b",
                             "fam_ledger", "famledger_v2", "lcshare2"],
                    default="")
    ap.add_argument("--on", choices=["flag_on", "v2", "v2b",
                                     "fam_ledger", "famledger_v2",
                                     "lcshare2"],
                    default="flag_on",
                    help="second arm (first is always flag_off)")
    args = ap.parse_args()
    recs = bars_cache.tune_records()
    if args.limit:
        recs = recs[:args.limit]

    if args.scoreboard:
        import scoreboard as SB
        import pa_slots
        cls = ARMS.get(args.scoreboard, ENG.PerceptionEngine)
        eng_hash = F.code_hash(F.V1_FILES)
        ruler_hash = SB.file_hash(
            os.path.join(_PERC, "evalcheck", "eval_v2.py"))
        with pa_slots.slot("levellab-ab", timeout=600):
            row = SB.measure(cls, eng_hash, recs,
                             variant=args.scoreboard)
        import datetime
        utc = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%MZ")
        line = SB.append_row(utc, "v1", eng_hash, ruler_hash, row,
                             lane="levellab", variant=args.scoreboard)
        print(line)
        return

    days = bars_cache.days()
    tag2 = args.on
    print("arm flag_off ...", flush=True)
    rows_off = eval_arm(ENG.PerceptionEngine, recs, days)
    print("arm %s ..." % tag2, flush=True)
    rows_on = eval_arm(ARMS[tag2], recs, days)

    res_off, fam_off = arm_stats(rows_off)
    res_on, fam_on = arm_stats(rows_on)
    report("flag_off", res_off, fam_off, len(recs))
    report(tag2, res_on, fam_on, len(recs))

    print("\n=== keep-rule: per-family matched-object delta (%s-off) ==="
          % tag2)
    for st in sorted(set(res_off["fam_g"]) | set(res_on["fam_g"])):
        ho, go = res_off["fam_hit"][st], res_off["fam_g"][st]
        hn, gn = res_on["fam_hit"][st], res_on["fam_g"][st]
        flag = "  <-- loses >1" if ho - hn > 1 else ""
        print("  %-14s gold %3d  hit off %3d on %3d  (delta %+d)%s"
              % (st, go, ho, hn, hn - ho, flag))

    for lbl, kw in (("LC born recall", dict(born=True)),
                    ("MINI born recall", dict(typ="MINI_LEVEL",
                                              born=True)),
                    ("LC recall@2", dict()),
                    ("MINI recall@2", dict(typ="MINI_LEVEL"))):
        d = paired_diff(fam_on, fam_off, **kw)
        if d:
            weak = "  weak evidence (CI includes 0)" \
                if d[1] <= 0 <= d[2] else ""
            print("paired day-bootstrap %s (on-off): %.3f [%.3f, %.3f]"
                  " over %d days%s" % (lbl, d[0], d[1], d[2], d[3],
                                       weak))

    if args.save:
        def slim(rows, fam):
            return {"day": {t: {d: fam[t]["day"][d]
                                for d in fam[t]["day"]}
                            for t in LVSET}}
        json.dump({"off": slim(rows_off, fam_off),
                   "on": slim(rows_on, fam_on)},
                  open(args.save, "w", encoding="utf8"), default=str)
        print("saved", args.save)


if __name__ == "__main__":
    main()
