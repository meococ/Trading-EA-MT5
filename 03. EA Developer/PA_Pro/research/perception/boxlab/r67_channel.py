"""r67_channel.py — R67 s.67.4: episode-container birth channel (EC).

Three pre-registered causal triggers (BOX_RESEARCH.md R67 prereg):

  EC-A session_range : at first bar m>=420, box = [min l,max h] of the
      day's bars with m in [0,420).  1 birth/date.
  EC-B spike_base    : spike |c[i]-c[i-6]| >= 2.0*ABR[i]; i_s = extreme
      bar of the move; base = bars [i_s, i_s+8]; birth at i_s+8 iff
      4p <= height <= 60p; 12-bar cooldown.
  EC-C first_block   : leg |c[i]-c[i-6]| >= 1.5*ABR[i]; first run of
      >=8 consecutive bars after the leg with per-bar range <= 1.0*ABR;
      birth at run end iff 4p <= height <= 60p; one birth per leg.

Object semantics (hypothetical ruler record):
  {type:BOX, lo, hi (pips), t0=m[start_bar], t1=tau (live), w0,w1}
  -> coverage/IoU fallback routes govern (no bs/be recorded).

Death model for the 'live' count: a box dies at the first bar after
birth whose CLOSE is outside [lo,hi] (c < lo or c > hi).
Reach reported both ways: born<=tau (R65 convention) and live-at-tau.
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
from snapshot import tau_of            # noqa: E402

PIP = 1e4

A_END = 420          # session_range: Asia window [0, 420) minutes
K = 6                # spike_base: spike lookback bars
S = 2.0              # spike_base: spike size in ABR
M = 8                # spike_base: absorption bars (incl. spike bar)
G = 12               # spike_base: cooldown bars after a birth
N = 6                # first_block: leg length bars
L = 1.5              # first_block: leg displacement in ABR
B = 8                # first_block: sideways-run length
X = 1.0              # first_block: quiet-bar range cap in ABR
HMIN, HMAX = 4.0, 60.0   # B/C height gate, pips


def ec_births(m, hp, lp, cp, abr):
    nb = len(m)
    cands = []

    # EC-A: session_range -------------------------------------------------
    day_idx = [i for i in range(nb) if 0 <= m[i] < A_END]
    if day_idx:
        born = next((i for i in range(nb) if m[i] >= A_END), None)
        if born is not None:
            cands.append(dict(trigger="session_range",
                              lo=float(min(lp[i] for i in day_idx)),
                              hi=float(max(hp[i] for i in day_idx)),
                              t0=day_idx[0], born=born))

    # EC-B: spike_base ----------------------------------------------------
    last_birth = -10**9
    for i in range(K, nb):
        a = abr[i] if i < len(abr) else 5.0
        if i - last_birth < G or abs(cp[i] - cp[i - K]) < S * a:
            continue
        up = cp[i] > cp[i - K]
        seg = range(i - K, i + 1)
        i_s = max(seg, key=lambda j: hp[j]) if up else \
            min(seg, key=lambda j: lp[j])
        e1 = min(i_s + M, nb - 1)
        if e1 <= i_s:
            continue
        lo = float(min(lp[i_s:e1 + 1]))
        hi = float(max(hp[i_s:e1 + 1]))
        if not (HMIN <= hi - lo <= HMAX):
            continue
        cands.append(dict(trigger="spike_base", lo=lo, hi=hi,
                          t0=i_s, born=e1))
        last_birth = e1

    # EC-C: first_block ---------------------------------------------------
    last_leg_end = -10**9
    i = N
    while i < nb:
        a = abr[i] if i < len(abr) else 5.0
        if abs(cp[i] - cp[i - N]) >= L * a and i > last_leg_end:
            run = 0
            j = i + 1
            while j < nb:
                aj = abr[j] if j < len(abr) else 5.0
                if hp[j] - lp[j] <= X * aj:
                    run += 1
                    if run >= B:
                        lo = float(min(lp[j - B + 1:j + 1]))
                        hi = float(max(hp[j - B + 1:j + 1]))
                        if HMIN <= hi - lo <= HMAX:
                            cands.append(dict(trigger="first_block",
                                              lo=lo, hi=hi,
                                              t0=j - B + 1, born=j))
                        last_leg_end = j
                        break
                    j += 1
                else:
                    break
            i = max(j + 1, i + 1)
        else:
            i += 1
    return cands


def live_at(cd, j_tau, cp):
    if cd["born"] > j_tau:
        return False
    seg = cp[cd["born"] + 1:j_tau + 1]
    return not ((seg > cd["hi"]) | (seg < cd["lo"])).any()


def gkey(panel, tau, g):
    return (panel, int(round(tau)),
            round(g["price_lo"] * PIP, 1), round(g["price_hi"] * PIP, 1))


def main():
    recs = C.load_tune()
    rows = pickle.load(open(
        os.path.join(PERC, "deepresearch", "dr_rows.pkl"), "rb"))
    unreach_keys = set()
    for r in rows:
        if r["n_match"] == 0:
            unreach_keys.add((r["panel"], int(round(r["tau"])),
                              round(r["g_lo"], 1), round(r["g_hi"], 1)))

    trig_names = ["session_range", "spike_base", "first_block", "union"]
    reach_b = {t: set() for t in trig_names}
    reach_l = {t: set() for t in trig_names}
    births_by_panel = []
    live_counts = []        # live channel objects at each golden's tau
    hits_detail = []
    n_all = n_un = 0

    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        hp, lp, cp = h, l, c          # cache bars are already pip-scale
        gobjs, _u, _to = EV.gold_objects(rec)
        golds = []
        for g in gobjs:
            if g["spec_type"] not in V2.BOX_TYPES or \
                    not V2.scorable(g, w0, w1):
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            golds.append((g, min(tau, w1)))
        if not golds:
            continue

        cands = ec_births(m, hp, lp, cp, abr)
        nb_in = sum(1 for cd in cands if w0 <= m[cd["born"]] < w1)
        births_by_panel.append((rec["id"], nb_in, len(cands)))

        for g, tau in golds:
            key = gkey(rec["id"], tau, g)
            n_all += 1
            is_un = key in unreach_keys
            n_un += is_un
            j_tau = min(int(np.searchsorted(m, tau)), len(m) - 1)
            live_counts.append(
                sum(1 for cd in cands if live_at(cd, j_tau, cp)))
            for cd in cands:
                if cd["born"] > j_tau:
                    continue
                rec_e = dict(type="BOX", lo=cd["lo"], hi=cd["hi"],
                             t0=float(m[cd["t0"]]), t1=float(tau),
                             w0=w0, w1=w1)
                ok, route = V2.match_detail(g, rec_e, m)
                if not ok:
                    continue
                is_live = live_at(cd, j_tau, cp)
                for tg in (cd["trigger"], "union"):
                    reach_b[tg].add(key + (is_un,))
                    if is_live:
                        reach_l[tg].add(key + (is_un,))
                hits_detail.append(
                    (rec["id"], key[1], is_un, cd["trigger"], route,
                     round(cd["lo"], 1), round(cd["hi"], 1),
                     is_live))

    def cnt(s, un):
        return sum(1 for k in s if k[4] == un)

    print("goldens scored: %d  unreachable: %d" % (n_all, n_un))
    print("%-14s %8s %8s %8s %8s" %
          ("trigger", "rch68_b", "rch68_l", "rch119b", "rch119l"))
    for t in trig_names:
        print("%-14s %8d %8d %8d %8d" % (
            t, cnt(reach_b[t], True), cnt(reach_l[t], True),
            cnt(reach_b[t], False) + cnt(reach_b[t], True),
            cnt(reach_l[t], False) + cnt(reach_l[t], True)))
    bp = np.array([b[1] for b in births_by_panel])
    tot = np.array([b[2] for b in births_by_panel])
    print("panels with goldens: %d" % len(births_by_panel))
    print("births in-window /panel: mean %.2f med %.1f max %d" %
          (bp.mean(), np.median(bp), bp.max()))
    print("births total /panel:     mean %.2f med %.1f" %
          (tot.mean(), np.median(tot)))
    print("live EC objects at tau: mean %.2f med %.1f max %d" %
          (np.mean(live_counts), np.median(live_counts),
           max(live_counts)))
    for d in sorted(set(hits_detail)):
        print("  HIT %-7s tau=%-5d un=%-5s %-13s %-15s [%.1f-%.1f] live=%s"
              % d)
    pickle.dump(dict(births=births_by_panel, hits=hits_detail),
                open(os.path.join(HERE, "_r67_ec.pkl"), "wb"))


if __name__ == "__main__":
    main()
