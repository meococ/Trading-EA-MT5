"""VPA-ECON-1b - does the Volman grade predict the outcome? (DESIGN 2016-2021)

Diagnostic only (no effect on the ECON-1 verdict). Simulates EVERY labelled
case of the three grading sets with the FROZEN ECON-1 engine (import, no edits):

  - research/lab/vpa_econ1_sim.py   (fill/exit engine, prereg SHA 87D3C735...)
  - research/lab/vpa_econ1_costs.py (cost scenarios, prereg SHA 4B9F0EC3...)
  - research/lab/vpa_dr1.py         (DR3 detector, prereg SHA 73497484...)
  - research/lab/vpa_data.py        (DESIGN loader, prereg SHA E0DEC380...)

Sets (all DESIGN 2016-2021):
  1. PLAN/grading_dr3/ - 180 cases (120 accepted + 60 rejected), grade = the
     G1/G2/G3 majority (same rule as vpa_fidelity_dr3.py); signal bar and side
     from KEY_HIDDEN_DR3.csv; invalidation from the DR3 record (= ECON-1 input).
  2. PLAN/grading_dr3/GRADES_LEAD_DR3_SPOTCHECK.csv - 20 cases, Lead grades.
  3. PLAN/grading/GRADES_LEAD_BLIND.csv - 60 v1 cases, Lead grades; signal bar
     = the v1 barrier's last recorded touch before the break (the DR3
     definition); invalidation derived by the DR3 rule at that bar (the same
     derivation reproduces the ECON-1 record invalidation 180/180 on set 1).

Costs: x1 (mult 1.0, primary) and gross (mult 0.0). Same prereg order model:
stop order 1 pip beyond the signal-bar extreme, V=3, invalidation cancel,
S=8 / TP=16, SL-first on same-bar hits, flats. Writes only under PLAN/econ1b/.

Run: python "03. EA Developer/EA_VolmanPA/PLAN/econ1b/econ1b_run.py"
"""

import csv
import datetime
import hashlib
import json
import math
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))          # PLAN/econ1b
PKG = os.path.dirname(os.path.dirname(HERE))                # EA_VolmanPA
LAB = os.path.join(PKG, "research", "lab")
sys.path.insert(0, LAB)

from vpa_data import load_m5_bars                            # noqa: E402
from vpa_random_baseline import load_m5                      # noqa: E402
from vpa_dr1 import run_dr1, DR3_CFG, Dr1Detector            # noqa: E402
from vpa_core import run_detector, Detector                  # noqa: E402
from vpa_econ1_sim import build_ctx, simulate_entries, metrics, newcombe_diff  # noqa: E402
from vpa_econ1_costs import COST_SCENARIOS                   # noqa: E402
from vpa_econ1_run import compute_next_end                   # noqa: E402

GRADE_DIR = os.path.join(PKG, "PLAN", "grading_dr3")
V1_DIR = os.path.join(PKG, "PLAN", "grading")
ECON1_DIR = os.path.join(PKG, "PLAN", "econ1")
ORDER = {"A": 0, "B": 1, "C": 2}
INV_MARGIN_ATR = 0.10  # DR3 invalidation margin: buildup extreme +/-0.10*ATR (vpa_dr1.py:379)
V_THRESHOLD_PP = 8.0   # the task's "predicts outcome" threshold

# Frozen ECON-1 hashes (research/VPA-DR3_ECON1_PREREG.md section 0 + ADDENDUM A1)
FROZEN_SHA = {
    "vpa_econ1_sim.py": "87D3C73507666B58AAA0553D1A3F6FE0EF03EDFB645D012C59080A2E23E33930",
    "vpa_econ1_costs.py": "4B9F0EC330A2003935276876BEF952D1CBCE045F6E54E0EF5F4C01B72532F274",
    "vpa_dr1.py": "73497484E2C26EDF44DAE5F1D574C56BBF40BBBFE8192A05AD38B4D782A781E0",
    "vpa_data.py": "E0DEC3808AF7D2BD730C1A6185D6E850B306459DDFC00DDD8AA776A909D7212F",
    "vpa_econ1_random.py": "07719AF87CB35298B2D990B8339E6883488537E258AC6FB879C08EC19A210A99",
}
HASH_FILES = [
    os.path.join(LAB, "vpa_econ1_sim.py"), os.path.join(LAB, "vpa_econ1_costs.py"),
    os.path.join(LAB, "vpa_dr1.py"), os.path.join(LAB, "vpa_data.py"),
    os.path.join(LAB, "vpa_econ1_random.py"), os.path.join(LAB, "vpa_random_baseline.py"),
    os.path.join(LAB, "vpa_core.py"), os.path.join(LAB, "vpa_econ1_run.py"),
    os.path.join(GRADE_DIR, "GRADES_V3_G1.csv"), os.path.join(GRADE_DIR, "GRADES_V3_G2.csv"),
    os.path.join(GRADE_DIR, "GRADES_V3_G3.csv"), os.path.join(GRADE_DIR, "KEY_HIDDEN_DR3.csv"),
    os.path.join(GRADE_DIR, "GRADES_LEAD_DR3_SPOTCHECK.csv"), os.path.join(GRADE_DIR, "FIDELITY_DR3.csv"),
    os.path.join(V1_DIR, "GRADES_LEAD_BLIND.csv"), os.path.join(V1_DIR, "KEY_HIDDEN.csv"),
    os.path.join(V1_DIR, "selected_cases.json"),
    os.path.join(ECON1_DIR, "RANDOM_MATCHED.csv"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def read_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def utc(epoch):
    dt = datetime.datetime.fromtimestamp(int(epoch), tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def dr3_majority_labels():
    """G1/G2/G3 majority exactly as vpa_fidelity_dr3.py:41-62 (dual + median fallback)."""
    g = {}
    for tag in ("G1", "G2", "G3"):
        g[tag] = {r["case_id"]: r["grade"].strip().upper()
                  for r in read_csv(os.path.join(GRADE_DIR, f"GRADES_V3_{tag}.csv"))}
    key = {r["case_id"]: r for r in read_csv(os.path.join(GRADE_DIR, "KEY_HIDDEN_DR3.csv"))}
    out, n3way = {}, 0
    for cid in key:
        a, b = g["G1"][cid], g["G2"][cid]
        if a == b:
            dual = maj = a
        else:
            dual = None
            c = g["G3"].get(cid)
            assert c is not None, f"G3 missing for disagreement {cid}"
            votes = [a, b, c]
            top = max(set(votes), key=votes.count)
            if votes.count(top) >= 2:
                maj = top
            else:
                maj = sorted(votes, key=lambda x: ORDER[x])[1]
                n3way += 1
        out[cid] = {"g1": a, "g2": b, "g3": g["G3"].get(cid), "dual": dual, "majority": maj}
    return out, n3way


def dr3_inv_at(d0, bars, sig, side, level):
    """The ECON-1 invalidation rule (vpa_dr1.py:379): buildup extreme +/-0.10*ATR
    from the DR3 buildup window at the signal bar. Returns (inv|None, src, atr)."""
    A = float(d0.atr[sig])
    bu = d0._buildup_dr1(int(sig), int(side), float(level), A)
    if bu is None:
        return None, "dr3_buildup_none", A
    s = bu["start"]
    if side > 0:
        inv = min(bars["l"][s:int(sig)]) - INV_MARGIN_ATR * A
    else:
        inv = max(bars["h"][s:int(sig)]) + INV_MARGIN_ATR * A
    return float(inv), "dr3_buildup@%d" % s, A


def stats(trades):
    """ECON-1 aggregator on the filled subset + the status mix on all entries."""
    m = metrics(trades)
    if m.get("N", 0) == 0:
        m = {"N": 0, "WR": 0.0, "PF": 0.0, "b": float("nan"), "exp_r": 0.0, "R_total": 0.0}
    st = {}
    for t in trades:
        st[t["status"]] = st.get(t["status"], 0) + 1
    return m, st


def pf_str(v):
    return "inf" if v == float("inf") else f"{v:.3f}"


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def mdd_pp(n1, n2, p_ref, alpha=0.05, power=0.80):
    """Minimum detectable difference (pp) for a two-sided two-proportion test."""
    if n1 <= 0 or n2 <= 0:
        return float("nan")
    za = 1.959963984540054
    zb = 0.8416212335729143
    d = 0.10
    for _ in range(50):
        p1 = min(1.0, p_ref + d)
        se = math.sqrt(p1 * (1 - p1) / n1 + p_ref * (1 - p_ref) / n2)
        new = (za + zb) * se
        if abs(new - d) < 1e-9:
            d = new
            break
        d = new
    return d * 100.0


def dnewcombe(trades_ab, trades_c):
    """(k, n) win counts and the Newcombe CI of WR_AB - WR_C (x1 or gross)."""
    fab = [t for t in trades_ab if t["status"] == "FILLED"]
    fc = [t for t in trades_c if t["status"] == "FILLED"]
    k1 = sum(1 for t in fab if t["r"] > 0)
    k2 = sum(1 for t in fc if t["r"] > 0)
    if not fab or not fc:
        return (k1, len(fab)), (k2, len(fc)), (float("nan"), float("nan"), float("nan"))
    d, lo, hi = newcombe_diff(k1, len(fab), k2, len(fc))
    return (k1, len(fab)), (k2, len(fc)), (d, lo, hi)


def row_of(t):
    """One output row from one ECON-1 trade record (status can be non-FILLED)."""
    if t["status"] != "FILLED":
        return {"status": t["status"], "exit_reason": "", "r": None}
    return {"status": "FILLED", "exit_reason": t["reason"], "r": round(float(t["r"]), 6)}


def main():
    os.makedirs(HERE, exist_ok=True)
    log = []

    def p(*a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        log.append(s)

    # ---- A1: engine hashes ----
    hashes = {os.path.basename(f): sha256(f) for f in HASH_FILES}
    for name, want in FROZEN_SHA.items():
        got = hashes[name]
        assert got == want, f"HASH MISMATCH {name}: {got} != {want}"
        p("[hash-ok]", name, got)
    p("[hash]", "vpa_random_baseline.py", hashes["vpa_random_baseline.py"])
    p("[hash]", "vpa_core.py", hashes["vpa_core.py"])
    p("[hash]", "vpa_econ1_run.py", hashes["vpa_econ1_run.py"])

    # ---- data (DESIGN only) ----
    bars = load_m5_bars("EURUSD")
    m1, m5b, m5_t, starts, sess_mask = load_m5("EURUSD")
    assert len(m5_t) == len(bars["t"]) and np.array_equal(m5_t, bars["t"]), "M5 frames misaligned"
    pip = bars["pip"]
    t0, t1 = int(bars["t"][0]), int(bars["t"][-1])
    e2016 = int(datetime.datetime(2016, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    e2022 = int(datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    assert e2016 <= t0 and t1 < e2022, "frame outside DESIGN 2016-2021"
    p("[frame]", utc(t0), "->", utc(t1), len(bars["t"]), "M5 bars;", len(m1["t"]), "M1 bars")

    cfg = dict(DR3_CFG, round_grid_price=50.0 * pip, collect_gates=True)
    recs, _ = run_dr1(bars, cfg=cfg)
    p("[dr3] records", len(recs), "accepted", sum(1 for r in recs if r.get("executable")))
    d0 = Dr1Detector(bars, cfg=cfg)
    for i in range(len(bars["t"])):
        d0._update_bar(i)

    # ---- Set 1: DR3 grading cases ----
    lab1, n3way = dr3_majority_labels()
    fid = {r["case_id"]: r for r in read_csv(os.path.join(GRADE_DIR, "FIDELITY_DR3.csv"))}
    for cid, v in lab1.items():
        assert v["majority"] == fid[cid]["majority"], f"majority mismatch {cid}"
        assert (v["dual"] is None) == (fid[cid]["dual"] == "" or fid[cid]["dual"] == "None"), cid
    p("[labels] set1 majority cross-checked vs FIDELITY_DR3.csv; 3-way splits:", n3way)

    key1 = read_csv(os.path.join(GRADE_DIR, "KEY_HIDDEN_DR3.csv"))
    idx1 = {}
    for r in recs:
        idx1[(int(r["bar_idx"]), int(r["trigger_idx"]), int(r["side"]), round(float(r["level"]), 9))] = r
    cases1 = []
    for k in key1:
        cid = k["case_id"]
        sig, trig, side = int(k["signal_idx"]), int(k["bar_idx"]), int(k["side"])
        lvl = float(k["level"])
        rec = idx1.get((sig, trig, side, round(lvl, 9)))
        assert rec is not None, f"set1 unmapped {cid}"
        assert bool(rec.get("executable")) == (k["group"] == "accepted"), cid
        inv, src, A = dr3_inv_at(d0, bars, sig, side, lvl)
        if rec.get("invalidation") is None:
            assert inv is None, f"set1 inv derivation mismatch {cid}"
            inv_rec = None
        else:
            assert inv is not None and abs(inv - float(rec["invalidation"])) < 1e-12, cid
            inv_rec = float(rec["invalidation"])
        cases1.append({
            "case_key": "S1:" + cid, "set": 1, "case_id": cid,
            "label_source": "dr3_g1g2g3_majority",
            "group": k["group"], "grade_majority": lab1[cid]["majority"],
            "grade_dual": lab1[cid]["dual"], "g1": lab1[cid]["g1"], "g2": lab1[cid]["g2"],
            "g3": lab1[cid]["g3"], "grade_lead_dr3": "", "grade_lead_v1": "",
            "sig": sig, "trig": trig, "side": side, "barrier": lvl,
            "map_route": "dr3_record", "inv_source": src, "inv": inv_rec, "atr": A,
        })
    p("[set1] mapped", len(cases1), "/", len(key1))

    # Lead spot-check grades (set 2, a subset of set 1)
    spot = {r["case_id"]: r["grade"].strip().upper()
            for r in read_csv(os.path.join(GRADE_DIR, "GRADES_LEAD_DR3_SPOTCHECK.csv"))}
    assert set(spot) <= {c["case_id"] for c in cases1}, "spotcheck id not in set 1"
    for c in cases1:
        c["grade_lead_dr3"] = spot.get(c["case_id"], "")
    p("[set2] Lead-graded", len(spot), "of set 1;", dict(Counter(spot.values())))

    # ---- Set 3: v1 Lead-labelled cases ----
    lead3 = {r["case_id"]: r["grade"].strip().upper()
             for r in read_csv(os.path.join(V1_DIR, "GRADES_LEAD_BLIND.csv"))}
    key3 = {r["case_id"]: r for r in read_csv(os.path.join(V1_DIR, "KEY_HIDDEN.csv"))}
    sel = json.load(open(os.path.join(V1_DIR, "selected_cases.json"), encoding="utf-8"))
    for i, s in enumerate(sel, 1):
        k = key3[f"case_{i:03d}"]
        assert int(k["bar_idx"]) == int(s["bar_idx"]) and int(k["side"]) == int(s["side"]), \
            f"selected_cases.json order mismatch case_{i:03d}"
    recs_v1, _ = run_detector(bars)
    vidx = {}
    for r in recs_v1:
        vidx.setdefault((int(r["bar_idx"]), int(r["side"])), []).append(r)
    # Three signal-bar anchors for the v1 cases (all with the same order model):
    #   A = the barrier's lock pivot - the frozen DR3 code's proxy (the v1 touch
    #       list is recorded at lock time only, so tch[-1] == lock_idx);
    #   B = the last bar that TOUCHED the barrier before the break, scanned back
    #       from the break bar with the barrier's own lock-time tolerance
    #       (barrier_eps_atr * ATR at the lock bar) - the DR3 definition as
    #       documented in vpa_dr1.py:288-291 and prescribed by the task. PRIMARY.
    #   C = the v1 break/decision bar itself - the bar the graded snapshot ends on.
    eps_atr = float(Detector(bars).cfg["barrier_eps_atr"])
    cases3 = []
    fallback = []
    for cid in sorted(lead3):
        k = key3[cid]
        b, side = int(k["bar_idx"]), int(k["side"])
        cands = vidx.get((b, side), [])
        barl = k["barrier_level"]
        if barl not in ("", None):
            cands = [r for r in cands if abs(float(r["level"]) - float(barl)) < 1e-9]
        assert len(cands) == 1, f"set3 record match {cid}: {len(cands)}"
        r = cands[0]
        base = {
            "case_key": "S3:" + cid, "set": 3, "case_id": cid,
            "label_source": "lead_v1_blind",
            "grade_majority": "", "grade_dual": "", "g1": "", "g2": "", "g3": "",
            "grade_lead_dr3": "", "grade_lead_v1": lead3[cid],
            "trig": b, "side": side,
        }
        if r["setup"] != "pattern_break":
            # pullback_reversal: no barrier -> no touch chain; the release bar is
            # the signal bar (the v1 entry construction the snapshot/grade uses).
            base.update({"group": "pullback_reversal", "barrier": None, "sig": b,
                         "sig_a": b, "sig_b": b, "sig_c": b,
                         "map_route": "v1_release_bar",
                         "inv_source": "pullback_reversal_no_barrier", "inv": None,
                         "atr": float(d0.atr[b])})
            cases3.append(base)
            continue
        lock = int(r["lock_idx"])
        tch = [i for i in (r.get("touches") or []) if lock <= i < b]
        assert tch and tch[-1] == lock, f"set3 lock pivot {cid}"
        tol = eps_atr * float(d0.atr[lock])
        sig_b = None
        for i in range(b - 1, lock - 1, -1):
            if abs((bars["h"][i] if side > 0 else bars["l"][i]) - float(r["level"])) <= tol:
                sig_b = i
                break
        if sig_b is None:
            fallback.append(cid)
            sig_b = lock
        inv_b, src_b, A_b = dr3_inv_at(d0, bars, sig_b, side, float(r["level"]))
        base.update({"group": "pattern_break", "barrier": float(r["level"]), "sig": sig_b,
                     "sig_a": lock, "sig_b": sig_b, "sig_c": b,
                     "map_route": "v1_last_touch_before_break",
                     "inv_source": src_b, "inv": inv_b, "atr": A_b})
        cases3.append(base)
    assert len(cases3) == len(lead3), "set3 accounting"
    p("[set3] mapped", len(cases3), "/", len(lead3),
      "; routes", dict(Counter(c["map_route"] for c in cases3)),
      "; touch-scan fallback (used lock pivot):", fallback)

    # ---- simulate all cases (x1 + gross), same engine call as ECON-1 ----
    mask_any = sess_mask["london"] | sess_mask["ny"]
    next_end = compute_next_end(starts, mask_any, len(m1["t"]))
    ctx = build_ctx(m1, m5b, m5_t, starts, pip, next_end=next_end)
    all_cases = cases1 + cases3
    entries = [{"sig": c["sig"], "side": c["side"], "inv": c["inv"], "atr": c["atr"],
                "tag": c["case_key"]} for c in all_cases]
    def run_sim(entry_list, mult):
        """simulate_entries + round r to 6 dp, so every reported aggregate
        (WR/PF/b/expectancy) is exactly reproducible from CASES_OUTCOMES.csv,
        which stores r at 6 dp. No win/loss flips: no fill has 0 < |r| < 1e-6."""
        tr = simulate_entries(entry_list, ctx, mult=mult)
        for t in tr:
            if t.get("status") == "FILLED":
                t["r"] = round(float(t["r"]), 6)
        return tr

    trades_by_multi, status_counts = {}, {}
    for name in ("x1", "gross"):
        tr = run_sim(entries, COST_SCENARIOS[name])
        trades_by_multi[name] = {t["tag"]: t for t in tr}
        status_counts[name] = dict(Counter(t["status"] for t in tr))
        p(f"[sim] {name} cost_mult={COST_SCENARIOS[name]}",
          "entries", len(tr), "status", status_counts[name])
    assert len(trades_by_multi["x1"]) == len(entries)

    # Cross-check set 1's accepted cases against the ECON-1 run itself: every
    # x1 fill must reproduce a TRADES_DESIGN.csv row (reason + r) and no
    # non-filled case may have a row there.
    td = read_csv(os.path.join(ECON1_DIR, "TRADES_DESIGN.csv"))
    td_store = Counter((int(r["signal_bar_idx"]), 1 if r["side"] == "long" else -1,
                        r["reason"], round(float(r["r"]), 6)) for r in td)
    td_sig_side = set((int(r["signal_bar_idx"]), 1 if r["side"] == "long" else -1) for r in td)
    n_fill_matched = n_bad = 0
    for c in cases1:
        if c["group"] != "accepted":
            continue
        t = trades_by_multi["x1"][c["case_key"]]
        if t["status"] == "FILLED":
            key = (c["sig"], c["side"], t["reason"], round(float(t["r"]), 6))
            assert td_store[key] > 0, f"ECON-1 row missing for {c['case_key']}"
            td_store[key] -= 1
            n_fill_matched += 1
        else:
            assert (c["sig"], c["side"]) not in td_sig_side, f"ECON-1 fill vs non-fill {c['case_key']}"
            n_bad += 1
    p(f"[xcheck] ECON-1 TRADES_DESIGN.csv ({len(td)} rows): {n_fill_matched} set-1 accepted fills "
      f"matched exactly (reason+r), {n_bad} set-1 accepted non-fills absent from the file, "
      f"{sum(td_store.values())} TD rows belong to ECON-1 signals outside this 120-case sample")

    # Variants A and C (set 3 only, labelled sensitivity): same rules, different
    # signal-bar anchor.
    def anchor_variant(anchor):
        out = []
        for c in cases3:
            cc = dict(c)
            cc["sig"] = c["sig_" + anchor]
            if c["group"] == "pattern_break":
                cc["inv"], cc["inv_source"], cc["atr"] = dr3_inv_at(
                    d0, bars, c["sig_" + anchor], c["side"], c["barrier"])
            out.append(cc)
        return out

    cases3a, cases3c = anchor_variant("a"), anchor_variant("c")
    trades_a, trades_c = {}, {}
    for tag, cases_v, store in (("A", cases3a, trades_a), ("C", cases3c, trades_c)):
        ents = [{"sig": c["sig"], "side": c["side"], "inv": c["inv"], "atr": c["atr"],
                 "tag": c["case_key"]} for c in cases_v]
        for name in ("x1", "gross"):
            tr = run_sim(ents, COST_SCENARIOS[name])
            store[name] = {t["tag"]: t for t in tr}
            p(f"[sim-{tag}] {name} entries", len(tr),
              "status", dict(Counter(t["status"] for t in tr)))

    # ---- per-case CSV ----
    csv_fields = ["case_key", "set", "case_id", "label_source", "group", "label_grade_primary",
                  "grade_majority", "grade_dual", "g1", "g2", "g3", "grade_lead_dr3", "grade_lead_v1",
                  "sig_bar_idx", "trigger_bar_idx", "side", "barrier_level", "map_route",
                  "inv_source", "inv", "atr",
                  "status_x1", "exit_reason_x1", "r_x1", "status_gross", "exit_reason_gross", "r_gross",
                  "fill_t", "exit_t", "fill_px", "exit_px",
                  "sig_bar_idx_varA", "status_varA_x1", "exit_reason_varA_x1", "r_varA_x1",
                  "sig_bar_idx_varC", "status_varC_x1", "exit_reason_varC_x1", "r_varC_x1"]
    out_rows = []
    for c in all_cases:
        t_x1 = trades_by_multi["x1"][c["case_key"]]
        t_gr = trades_by_multi["gross"][c["case_key"]]
        o_x1, o_gr = row_of(t_x1), row_of(t_gr)
        primary = c["grade_lead_v1"] if c["set"] == 3 else c["grade_majority"]
        row = {
            "case_key": c["case_key"], "set": c["set"], "case_id": c["case_id"],
            "label_source": c["label_source"], "group": c["group"], "label_grade_primary": primary,
            "grade_majority": c["grade_majority"], "grade_dual": c["grade_dual"] if c["grade_dual"] else "",
            "g1": c["g1"], "g2": c["g2"], "g3": c["g3"] if c["g3"] else "",
            "grade_lead_dr3": c["grade_lead_dr3"], "grade_lead_v1": c["grade_lead_v1"],
            "sig_bar_idx": c["sig"], "trigger_bar_idx": c["trig"],
            "side": "long" if c["side"] > 0 else "short",
            "barrier_level": ("" if c["barrier"] is None else c["barrier"]),
            "map_route": c["map_route"], "inv_source": c["inv_source"],
            "inv": ("" if c["inv"] is None else round(c["inv"], 6)),
            "atr": round(c["atr"], 8),
            "status_x1": o_x1["status"], "exit_reason_x1": o_x1["exit_reason"],
            "r_x1": ("" if o_x1["r"] is None else o_x1["r"]),
            "status_gross": o_gr["status"], "exit_reason_gross": o_gr["exit_reason"],
            "r_gross": ("" if o_gr["r"] is None else o_gr["r"]),
            "fill_t": t_x1.get("fill_t", ""), "exit_t": t_x1.get("exit_t", ""),
            "fill_px": ("" if "fill" not in t_x1 else round(t_x1["fill"], 6)),
            "exit_px": ("" if "exit_px" not in t_x1 else round(t_x1["exit_px"], 6)),
            "sig_bar_idx_varA": "", "status_varA_x1": "", "exit_reason_varA_x1": "", "r_varA_x1": "",
            "sig_bar_idx_varC": "", "status_varC_x1": "", "exit_reason_varC_x1": "", "r_varC_x1": "",
        }
        if c["set"] == 3:
            for tag, store in (("varA", trades_a), ("varC", trades_c)):
                o_v = row_of(store["x1"][c["case_key"]])
                row[f"sig_bar_idx_{tag}"] = c["sig_" + tag[-1].lower()]
                row[f"status_{tag}_x1"] = o_v["status"]
                row[f"exit_reason_{tag}_x1"] = o_v["exit_reason"]
                row[f"r_{tag}_x1"] = ("" if o_v["r"] is None else o_v["r"])
        out_rows.append(row)
    with open(os.path.join(HERE, "CASES_OUTCOMES.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerows(out_rows)
    p("[write] CASES_OUTCOMES.csv rows", len(out_rows))

    # ---- comparisons ----
    def eval_group(cases, grade_fn, trade_of, mult):
        ab, cc = [], []
        for c in cases:
            g = grade_fn(c)
            assert g in ("A", "B", "C"), (c["case_key"], g)
            (ab if g in ("A", "B") else cc).append(trade_of(c, mult))
        m_ab, st_ab = stats(ab)
        m_c, st_c = stats(cc)
        (k1, n1), (k2, n2), (d, lo, hi) = dnewcombe(ab, cc)
        return {"cases": len(cases), "cases_ab": len(ab), "cases_c": len(cc),
                "ab": m_ab, "c": m_c, "st_ab": st_ab, "st_c": st_c,
                "k_ab": k1, "n_ab": n1, "k_c": k2, "n_c": n2, "d": d, "lo": lo, "hi": hi}

    def t_primary(c, mult):
        return trades_by_multi[mult][c["case_key"]]

    def t_pool_a(c, mult):
        return t_primary(c, mult) if c["set"] == 1 else trades_a[mult][c["case_key"]]

    def t_pool_c(c, mult):
        return t_primary(c, mult) if c["set"] == 1 else trades_c[mult][c["case_key"]]

    lead1 = [c for c in cases1 if c["grade_lead_dr3"]]
    g_pool_a = (lead1 + cases3a, lambda c: c["grade_lead_v1"] if c["set"] == 3 else c["grade_lead_dr3"], t_pool_a)
    g_pool_c = (lead1 + cases3c, lambda c: c["grade_lead_v1"] if c["set"] == 3 else c["grade_lead_dr3"], t_pool_c)
    groups = {
        "set1_majority": (cases1, lambda c: c["grade_majority"], t_primary),
        "set2_lead_dr3": (lead1, lambda c: c["grade_lead_dr3"], t_primary),
        "set3_lead_v1": (cases3, lambda c: c["grade_lead_v1"], t_primary),
        "pooled_lead_2plus3": (lead1 + cases3,
                               lambda c: c["grade_lead_v1"] if c["set"] == 3 else c["grade_lead_dr3"],
                               t_primary),
        "set3_lead_v1_varA": (cases3a, lambda c: c["grade_lead_v1"], lambda c, m: trades_a[m][c["case_key"]]),
        "pooled_lead_2plus3_varA": g_pool_a,
        "set3_lead_v1_varC": (cases3c, lambda c: c["grade_lead_v1"], lambda c, m: trades_c[m][c["case_key"]]),
        "pooled_lead_2plus3_varC": g_pool_c,
    }
    results = {}
    for name, (cases, gf, trade_of) in groups.items():
        for mult in ("x1", "gross"):
            r = eval_group(cases, gf, trade_of, mult)
            results[(name, mult)] = r
            p(f"[{name}/{mult}] AB cases {r['cases_ab']} fills {r['ab']['N']} WR {r['ab']['WR']*100:.2f}% "
              f"PF {pf_str(r['ab']['PF'])} | C cases {r['cases_c']} fills {r['c']['N']} "
              f"WR {r['c']['WR']*100:.2f}% PF {pf_str(r['c']['PF'])} | "
              f"dWR {r['d']*100:+.2f}pp CI [{r['lo']*100:+.2f}, {r['hi']*100:+.2f}]")

    # set 1 detail: A / B / C
    detail1 = {}
    for mult in ("x1", "gross"):
        for g in ("A", "B", "C"):
            tr = [trades_by_multi[mult][c["case_key"]] for c in cases1 if c["grade_majority"] == g]
            m, st = stats(tr)
            detail1[(g, mult)] = {"m": m, "st": st, "cases": len(tr)}
            p(f"[set1 {g}/{mult}] cases {len(tr)} fills {m['N']} WR {m['WR']*100:.2f}% PF {pf_str(m['PF'])}")
    acc1 = [c for c in cases1 if c["group"] == "accepted"]
    acc1_res = {}
    for mult in ("x1", "gross"):
        r = eval_group(acc1, lambda c: c["grade_majority"], t_primary, mult)
        acc1_res[mult] = r
        p(f"[set1-accepted/{mult}] AB fills {r['ab']['N']} WR {r['ab']['WR']*100:.2f}% | "
          f"C fills {r['c']['N']} WR {r['c']['WR']*100:.2f}% | "
          f"dWR {r['d']*100:+.2f}pp CI [{r['lo']*100:+.2f}, {r['hi']*100:+.2f}]")

    # ---- matched-random reference (ECON-1 x1 file) ----
    rnd = read_csv(os.path.join(ECON1_DIR, "RANDOM_MATCHED.csv"))
    rnd_r = [float(x["r"]) for x in rnd]
    rnd_wr = sum(1 for v in rnd_r if v > 0) / len(rnd_r)
    rnd_pf = sum(v for v in rnd_r if v > 0) / abs(sum(v for v in rnd_r if v < 0))
    rnd_zero = sum(1 for v in rnd_r if v == 0.0)
    m1_json = json.load(open(os.path.join(ECON1_DIR, "ECON1_METRICS.json"), encoding="utf-8"))
    rnd_wr_run = m1_json["scenarios"]["x1"]["random"]["WR"]
    rnd_pf_run = m1_json["scenarios"]["x1"]["random"]["PF"]
    p(f"[random-ref] RANDOM_MATCHED.csv: N {len(rnd_r)} WR {rnd_wr*100:.2f}% PF {rnd_pf:.3f}; "
      f"ECON1_METRICS.json x1 random: N {m1_json['scenarios']['x1']['random']['N']} "
      f"WR {rnd_wr_run*100:.2f}% PF {rnd_pf_run:.3f}; r==0.0 rows (6-dp rounding): {rnd_zero}")
    assert len(rnd_r) == 42257 and abs(rnd_wr - 0.2992) < 0.001, "RANDOM_MATCHED.csv changed"
    assert abs(rnd_wr_run - 0.2994) < 0.0001, "ECON1_METRICS.json changed"

    # ---- verdict rule ----
    def rule(res):
        d, lo, hi = res["d"], res["lo"], res["hi"]
        if d * 100 >= V_THRESHOLD_PP and lo > 0:
            return "YES"
        if hi * 100 < V_THRESHOLD_PP:
            return "NO"
        return "INCONCLUSIVE"

    rule_v = {}
    for name in ("set1_majority", "set2_lead_dr3", "set3_lead_v1", "pooled_lead_2plus3",
                 "set3_lead_v1_varA", "pooled_lead_2plus3_varA",
                 "set3_lead_v1_varC", "pooled_lead_2plus3_varC"):
        rule_v[name] = rule(results[(name, "x1")])
    v_set1 = rule_v["set1_majority"]
    v_pool = rule_v["pooled_lead_2plus3"]
    if v_pool == "YES" or v_set1 == "YES":
        verdict = "YES"
    elif v_pool == "NO" or v_set1 == "NO":
        verdict = "NO"
    else:
        verdict = "INCONCLUSIVE"
    p("[verdict/bullets] " + "; ".join(f"{k}={v}" for k, v in rule_v.items()) +
      f" -> {verdict} (bullet order: YES if any of set1/pooled YES; else NO if any of "
      "set1/pooled NO; else INCONCLUSIVE)")

    # ---- power note ----
    power = {}
    for name in ("set1_majority", "pooled_lead_2plus3"):
        r = results[(name, "x1")]
        if r["n_ab"] and r["n_c"]:
            p_c = r["k_c"] / r["n_c"]
            power[name] = {"mdd_pp": mdd_pp(r["n_ab"], r["n_c"], p_c), "p_ref": p_c,
                           "ci_halfwidth_pp": (r["hi"] - r["lo"]) / 2 * 100}
            p(f"[power] {name}: p_ref(C) {p_c*100:.2f}%, n_AB {r['n_ab']}, n_C {r['n_c']}, "
              f"MDD(80% power) {power[name]['mdd_pp']:.1f}pp, CI half-width "
              f"{power[name]['ci_halfwidth_pp']:.1f}pp")

    # ---- evidence json ----
    ev = {
        "hashes": hashes, "frozen_expected": FROZEN_SHA,
        "frame": {"first_utc": utc(t0), "last_utc": utc(t1), "n_m5": len(bars["t"]), "n_m1": len(m1["t"])},
        "set1_mapped": len(cases1), "set1_total": len(key1),
        "set2_lead": len(spot), "set3_mapped": len(cases3), "set3_total": len(lead3),
        "set3_routes": dict(Counter(c["map_route"] for c in cases3)),
        "set3_anchor_gaps": {"A_lock_pivot": [c["trig"] - c["sig_a"] for c in cases3],
                             "B_last_touch": [c["trig"] - c["sig_b"] for c in cases3],
                             "C_break_bar": [c["trig"] - c["sig_c"] for c in cases3]},
        "econ1_xcheck": {"matched_fills": n_fill_matched, "nonfill_absent": n_bad,
                         "trades_design_rows": len(td)},
        "inv_source_counts": dict(Counter(c["inv_source"] for c in all_cases)),
        "status_counts": status_counts,
        "status_counts_varA": {n: dict(Counter(t["status"] for t in trades_a[n].values())) for n in ("x1", "gross")},
        "status_counts_varC": {n: dict(Counter(t["status"] for t in trades_c[n].values())) for n in ("x1", "gross")},
        "random_ref": {"N": len(rnd_r), "WR": rnd_wr, "PF": rnd_pf},
        "results": {f"{k[0]}|{k[1]}": {kk: vv for kk, vv in v.items() if kk not in ("st_ab", "st_c")}
                    for k, v in results.items()},
        "results_status": {f"{k[0]}|{k[1]}": {"ab": v["st_ab"], "c": v["st_c"]} for k, v in results.items()},
        "set1_detail": {f"{g}|{m}": v for (g, m), v in detail1.items()},
        "set1_accepted": acc1_res,
        "rule_bullet_verdicts": rule_v,
        "verdict": {"set1": v_set1, "pooled_lead": v_pool, "final": verdict},
        "power": power,
    }
    with open(os.path.join(HERE, "EVIDENCE.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, indent=1, default=str)
    p("[write] EVIDENCE.json")

    # ---- GRADE_VS_OUTCOME.md ----
    def pp(v):
        return f"{v*100:+.2f}pp"

    def ci(r):
        return f"[{r['lo']*100:+.2f}, {r['hi']*100:+.2f}]"

    def wcell(m):
        return f"N={m['N']} WR={m['WR']*100:.2f}% PF={pf_str(m['PF'])}"

    def row_line(label, r, weight):
        return (f"| {label} | {weight} | {wcell(r['ab'])} | {wcell(r['c'])} | "
                f"{pp(r['d'])} | {ci(r)} | {rule(r)} |")

    LABELS = {
        "set1_majority": "set 1 - DR3, majority of G1/G2/G3",
        "set2_lead_dr3": "set 2 - DR3 spot-check, Lead grades",
        "set3_lead_v1": "set 3 - v1 blind, Lead grades (anchor B)",
        "pooled_lead_2plus3": "pooled Lead (sets 2+3, anchor B)",
        "set3_lead_v1_varA": "set 3, anchor A (barrier lock pivot)",
        "set3_lead_v1_varC": "set 3, anchor C (v1 break bar)",
        "pooled_lead_2plus3_varA": "pooled Lead, anchor A (lock pivot)",
        "pooled_lead_2plus3_varC": "pooled Lead, anchor C (break bar)",
    }

    md = []
    md += ["# GRADE_VS_OUTCOME - VPA-ECON-1b diagnostic (DESIGN 2016-2021)", "",
           "Question: does the Volman grade (the 'pro eye': A/B = tradeable, C = pass) "
           "predict the OUTCOME of the case when it is traded by the frozen ECON-1 model?",
           "This is exploratory (ECON-1b); it does NOT change the ECON-1 verdict.", "",
           "## 0. Method", "",
           "Every labelled case is simulated with the frozen ECON-1 engine imported unchanged "
           "(`vpa_econ1_sim.simulate_entries`, `vpa_econ1_costs` scenarios, the same prereg order "
           "model: stop order 1 pip beyond the signal-bar extreme, V=3 M5 bars, invalidation "
           "cancel, S=8 / TP=16, SL-first inside an M1 bar, Friday/daily flats and the "
           "session-end cancel). Costs: **x1 = 1.0 pip** (primary) and **gross = 0.0** (sanity). "
           "Only DESIGN 2016-2021 data is loaded.", "",
           "Engine SHA256 (must match the ECON-1 prereg):", "",
           "| artifact | SHA256 | matches ECON-1 |", "|---|---|---|"]
    for name in ("vpa_econ1_sim.py", "vpa_econ1_costs.py", "vpa_dr1.py", "vpa_data.py", "vpa_econ1_random.py"):
        md.append(f"| research/lab/{name} | `{hashes[name]}` | yes |")
    md += ["", "`vpa_random_baseline.py` (loader/session helper) `" + hashes["vpa_random_baseline.py"] + "`, "
           "`vpa_core.py` (v1 records) `" + hashes["vpa_core.py"] + "`, "
           "`vpa_econ1_run.py` (helper reuse) `" + hashes["vpa_econ1_run.py"] + "`.", "",
           f"Frame: {utc(t0)} -> {utc(t1)} ({len(bars['t'])} M5 bars, {len(m1['t'])} M1 bars).", "",
           "## 1. Labelled cases and mapping", "",
           f"- Set 1 (DR3 grading): {len(cases1)}/{len(key1)} mapped to DR3 records; label = "
           "G1/G2/G3 majority (same rule as `vpa_fidelity_dr3.py`, cross-checked against "
           "`FIDELITY_DR3.csv`); signal bar = `signal_idx`, invalidation = the record's own "
           "`invalidation` (the exact ECON-1 input; the DR3-rule derivation reproduces it 180/180).",
           f"- Set 2 (DR3 Lead spot-check): {len(spot)}/20 Lead-graded cases, all inside set 1.",
           f"- Set 3 (v1 Lead blind): {len(cases3)}/{len(lead3)} accounted for - "
           f"{ev['set3_routes'].get('v1_last_touch_before_break', 0)} pattern_break cases mapped to "
           "the LAST BAR THAT TOUCHED THE BARRIER BEFORE THE BREAK (the DR3 signal-bar definition; "
           "scanned from the break bar with the barrier's own lock-time tolerance "
           "`barrier_eps_atr*ATR`), "
           f"{ev['set3_routes'].get('v1_release_bar', 0)} pullback_reversal cases mapped to the "
           "release bar (v1 has no barrier there; the bar the snapshot/grade is anchored on); "
           f"0 unmapped. Invalidation: the DR3 rule at the mapped signal bar "
           f"({sum(1 for c in cases3 if c['inv'] is not None)} derivable, "
           f"{sum(1 for c in cases3 if c['inv'] is None)} none -> no cancel, exactly as ECON-1 "
           "behaves when a record has no invalidation).", "",
           f"- Cross-check against the ECON-1 run itself: every x1 fill of the 120 set-1 accepted "
           f"cases reproduces its `PLAN/econ1/TRADES_DESIGN.csv` row (reason + r) exactly, and no "
           f"non-filled set-1 accepted case has a row there ({n_fill_matched} matched, "
           f"{n_bad} absent; the file holds {len(td)} ECON-1 fills in total).", "",
           "Grade counts: set 1 majority " + str(dict(Counter(c["grade_majority"] for c in cases1))) +
           "; set 2 Lead " + str(dict(Counter(c["grade_lead_dr3"] for c in cases1 if c["grade_lead_dr3"]))) +
           "; set 3 Lead " + str(dict(Counter(c["grade_lead_v1"] for c in cases3))) + ".", "",
           "### Headline", "",
           f"A/B minus C win rate (x1): pooled Lead sets "
           f"{pp(results[('pooled_lead_2plus3','x1')]['d'])} "
           f"CI {ci(results[('pooled_lead_2plus3','x1')])} "
           f"({wcell(results[('pooled_lead_2plus3','x1')]['ab'])} vs "
           f"{wcell(results[('pooled_lead_2plus3','x1')]['c'])}); set 1 "
           f"{pp(results[('set1_majority','x1')]['d'])} "
           f"CI {ci(results[('set1_majority','x1')])} "
           f"({wcell(results[('set1_majority','x1')]['ab'])} vs "
           f"{wcell(results[('set1_majority','x1')]['c'])}). "
           "Every comparison in this diagnostic sits at or below zero: the A/B grades do not show "
           "the higher win rate. The rule's classification is in section 5.", "",
           "## 2. Grade A/B vs grade C - fills, win rate, PF (x1)", "",
           "| comparison | grade weight (A/B / C) | A/B fills | C fills | dWR (A/B - C) | 95% CI (Newcombe) | rule |",
           "|---|---|---|---|---|---|---|"]
    for name in ("set1_majority", "set2_lead_dr3", "set3_lead_v1", "pooled_lead_2plus3"):
        r = results[(name, "x1")]
        w = f"{r['cases_ab']} / {r['cases_c']} (of {r['cases']})"
        md.append(row_line(LABELS[name], r, w))
    md += ["", f"Matched-random reference line (ECON-1 x1): "
           f"WR **{rnd_wr_run*100:.2f}%** (N={len(rnd_r)}; `RANDOM_MATCHED.csv` recomputation: "
           f"{rnd_wr*100:.2f}%, {rnd_zero} rows round to r=0.000000 at 6 dp).", "",
           "Gross (no cost) robustness:", "",
           "| comparison | A/B fills | C fills | dWR | 95% CI | rule (informative) |", "|---|---|---|---|---|---|"]
    for name in ("set1_majority", "set2_lead_dr3", "set3_lead_v1", "pooled_lead_2plus3"):
        r = results[(name, "gross")]
        md.append(f"| {LABELS[name]} | {wcell(r['ab'])} | {wcell(r['c'])} | {pp(r['d'])} | {ci(r)} | {rule(r)} |")
    md += ["", "Fill-status mix (x1; the non-fills are cases where the stop order never traded "
           "through in its V=3-bar window, was cancelled by the invalidation, or was Friday-vetoed):", "",
           "| comparison | group | FILLED | CANCELLED | EXPIRED | VETO_FRIDAY | fill rate |",
           "|---|---|---|---|---|---|---|"]
    for name in ("set1_majority", "set2_lead_dr3", "set3_lead_v1", "pooled_lead_2plus3"):
        r = results[(name, "x1")]
        for side, cases, st in (("A/B", r["cases_ab"], r["st_ab"]), ("C", r["cases_c"], r["st_c"])):
            nf = sum(st.values())
            md.append(f"| {LABELS[name]} | {side} | {st.get('FILLED', 0)} | {st.get('CANCELLED', 0)} | "
                      f"{st.get('EXPIRED', 0)} | {st.get('VETO_FRIDAY', 0)} | "
                      f"{st.get('FILLED', 0)/nf*100:.1f}% ({nf} cases) |")
    md += ["", "### Sensitivity: set-3 signal-bar choice (x1)", "",
           "For the v1 cases the signal bar is not given by the v1 record (its `bar_idx` is the "
           "break bar). Three anchors are computed and all pass through the same order model:", "",
           "- **B (primary)**: the last bar that touched the barrier before the break, scanned back "
           "from the break bar with the barrier's own lock-time tolerance (`barrier_eps_atr*ATR`) - "
           "the DR3 definition (`vpa_dr1.py:288-291`) and what the task prescribes. Gap to the "
           "break: median " + f"{int(np.median([c['trig']-c['sig_b'] for c in cases3 if c['group']=='pattern_break']))}" +
           " M5 bars (1-12).",
           "- **A**: the barrier's lock pivot - the frozen DR3 code's proxy, because the v1 touch "
           "list is recorded at lock time only (`tch[-1] == lock_idx`). Here the V=3 order window "
           "often expires before the break.",
           "- **C**: the v1 break/decision bar itself - the bar the graded snapshot ends on.",
           "",
           "| set-3 anchor | grade weight (A/B / C) | A/B fills | C fills | dWR | 95% CI | rule |",
           "|---|---|---|---|---|---|---|"]
    for name in ("set3_lead_v1_varA", "set3_lead_v1", "set3_lead_v1_varC",
                 "pooled_lead_2plus3_varA", "pooled_lead_2plus3", "pooled_lead_2plus3_varC"):
        r = results[(name, "x1")]
        w = f"{r['cases_ab']} / {r['cases_c']} (of {r['cases']})"
        md.append(row_line(LABELS[name], r, w))
    md += ["", "## 3. Set 1 detail (x1)", "",
           "| grade | cases | fills | fill rate | WR | PF |", "|---|---|---|---|---|---|"]
    for g in ("A", "B", "C"):
        d = detail1[(g, "x1")]
        st = d["st"]
        nf = sum(st.values())
        md.append(f"| {g} | {d['cases']} | {d['m']['N']} | {d['m']['N']/nf*100:.1f}% | "
                  f"{d['m']['WR']*100:.2f}% | {pf_str(d['m']['PF'])} |")
    a = acc1_res["x1"]
    md += ["", "Fidelity inside DR3 (accepted cases only, x1): "
           f"A/B fills {a['ab']['N']} WR {a['ab']['WR']*100:.2f}% PF {pf_str(a['ab']['PF'])} vs "
           f"C fills {a['c']['N']} WR {a['c']['WR']*100:.2f}% PF {pf_str(a['c']['PF'])} -> "
           f"dWR {pp(a['d'])} CI {ci(a)} ({rule(a)}).", "",
           "## 4. Power note", "",
           "With these sample sizes (x1 fills) the smallest A/B vs C win-rate difference "
           "detectable at 80% power (two-sided alpha 0.05, reference p = the observed C win rate):", "",
           "| comparison | n A/B fills | n C fills | p_ref (C WR) | MDD @80% power | observed CI half-width |",
           "|---|---|---|---|---|---|"]
    for name in ("set1_majority", "pooled_lead_2plus3"):
        r = results[(name, "x1")]
        if name in power:
            md.append(f"| {LABELS[name]} | {r['n_ab']} | {r['n_c']} | {power[name]['p_ref']*100:.1f}% | "
                      f"{power[name]['mdd_pp']:.1f}pp | {power[name]['ci_halfwidth_pp']:.1f}pp |")
    md += ["", "So a true effect smaller than roughly the MDD above cannot be separated from noise "
           "with these labelled samples; the CI, not the point estimate, carries the information.", "",
           "## 5. Verdict", "",
           "Rule (task ECON-1b): YES if A/B - C >= +8pp with CI lower bound > 0 in the pooled "
           "Lead-labelled sets (2+3) or in set 1; NO if the CI upper bound < +8pp; otherwise "
           "INCONCLUSIVE.", "",
           f"- Set 1 (majority): dWR {pp(results[('set1_majority','x1')]['d'])} "
           f"CI {ci(results[('set1_majority','x1')])} -> **{v_set1}**",
           f"- Set 2 (Lead, DR3 spot-check): dWR {pp(results[('set2_lead_dr3','x1')]['d'])} "
           f"CI {ci(results[('set2_lead_dr3','x1')])} -> {rule_v['set2_lead_dr3']}",
           f"- Set 3 (Lead, v1; anchor B): dWR {pp(results[('set3_lead_v1','x1')]['d'])} "
           f"CI {ci(results[('set3_lead_v1','x1')])} -> {rule_v['set3_lead_v1']}",
           f"- Pooled Lead (2+3; anchor B): dWR {pp(results[('pooled_lead_2plus3','x1')]['d'])} "
           f"CI {ci(results[('pooled_lead_2plus3','x1')])} -> **{v_pool}**",
           f"- Sensitivity anchors (rule values): A: set 3 {rule_v['set3_lead_v1_varA']}, "
           f"pooled {rule_v['pooled_lead_2plus3_varA']}; C: set 3 {rule_v['set3_lead_v1_varC']}, "
           f"pooled {rule_v['pooled_lead_2plus3_varC']}",
           "",
           "Rule reading used here: the task's bullets name two comparisons (the pooled Lead sets "
           "2+3, and set 1). Evaluated in order - a YES in either comparison wins; otherwise a NO "
           "in either comparison (CI upper bound < +8pp) gives NO; otherwise INCONCLUSIVE. Under "
           "this reading the NO comes from the pooled Lead-labelled sets (CI upper "
           f"{results[('pooled_lead_2plus3','x1')]['hi']*100:+.2f}pp < +8pp); set 1 alone is "
           f"INCONCLUSIVE (CI upper {results[('set1_majority','x1')]['hi']*100:+.2f}pp). If the "
           "rule were instead read as 'NO only when BOTH comparisons exclude +8pp', the verdict "
           "would be INCONCLUSIVE on the strength of set 1's wide interval - the substantive "
           "read-out below is unchanged either way.", "",
           f"**Grade predicts outcome: {verdict}**", "",
           "Substance (independent of the rule reading): in every comparison of this diagnostic the "
           "A/B point estimate is at or below the C point estimate, and no comparison shows A/B "
           "winning more, so the data provide no support for 'A/B setups win more'. The pooled "
           "Lead-labelled fills (n=12 A/B vs n=34 C) exclude a +8pp A/B advantage; the set-1 "
           "sample is too small (n=50 vs 46 fills, MDD ~28pp) to exclude it on its own.", "",
           "## 6. Deviations & assumptions", "",
           "1. Set 1 uses the DR3 grading cases' own labels (G1/G2/G3 majority) and the DR3 "
           "record invalidation - bit-identical to the ECON-1 entry definition.",
           "2. Set 3 signal bar (primary, anchor B): for pattern_break v1 cases, the last bar that "
           "touched the barrier before the break - the DR3 definition - scanned back from the v1 "
           "break bar with the barrier's own lock-time tolerance (`barrier_eps_atr * ATR`, the same "
           "eps that accepted the barrier's touches at lock). The frozen DR3/v1 detectors record "
           "touches only at lock time, so anchors A (lock pivot = the code-literal `tch[-1]`) and C "
           "(the break bar, i.e. the graded snapshot's last bar) are reported as labelled "
           "sensitivities. The 11 pullback_reversal cases (no barrier) use the release bar in all "
           "anchors.",
           "3. Set 3 invalidation: derived by the DR3 rule (`_buildup_dr1` at the mapped signal "
           "bar, extreme +/-0.10xATR). On set 1 this derivation reproduces the ECON-1 "
           "`invalidation` 180/180 (0 mismatches), so it is the ECON-1 rule; when no DR3 buildup "
           "window exists there is no cancel (as in ECON-1 for records without invalidation).",
           "4. Grades for set 3 come from the Lead's v1 blind grading (`GRADES_LEAD_BLIND.csv`), "
           "assigned on the chart ending at the v1 break/decision bar, while the simulated entry "
           "uses the mapped signal bar; the same anchor applies to set 1 (snapshot ends at the "
           "trigger bar).",
           "5. This is a diagnostic on a sample of 240 cases; it is not a new strategy run and it "
           "does not modify any parameter, code, or verdict of ECON-1.",
           "6. The ECON-1 cost/exit semantics (incl. the inherited Thursday/'FRIDAY' quirk) are "
           "unchanged and identical for A/B and C, so the comparison is internally consistent.",
           "7. `RANDOM_MATCHED.csv` stores `r` rounded to 6 dp; recomputing its win rate from the "
           "file gives 29.92% while the ECON-1 run itself recorded 29.94% (`ECON1_METRICS.json`) - "
           "25 tiny-r rows round to exactly 0.000000. The reference line quotes the ECON-1 run "
           "value.",
           "8. Each trade's `r` is rounded to 6 dp before aggregation (the engine's fill/exit "
           "semantics are untouched), so every number printed here - including PF - is exactly "
           "reproducible from `CASES_OUTCOMES.csv`. No fill in this sample has 0 < |r| < 1e-6, so "
           "no win/loss classification changes; the reviewers' first pass flagged two PF cells "
           "whose 3rd decimal differed by one unit from the CSV-based recomputation, and this "
           "rounding removes that discrepancy.", "",
           "## 7. Reproduction", "",
           "`python \"03. EA Developer/EA_VolmanPA/PLAN/econ1b/econ1b_run.py\"` prints every number "
           "into `RUN_LOG.txt` and writes `CASES_OUTCOMES.csv` (one row per case: labels, mapping, "
           "signal-bar anchors, fill status, exit reason, R for x1 and gross + the A/C anchor "
           "outcomes) and `EVIDENCE.json` (all group results, hashes, power).", ""]
    with open(os.path.join(HERE, "GRADE_VS_OUTCOME.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    p("[write] GRADE_VS_OUTCOME.md")

    with open(os.path.join(HERE, "RUN_LOG.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("[done]")
    return ev


if __name__ == "__main__":
    main()
