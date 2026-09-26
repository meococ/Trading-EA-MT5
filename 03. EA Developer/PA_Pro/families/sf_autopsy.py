"""sf_autopsy.py — SF02 Q1 autopsy machinery (DESIGN only).

Implements AUTOPSY_PLAN.md (ledger T000229):

  A1  random drag curve via pa_eval.evaluate (referee path, ledgered)
  A2  MFE/MAE exit-free edge  (DESCRIPTIVE)
  A3  salience perception audit (DESCRIPTIVE; tercile lift via the same
      referee-simulated trade lists)
  A4  context slices (DESCRIPTIVE)

The plan fixes the thick cell per family, the salience formula, all bin
edges and horizons BEFORE any computation.
"""

import importlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
PA_PRO = os.path.dirname(HERE)
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_clock        # noqa: E402
import pa_costs        # noqa: E402
import pa_eval         # noqa: E402
import pa_fill         # noqa: E402
import pa_metrics      # noqa: E402
import pa_random       # noqa: E402
import pa_sealed       # noqa: E402
import sf_ctx          # noqa: E402
import sf_provider     # noqa: E402

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
SEED = 20260920
K_RAND = 20

# thick cell per family (declared in AUTOPSY_PLAN.md)
THICK = {
    "f1_zone_rejection":  {"S_pips": 18.0, "gen": "line1_cluster", "rej_body": 0},
    "f2_break_retest":    {"S_pips": 18.0, "gen": "line1_cluster", "rej_body": 0},
    "f3_failed_breakout": {"S_pips": 18.0, "gen": "line1_cluster", "rej_body": 0},
    "f4_trend_pullback":  {"S_pips": 18.0, "gen": "line1_cluster", "tr_src": "h1"},
    "f5_second_entry":    {"S_pips": 14.0, "tr_src": "h1", "tol_atr": 1.0},
    "f6_volman_box":      {"S_pips": 24.0, "gen": "line1_cluster", "box_atr": 4.0},
}

ENGINE = {                       # identical to the SF01 screens
    "order_type": "stop", "v_bars": 3, "invalidation": True,
    "session_cancel": True, "flats": True, "legacy_flats": False,
    "daily_flat_hour": 22, "friday_flat_hour": 20, "weekend_veto": True,
    "tp_mult": 2.0,
}

OUT_DIR = os.path.join(PA_PRO, "rounds", "SF02")
_D = {}          # (sym, gen) -> cache
_FRAMES = {}     # sym -> provider frame
_CTX = {}        # sym -> pa_fill ctx


def cache(sym, gen):
    if (sym, gen) not in _D:
        _D[(sym, gen)] = sf_ctx.load_cache(sym, gen)
    return _D[(sym, gen)]


def frame(sym):
    if sym not in _FRAMES:
        _FRAMES[sym] = sf_provider.provider(sym, "DESIGN", "M5")
    return _FRAMES[sym]


def fctx(sym, spec):
    if sym not in _CTX:
        d = frame(sym)
        _CTX[sym] = pa_fill.build_ctx(
            d["m1"], d["m5"], d["m5_t"], d["starts"], d["pip"],
            next_end=d.get("next_end"),
            first_live_idx=d.get("first_live_idx", 0),
            symbol=sym, c_rt_pips=d.get("c_rt_pips"))
        ctx = _CTX[sym]
        if ctx.get("next_end") is None:
            masks = d.get("sess_mask") or {}
            mask_any = masks.get("eu", masks.get("london"))
            if "us" in masks:
                mask_any = mask_any | masks["us"]
            elif "ny" in masks:
                mask_any = mask_any | masks["ny"]
            ctx["next_end"] = pa_fill.compute_next_end(
                d["starts"], mask_any, len(d["m1"]["t"])).tolist()
    return _CTX[sym]


def thick_entries(fam):
    """Regenerate the screened thick-cell entries per symbol."""
    mod = importlib.import_module(fam)
    params = THICK[fam]
    out = {}
    for sym in SYMBOLS:
        if hasattr(mod, "_load"):
            D = mod._load(sym)
        else:
            D = cache(sym, params["gen"])
        c_rt = pa_costs.C_RT_P90[sym]
        out[sym] = mod.detect(D, c_rt, params)
    return out


def randoms_for(entries_by_sym, K=K_RAND, seed=SEED):
    """Reproduce the referee's matched randoms (same seed/contract)."""
    out = {}
    for sym, entries in entries_by_sym.items():
        d = frame(sym)
        sig_list = [{"bar_idx": int(e["sig"]), "side": int(e["side"])}
                    for e in entries]
        picks = pa_random.match_random(sig_list, d["bars"], K=K, seed=seed)
        kept = [i for i, e in enumerate(entries)
                if pa_random.session_of(
                    d["bars"]["utc_min"][int(e["sig"])]) is not None]
        rows = [{"sig": int(p[0]), "side": int(p[1]),
                 "tag": kept[i // K]} for i, p in enumerate(picks)]
        # drop warm-up picks exactly as pa_eval does
        utc = pa_clock.server_to_utc_epoch(
            np.asarray(d["bars"]["t"], dtype=np.int64))
        start_u = int(d.get("utc_start", 0))
        out[sym] = [e for e in rows if int(utc[e["sig"]]) >= start_u]
    return out


def cell_spec(fam, params):
    """Engine spec dict for direct pa_fill.simulate (DESCRIPTIVE use)."""
    s = dict(ENGINE)
    s["S_pips"] = float(params["S_pips"])
    return s


# ---------------------------------------------------------------- A1

def a1_anchor(entries_pool):
    """Anchor signal set: pooled dedup in-session sig bars."""
    out = {}
    for sym in SYMBOLS:
        seen = {}
        for entries in entries_pool[sym]:
            for e in entries:
                seen[int(e["sig"])] = int(e["side"])
        out[sym] = [{"sig": k, "side": v} for k, v in sorted(seen.items())]
    return out


def a1_run(out_path):
    """32-config random drag curve through pa_eval (ledgered)."""
    pool = {sym: [] for sym in SYMBOLS}
    for fam in THICK:
        for sym, ent in thick_entries(fam).items():
            pool[sym].append(ent)
    anchor = a1_anchor(pool)
    rnd = {}
    for sym in SYMBOLS:
        d = frame(sym)
        picks = pa_random.match_random(
            [{"bar_idx": s["sig"], "side": s["side"]}
             for s in anchor[sym]], d["bars"], K=K_RAND, seed=SEED)
        utc = pa_clock.server_to_utc_epoch(
            np.asarray(d["bars"]["t"], dtype=np.int64))
        start_u = int(d.get("utc_start", 0))
        rnd[sym] = [{"sig": int(p[0]), "side": int(p[1]), "tag": i}
                    for i, p in enumerate(picks)
                    if int(utc[int(p[0])]) >= start_u]
        print(f"  A1 anchor {sym}: {len(anchor[sym])} sigs -> "
              f"{len(rnd[sym])} randoms", flush=True)

    grid_S = [11.0, 14.0, 18.0, 24.0, 32.0, 40.0, 55.0, 75.0]
    grid_tp = [1.0, 1.5, 2.0, 3.0]
    rows = []
    i = 0
    for S in grid_S:
        for tp in grid_tp:
            i += 1
            t0 = time.time()
            spec = dict(ENGINE)
            spec.update({"S_pips": S, "tp_mult": tp,
                         "family": "sf02_autopsy_a1",
                         "round": "SF02", "tf": "M5",
                         "entries_fn": (
                             lambda sym, bars, _s, _r=rnd: _r[sym])})
            res = pa_eval.evaluate(
                spec, "DESIGN", SYMBOLS, "M5", cost_tiers=["x1"],
                round_name="SF02", family="sf02_autopsy_a1",
                data_provider=sf_provider.provider,
                random_enabled=False,
                notes={"a1_cell": i, "S": S, "tp_mult": tp})
            m = res["tiers"]["x1"]["strategy"]
            rows.append({"S_pips": S, "tp_mult": tp,
                         "N": m.get("N"), "PF": m.get("PF"),
                         "exp_r": m.get("exp_R") or m.get("expr"),
                         "WR": m.get("WR"),
                         "exit_mix": m.get("exit_mix"),
                         "per_symbol": m.get("per_symbol_expr"),
                         "elapsed": round(time.time() - t0, 1)})
            print(f"  A1 [{i}/32] S={S} tp={tp}: N={m.get('N')} "
                  f"PF={m.get('PF')} ({rows[-1]['elapsed']}s)", flush=True)
    json.dump({"rows": rows, "seed": SEED, "K": K_RAND},
              open(out_path, "w"), indent=1)
    return rows


# ------------------------------------------------- A2 (DESCRIPTIVE)

def mfe_mae(D, e, horizons=(6, 12, 24, 48, 96)):
    """Forward MFE/MAE in ATR(H1) units from the signal bar.

    entry ref = order_px (strategy) else c[sig] (randoms).  Window is
    capped at the session-flat M5 bar and data end.  Returns
    {h: (mfe, mae)}.
    """
    sig = int(e["sig"])
    side = int(e["side"])
    px = float(e.get("order_px") or D["c"][sig])
    a_h1 = float(D["s_atr_h1"][sig])
    h_arr, l_arr = D["h"], D["l"]
    n = len(h_arr)
    end_cap = int(D.get("_sess_end_m5", n - 1)[sig]) \
        if "_sess_end_m5" in D else n - 1
    out = {}
    for hz in horizons:
        j1, j2 = sig + 1, min(sig + hz, end_cap, n - 1)
        if j1 > j2:
            out[hz] = (0.0, 0.0)
            continue
        hi = float(np.max(h_arr[j1:j2 + 1]))
        lo = float(np.min(l_arr[j1:j2 + 1]))
        if side > 0:
            mfe, mae = (hi - px), (px - lo)
        else:
            mfe, mae = (px - lo), (hi - px)
        out[hz] = (mfe / a_h1 if a_h1 > 0 else np.nan,
                   mae / a_h1 if a_h1 > 0 else np.nan)
    return out


def attach_sess_end(D, frame_d):
    """Precompute per-M5-bar session-end cap (M5 bar index)."""
    ctx_next = None
    masks = frame_d.get("sess_mask") or {}
    mask_any = masks.get("eu", masks.get("london"))
    if mask_any is not None:
        if "us" in masks:
            mask_any = mask_any | masks["us"]
        elif "ny" in masks:
            mask_any = mask_any | masks["ny"]
        ne_m1 = pa_fill.compute_next_end(
            frame_d["starts"], mask_any, len(frame_d["m1"]["t"]))
        starts = np.asarray(frame_d["starts"], dtype=np.int64)
        # M5 bar index of the last M5 bar that starts before ne_m1
        idx = np.searchsorted(starts, ne_m1, side="right") - 1
        D["_sess_end_m5"] = np.minimum(idx, len(D["t"]) - 1)
    else:
        D["_sess_end_m5"] = np.full(len(D["t"]), len(D["t"]) - 1)


def day_clustered_ci(vals, keys, B=1000, seed=7):
    """Bootstrap CI of mean(vals) resampling by cluster ``keys``."""
    vals = np.asarray(vals, dtype=np.float64)
    keys = np.asarray(keys)
    uniq = {}
    for k in keys:
        uniq.setdefault(k, []).append(0)
    cl = {k: np.where(keys == k)[0] for k in uniq}
    ks = list(cl.keys())
    rng = np.random.default_rng(seed)
    mu = np.empty(B)
    for b in range(B):
        pick = rng.choice(len(ks), size=len(ks), replace=True)
        idx = np.concatenate([cl[ks[p]] for p in pick])
        mu[b] = vals[idx].mean()
    return float(np.percentile(mu, 2.5)), float(np.percentile(mu, 97.5))


def a2_run(entries_by_sym, rnd_by_sym):
    """Exit-free MFE/MAE edge, strategy minus random, per horizon."""
    res = {}
    for fam in entries_by_sym:
        res[fam] = {}
        for hz in (6, 12, 24, 48, 96):
            s_mfe, s_mae, s_day = [], [], []
            r_mfe, r_mae, r_day = [], [], []
            for sym in SYMBOLS:
                D = cache(sym, THICK[fam].get("gen", "line1_cluster"))
                if "_sess_end_m5" not in D:
                    attach_sess_end(D, frame(sym))
                day = (pa_clock.server_to_utc_epoch(
                    np.asarray(D["t"], dtype=np.int64)) // 86400)
                for e in entries_by_sym[fam][sym]:
                    mm = mfe_mae(D, e, (hz,))[hz]
                    s_mfe.append(mm[0]); s_mae.append(mm[1])
                    s_day.append(int(day[int(e["sig"])]))
                for e in rnd_by_sym[fam][sym]:
                    mm = mfe_mae(D, e, (hz,))[hz]
                    r_mfe.append(mm[0]); r_mae.append(mm[1])
                    r_day.append(int(day[int(e["sig"])]))
            s_mfe = np.asarray(s_mfe); s_mae = np.asarray(s_mae)
            r_mfe = np.asarray(r_mfe); r_mae = np.asarray(r_mae)
            er_s = np.nanmean(s_mfe) / max(np.nanmean(s_mae), 1e-12)
            er_r = np.nanmean(r_mfe) / max(np.nanmean(r_mae), 1e-12)
            # bootstrap delta of the edge ratio by UTC-day clusters
            rng = np.random.default_rng(11)
            days = np.unique(s_day)
            dl = []
            for _ in range(300):
                pick = rng.choice(days, size=len(days), replace=True)
                sm = np.concatenate(
                    [np.where(np.asarray(s_day) == dd)[0] for dd in pick])
                rm_mask = np.isin(r_day, pick)
                if rm_mask.sum() < 10:
                    continue
                e1 = (np.nanmean(s_mfe[sm]) /
                      max(np.nanmean(s_mae[sm]), 1e-12))
                e2 = (np.nanmean(r_mfe[rm_mask]) /
                      max(np.nanmean(r_mae[rm_mask]), 1e-12))
                dl.append(e1 - e2)
            ci = (float(np.percentile(dl, 2.5)),
                  float(np.percentile(dl, 97.5))) if dl else (None, None)
            res[fam][hz] = {
                "E_MFE_s": float(np.nanmean(s_mfe)),
                "E_MAE_s": float(np.nanmean(s_mae)),
                "edge_s": float(er_s),
                "E_MFE_r": float(np.nanmean(r_mfe)),
                "E_MAE_r": float(np.nanmean(r_mae)),
                "edge_r": float(er_r),
                "delta": float(er_s - er_r),
                "ci95": ci,
            }
    return res


# ------------------------------------ A3/A4 features (DESCRIPTIVE)

def zone_rec_at(D, t, zid):
    for z in sf_ctx.zones_at(D, t):
        if int(z["zid"]) == int(zid):
            return z
    return None


def armed_zones_near(D, t, atr_h1, mult=2.0):
    px = float(D["c"][t])
    out = []
    for z in sf_ctx.zones_at(D, t):
        if not z.get("armed"):
            continue
        if abs(z["lo"] - px) <= mult * atr_h1 or \
           abs(z["hi"] - px) <= mult * atr_h1 or \
           (z["lo"] <= px <= z["hi"]):
            out.append(z)
    return out


def salience(z, D, t, atr_h1):
    """Plan-fixed causal salience (AUTOPSY_PLAN A3)."""
    if z is None:
        return np.nan
    nr = float(z.get("n_respected") or 0)
    # pivot confluence: confirmed H1/H4 pivot within 0.5*ATR_H1 of edge
    pconf = 0.0
    for arr_i, arr_px, arr_cf in (("h1p_i", "h1p_px", "h1p_conf"),):
        pi, pp, pc = D[arr_i], D[arr_px], D[arr_cf]
        m = (pc <= t)
        if m.any():
            near = np.min(np.abs(pp[m] - z["hi"]))
            near2 = np.min(np.abs(pp[m] - z["lo"]))
            if min(near, near2) <= 0.5 * atr_h1:
                pconf = 1.0
    mid = 0.5 * (z["lo"] + z["hi"])
    pip = float(D["pip"])
    grid = 25.0 * pip
    dist = abs(mid / grid - round(mid / grid)) * grid
    rconf = 1.0 if dist <= 0.25 * atr_h1 else 0.0
    width = (z["hi"] - z["lo"]) / atr_h1
    age = float(z.get("age") or 0)
    return (1.0 * nr + 1.0 * pconf + 0.5 * rconf
            - 0.5 * width + 0.25 * np.log1p(age / 96.0))


def trade_slices(D, e, z, S_pips):
    """A4 bin labels for one entry (None where undefined)."""
    t = int(e["sig"]); side = int(e["side"])
    px = float(e.get("order_px") or D["c"][t])
    a5 = float(D["s_atr_m5"][t]); a1 = float(D["s_atr_h1"][t])
    tr1, tr4 = int(D["s_tr_h1"][t]), int(D["s_tr_h4"][t])
    def _lab(tr):
        return "aligned" if tr == side else ("counter" if tr == -side
                                             else "flat")
    # H4 range position: rolling 24-H1-bar range (~4 days = 1152 M5)
    W = 1152
    j0 = max(0, t - W)
    hi = float(np.max(D["h"][j0:t + 1])); lo = float(np.min(D["l"][j0:t + 1]))
    pos = (px - lo) / (hi - lo) if hi > lo else 0.5
    pos = min(max(pos, 0.0), 1.0)
    # chase: distance of order beyond triggering zone edge, in ATR_M5
    chase = np.nan
    if z is not None and a5 > 0:
        edge = z["hi"] if side > 0 else z["lo"]
        chase = abs(px - edge) / a5
    # room: nearest opposing armed zone edge in R (units of S)
    room = np.nan
    best = np.inf
    for zz in sf_ctx.zones_at(D, t):
        if not zz.get("armed"):
            continue
        opp_edge = zz["lo"] if side > 0 else zz["hi"]   # opposing side
        dist = (opp_edge - px) * side
        if dist > 0:
            best = min(best, dist)
    if np.isfinite(best) and S_pips > 0:
        room = best / (S_pips * float(D["pip"]))
    return {"tr_h1": _lab(tr1), "tr_h4": _lab(tr4), "h4_pos": pos,
            "atr_h1": a1, "chase": chase, "room_R": room}
