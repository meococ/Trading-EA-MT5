"""phys_analysis — post-freeze outcome resolution + pooled bake-off statistics.

Phases `resolve` and `report` of `run_bakeoff.py`.  `resolve` is the first code
in the round that reads a bar after an event bar and refuses to run unless
`rounds/R01/FREEZE.json` exists and is older than the CSV tables.
"""

import csv
import hashlib
import json
import os

import numpy as np

import phys_common as pc
import phys_extract as px
import phys_resolve as pr
import phys_stats as ps

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bakeoff")
ROUNDS = os.path.join(pc.PA_PRO, "rounds", "R01")
FREEZE = os.path.join(ROUNDS, "FREEZE.json")

EVENT_FLOATS = ("lo", "hi", "w", "near", "far", "m", "strength", "close_prev",
                "close_t")
EVENT_INTS = ("zid", "bar_idx", "bar_t", "utc_min", "year", "side", "touches",
              "n_respected", "role_flip", "age_bars", "overlap")
CTRL_FLOATS = ("lo", "hi", "w", "near", "far", "m")
CTRL_INTS = ("anchor_i", "anchor_bar_idx", "anchor_zid", "slot", "draw",
             "bar_idx", "bar_t", "side", "tk_dt")
OUTCOME_FIELDS = ["outcome", "bounce_bar", "break_bar", "break_close",
                  "cont_outcome", "cont_bar", "return_bar", "resolved",
                  "window_ok", "tercile"]


def load_rows(path, floats, ints):
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for k in floats:
                row[k] = float(row[k]) if row.get(k) not in ("", None) else float("nan")
            for k in ints:
                row[k] = int(float(row[k])) if row.get(k) not in ("", None) else -1
            if "contam_zone" in row:
                row["contam_zone"] = str(row["contam_zone"]) in ("True", "true", "1")
                row["contam_ref"] = str(row["contam_ref"]) in ("True", "true", "1")
            rows.append(row)
    return rows


def _load_bars(symbol):
    from data_helpers import load_ctx

    return load_ctx(symbol, max_bars=None).bars


def _freeze_ok(tables=None):
    """Refuse outcome work unless FREEZE.json exists AND precedes every input
    table it guards (R02-A F5: the docstring's ordering guard is now real).

    `tables=None` scans the bake-off directory's INPUT tables (EVENTS_*/CONTROLS_*);
    OUTCOME_* files are written by the resolver itself and are intentionally not
    part of the comparison.
    """
    if not os.path.exists(FREEZE):
        return False, "FREEZE.json missing"
    freeze_m = os.path.getmtime(FREEZE)
    if tables is None:
        import glob

        tables = sorted(glob.glob(os.path.join(OUT, "EVENTS_*.csv"))
                        + glob.glob(os.path.join(OUT, "CONTROLS_*.csv")))
    for p in tables:
        if os.path.exists(p) and os.path.getmtime(p) > freeze_m:
            return False, (f"input table {os.path.basename(p)} is newer than "
                           "FREEZE.json (freeze ordering violated)")
    return True, None


def phase_resolve(symbols, generators):
    ok, why = _freeze_ok()
    if not ok:
        raise SystemExit(f"refusing to resolve outcomes: {why}")
    with open(FREEZE, "r", encoding="utf-8") as f:
        freeze = json.load(f)
    import registry

    names = registry.names() if generators == "all" else generators.split(",")
    for symbol in symbols:
        bars = _load_bars(symbol)
        for name in names:
            epath = os.path.join(OUT, f"EVENTS_{symbol}_{name}.csv")
            cpath = os.path.join(OUT, f"CONTROLS_{symbol}_{name}.csv")
            if not os.path.exists(epath):
                continue
            ev = load_rows(epath, EVENT_FLOATS, EVENT_INTS)
            ct = load_rows(cpath, CTRL_FLOATS, CTRL_INTS) if os.path.exists(cpath) else []
            res, cnt = pr.resolve_events(ev, bars)
            rres, rcnt = pr.resolve_events(ct, bars) if ct else ([], {})
            bounds = freeze["generators"][name]["tercile_bounds"]
            for rows, results, out_path in ((ev, res, f"OUTCOME_EVENTS_{symbol}_{name}.csv"),
                                            (ct, rres, f"OUTCOME_CONTROLS_{symbol}_{name}.csv")):
                if not rows:
                    continue
                with open(os.path.join(OUT, out_path), "w", newline="",
                          encoding="utf-8") as f:
                    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())
                                        + [k for k in OUTCOME_FIELDS
                                           if k not in rows[0]])
                    wr.writeheader()
                    for row, r in zip(rows, results):
                        out = dict(row)
                        out.update(r)
                        out["tercile"] = px.tercile_of(float(row["strength"]),
                                                       *bounds) if "strength" in row else "na"
                        wr.writerow(out)
            with open(os.path.join(OUT, f"RESOLVE_{symbol}_{name}.json"), "w",
                      encoding="utf-8") as f:
                json.dump({"utc": pc.utc_now(), "symbol": symbol,
                           "generator": name, "events": cnt,
                           "controls": rcnt}, f, indent=1, sort_keys=True)
            print(f"resolved {symbol} {name}: ev {cnt.get('bounce')}/{cnt.get('break')}"
                  f"/{cnt.get('none')} ctrl {rcnt.get('bounce', 0)}/"
                  f"{rcnt.get('break', 0)}/{rcnt.get('none', 0)}", flush=True)


def _subset(real, ctrl, keep_idx):
    pos = {gi: p for p, gi in enumerate(keep_idx)}
    real2 = [real[i] for i in keep_idx]
    ctrl2 = []
    for c in ctrl:
        p = pos.get(c.get("anchor_i"))
        if p is None:
            continue
        c2 = dict(c)
        c2["anchor_i"] = p
        ctrl2.append(c2)
    return real2, ctrl2


def _load_generator(name, symbols):
    real, ctrl = [], []
    for symbol in symbols:
        epath = os.path.join(OUT, f"OUTCOME_EVENTS_{symbol}_{name}.csv")
        cpath = os.path.join(OUT, f"OUTCOME_CONTROLS_{symbol}_{name}.csv")
        if not os.path.exists(epath):
            continue
        ev = load_rows(epath, EVENT_FLOATS, EVENT_INTS)
        ct = load_rows(cpath, CTRL_FLOATS, CTRL_INTS) if os.path.exists(cpath) else []
        off = len(real)
        for r in ev:
            r["symbol"] = symbol
        for c in ct:
            c["symbol"] = symbol
            c["anchor_i"] = int(c["anchor_i"]) + off
        real.extend(ev)
        ctrl.extend(ct)
    return real, ctrl


def _bounce(r):
    return pr.bounce_cond([r], 0)


def _cont(r):
    return pr.cont_cond([r], 0)


def _d_top(real, ctrl, value_fn, n_boot=10000):
    return ps.cell_stats(real, ctrl, value_fn, n_boot=n_boot)


def phase_report(symbols, generators):
    ok, why = _freeze_ok()
    if not ok:
        raise SystemExit(f"refusing to report: {why}")
    with open(FREEZE, "r", encoding="utf-8") as f:
        freeze = json.load(f)
    import registry

    names = registry.names() if generators == "all" else generators.split(",")
    freeze["freeze_sha256"] = pc.sha256_file(FREEZE)
    summary = {}
    for name in names:
        real, ctrl = _load_generator(name, symbols)
        bounds = freeze["generators"][name]["tercile_bounds"]
        for rows in (real, ctrl):
            for r in rows:
                if "tercile" not in r or r["tercile"] in ("", "na"):
                    r["tercile"] = "na"
        n_resolved = int(sum(1 for r in real if r.get("resolved") in (True, "True")))
        top_idx = [i for i, r in enumerate(real) if r["tercile"] == "top"]
        mid_idx = [i for i, r in enumerate(real) if r["tercile"] == "mid"]
        bot_idx = [i for i, r in enumerate(real) if r["tercile"] == "bot"]

        def cell(idx, fn=_bounce, n_boot=10000):
            r2, c2 = _subset(real, ctrl, idx)
            return _d_top(r2, c2, fn, n_boot=n_boot)

        d_top = cell(top_idx)
        d_mid = cell(mid_idx)
        d_bot = cell(bot_idx)
        mono = bool(np.isfinite(d_bot["D"]) and np.isfinite(d_mid["D"])
                    and d_bot["D"] <= d_mid["D"] <= d_top["D"])
        sym_signs = {}
        for s in symbols:
            idx = [i for i in top_idx if real[i]["symbol"] == s]
            sym_signs[s] = cell(idx, n_boot=2000)["D"]
        years = sorted({int(r["year"]) for r in real})
        yr_signs = {}
        for y in years:
            idx = [i for i in top_idx if int(real[i]["year"]) == y]
            yr_signs[str(y)] = cell(idx, n_boot=2000)["D"]
        gate = ps.gate_verdict(d_top, mono, sym_signs, yr_signs)
        n_break_top = int(sum(1 for r in top_idx if real[r].get("outcome") == "BREAK"))
        d_cont = cell(top_idx, fn=_cont)
        d_cont_mid = cell(mid_idx, fn=_cont)
        d_cont_bot = cell(bot_idx, fn=_cont)
        cont_mono = bool(np.isfinite(d_cont_bot["D"]) and np.isfinite(d_cont_mid["D"])
                         and d_cont_bot["D"] <= d_cont_mid["D"] <= d_cont["D"])
        cont_sym = {}
        for s in symbols:
            idx = [i for i in top_idx if real[i]["symbol"] == s]
            cont_sym[s] = cell(idx, fn=_cont, n_boot=2000)["D"]
        cont_yr = {}
        for y in years:
            idx = [i for i in top_idx if int(real[i]["year"]) == y]
            cont_yr[str(y)] = cell(idx, fn=_cont, n_boot=2000)["D"]
        cont_gate = ps.gate_verdict(d_cont, cont_mono, cont_sym, cont_yr) \
            if n_break_top >= 60 else {"pass": False, "checks": {"floor": False}}
        clean_ctrl = [c for c in ctrl if not c.get("contam_zone")
                      and not c.get("contam_ref")]
        r2, c2 = _subset(real, clean_ctrl, top_idx)
        d_clean = _d_top(r2, c2, _bounce)
        near_ctrl = [c for c in ctrl if int(c.get("tk_dt", 0)) <= 288]
        r2, c2 = _subset(real, near_ctrl, top_idx)
        d_near = _d_top(r2, c2, _bounce)
        n_ctrl = len(ctrl)
        contam = {
            "n_controls": n_ctrl,
            "zone_rate": (sum(1 for c in ctrl if c.get("contam_zone")) / n_ctrl)
            if n_ctrl else None,
            "ref_rate": (sum(1 for c in ctrl if c.get("contam_ref")) / n_ctrl)
            if n_ctrl else None,
            "ctrl_per_resolved": (n_ctrl / n_resolved) if n_resolved else None,
            "mean_k_per_event": (n_ctrl / len(real)) if real else None,
        }
        summary[name] = {
            "n_events": len(real), "n_resolved": n_resolved,
            "n_top": len(top_idx), "n_break_top": n_break_top,
            "D_top": d_top, "D_mid": d_mid, "D_bot": d_bot, "monotone": mono,
            "sym_signs": sym_signs, "year_signs": yr_signs,
            "gate": gate, "cont_gate": cont_gate, "D_cont": d_cont,
            "D_cont_mid": d_cont_mid, "D_cont_bot": d_cont_bot,
            "cont_monotone": cont_mono, "cont_sym": cont_sym, "cont_yr": cont_yr,
            "S_CLEAN": d_clean, "S_NEAR": d_near, "contam": contam,
            "coverage": freeze["generators"][name].get("coverage_med"),
            "power_ok": bool(n_resolved >= 1000),
            "cont_power_ok": bool(n_break_top >= 60),
        }
        print(f"{name}: events={len(real)} resolved={n_resolved} "
              f"D_top={d_top['D']:.4f} [{d_top['lo']:.4f},{d_top['hi']:.4f}] "
              f"p={d_top['p']:.5f} gate={gate['pass']} mono={mono}", flush=True)

    # BH across 6 x 2 endpoints
    pvals, labels = [], []
    for name in names:
        pvals.append(summary[name]["D_top"]["p"])
        labels.append(name + ":bounce")
        pvals.append(summary[name]["D_cont"]["p"])
        labels.append(name + ":cont")
    bh = ps.bh_across(pvals, q=0.10)
    for i, name in enumerate(names):
        summary[name]["bh_bounce"] = {"q": bh["qvalues"][2 * i],
                                      "rejected": bh["rejected"][2 * i]}
        summary[name]["bh_cont"] = {"q": bh["qvalues"][2 * i + 1],
                                    "rejected": bh["rejected"][2 * i + 1]}
    summary["_bh"] = {"labels": labels, "qvalues": bh["qvalues"],
                      "rejected": bh["rejected"], "q": bh["q"]}

    # winner rule (SHORTLIST section 4)
    baseline = "line1_cluster"
    def eligible(nm):
        return summary[nm]["power_ok"]
    ranked = sorted([n for n in names if eligible(n)],
                    key=lambda n: -(summary[n]["D_top"]["D"] if np.isfinite(summary[n]["D_top"]["D"]) else -9))
    passes = [n for n in ranked if summary[n]["gate"]["pass"] and summary[n]["bh_bounce"]["rejected"]]
    winner = None
    if passes:
        lead = passes[0]
        b = summary[baseline]["D_top"]["D"]
        if lead == baseline or (np.isfinite(b) and summary[lead]["D_top"]["D"] - b >= 0.02):
            winner = lead
        else:
            winner = baseline if eligible(baseline) else None
    summary["_winner"] = {"ranked": ranked, "passes": passes, "winner": winner,
                          "baseline": baseline}
    with open(os.path.join(OUT, "STATS.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True, default=float)
    _ledger_trials(names, summary, freeze)
    _write_results_md(names, summary, freeze, symbols)
    print("report done; winner:", winner)


def _tables_data_sha256(freeze):
    """R02-C (a2): SHA256 over the frozen input-table hashes this line's
    numbers were computed from (the ``tables`` map already in FREEZE.json)."""
    h = hashlib.sha256()
    for name, sha in sorted((freeze.get("tables") or {}).items()):
        h.update(f"{name}:{sha}\n".encode("utf-8"))
    return h.hexdigest()


def _ledger_trials(names, summary, freeze):
    import pa_ledger

    data_sha = _tables_data_sha256(freeze)
    for name in names:
        s = summary[name]
        params = {
            "generator": name, "symbols": freeze["symbols"],
            "tf": "M5", "population": "armed",
            "control": "addendum2_arbitrary_band", "seed": pc.SEED,
            "freeze_sha256": freeze.get("freeze_sha256"),
        }
        metrics = {
            "n_resolved": s["n_resolved"], "n_top": s["n_top"],
            "D_top": s["D_top"]["D"], "D_top_ci": [s["D_top"]["lo"], s["D_top"]["hi"]],
            "p_top": s["D_top"]["p"], "monotone": s["monotone"],
            "gate_pass": s["gate"]["pass"], "bh_q_bounce": s["bh_bounce"]["q"],
            "D_cont_top": s["D_cont"]["D"], "n_break_top": s["n_break_top"],
            "gate_cont_pass": s["cont_gate"]["pass"],
            "bh_q_cont": s["bh_cont"]["q"],
            "S_CLEAN": s["S_CLEAN"]["D"], "S_NEAR": s["S_NEAR"]["D"],
            "contam_zone_rate": s["contam"]["zone_rate"],
            "contam_ref_rate": s["contam"]["ref_rate"],
            "coverage_med": s["coverage"],
        }
        tid = pa_ledger.append({
            "round": "R01", "family": "PHYSICS", "split": "DESIGN",
            "symbols": freeze["symbols"], "tf": "M5", "n": s["n_resolved"],
            "spec_sha256": freeze["prereg_sha256"], "params": params,
            "key_metrics": metrics, "status": "OK",
            "code_sha256": freeze.get("physics_code_sha256"),
            "data_sha256": data_sha,
        }, kind="eval")
        print("ledger", tid, name, flush=True)


def _fmt(x, nd=4):
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "n/a"


def _write_results_md(names, summary, freeze, symbols):
    import pa_costs
    import pa_ledger

    L = []
    L.append("# R01 PHYSICS_RESULTS — zone-generator level-physics bake-off")
    L.append("")
    L.append(f"UTC {pc.utc_now()} · DESIGN {freeze['split']} · core symbols "
             f"{', '.join(symbols)} · execution {freeze['tf']} · seed {pc.SEED}")
    L.append("")
    L.append("**Estimand (Lead ruling R01-C1, quoted verbatim):**")
    L.append("")
    L.append("> D = P(bounce | fresh approach to an ARMED zone of generator g) − P(bounce | "
             "fresh approach to a geometry-matched arbitrary band). D is the incremental value "
             "of using this generator's zones instead of an arbitrary level with the same geometry.")
    L.append("")
    L.append(f"Hashes: prereg `{freeze['prereg_sha256']}` · addendum-2 "
             f"`{freeze['addendum2_sha256']}` · physics code `{freeze['physics_code_sha256']}` · "
             f"zones code `{freeze['zones_code_sha256']}` · freeze `{freeze.get('freeze_sha256')}`")
    L.append("")
    # R02-C/R02-F: the round report artifact anchors the ledger head it was
    # written against AND records that anchor in ledger/ANCHORS.jsonl (the
    # mechanism is only real when the artifact exists).  Re-verify with
    # pa_ledger.verify_against_anchors() / check_anchor().
    _anchor = pa_ledger.append_anchor(
        note=f"round report {os.path.join(ROUNDS, 'PHYSICS_RESULTS.md')}")
    L.append(pa_ledger.anchor_md(_anchor))
    L.append("")
    L.append("A FAIL means: no measurable edge over arbitrary levels of the same geometry. "
             "It does NOT mean levels do not exist.")
    L.append("")
    L.append("## Pooled core results (ARMED population)")
    L.append("")
    L.append("| generator | events | resolved | ctrl/resolved | mean K/event | cov med | D_top | 95% CI | p | "
             "D_mid | D_bot | mono | gate | BH q | D_cont_top | N brk top | cont gate | BH q cont |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name in names:
        s = summary[name]
        L.append(
            f"| `{name}` | {s['n_events']} | {s['n_resolved']} | "
            f"{_fmt(s['contam']['ctrl_per_resolved'],2) if s['contam'].get('ctrl_per_resolved') else 'n/a'} | "
            f"{_fmt(s['contam']['mean_k_per_event'],2) if s['contam'].get('mean_k_per_event') else 'n/a'} | "
            f"{_fmt(s['coverage'],2)} | {_fmt(s['D_top']['D'])} | "
            f"[{_fmt(s['D_top']['lo'])},{_fmt(s['D_top']['hi'])}] | {_fmt(s['D_top']['p'],5)} | "
            f"{_fmt(s['D_mid']['D'])} | {_fmt(s['D_bot']['D'])} | "
            f"{'yes' if s['monotone'] else 'no'} | "
            f"{'PASS' if s['gate']['pass'] else 'fail'} | {_fmt(s['bh_bounce']['q'],4)} | "
            f"{_fmt(s['D_cont']['D'])} | {s['n_break_top']} | "
            f"{'PASS' if s['cont_gate']['pass'] else ('UNDERPOWERED' if not s['cont_power_ok'] else 'fail')} | "
            f"{_fmt(s['bh_cont']['q'],4)} |")
    L.append("")
    L.append("## Gate detail (charter thresholds, SHORTLIST section 4)")
    L.append("")
    for name in names:
        s = summary[name]
        if not s["power_ok"]:
            L.append(f"- `{name}`: **UNDERPOWERED** (resolved {s['n_resolved']} < 1000) — not a loss.")
            continue
        L.append(f"- `{name}`: checks {json.dumps(s['gate']['checks'])} · "
                 f"symbols +{s['gate']['n_sym_pos']}/{s['gate']['n_sym']} · "
                 f"years +{s['gate']['n_yr_pos']}/{s['gate']['n_yr']} · "
                 f"BH q(bounce) {_fmt(s['bh_bounce']['q'],4)} rejected "
                 f"{s['bh_bounce']['rejected']} → "
                 f"{'LINES MATTER PASS' if s['gate']['pass'] and s['bh_bounce']['rejected'] else 'FAIL'}")
    L.append("")
    L.append("## Declared descriptive views (Addendum 2; never gates)")
    L.append("")
    L.append("| generator | coverage med | contam_zone rate | contam_ref rate | S-CLEAN D_top | N kept | S-NEAR D_top |")
    L.append("|---|---|---|---|---|---|---|")
    for name in names:
        s = summary[name]
        L.append(f"| `{name}` | {_fmt(s['coverage'],2)} | "
                 f"{_fmt(s['contam']['zone_rate'],4)} | {_fmt(s['contam']['ref_rate'],4)} | "
                 f"{_fmt(s['S_CLEAN']['D'])} | {s['S_CLEAN']['n']} | {_fmt(s['S_NEAR']['D'])} |")
    L.append("")
    L.append("Declared interpretation (Addendum 2 item 5): a sparser generator is attenuated less "
             "by contamination than a denser one; selectivity is part of what this bake-off measures "
             "and is not corrected for — coverage is reported so the reader can see it.")
    L.append("")
    L.append("## Winner rule (SHORTLIST section 4, pre-declared)")
    w = summary["_winner"]
    L.append("")
    L.append(f"- eligible (resolved >= 1000): {', '.join(w['ranked']) if w['ranked'] else 'none'}")
    L.append(f"- threshold passers (charter + BH q<=0.10, bounce endpoint): "
             f"{', '.join(w['passes']) if w['passes'] else 'none'}")
    L.append(f"- ranked by D_top: " + ", ".join(
        f"{n} {_fmt(summary[n]['D_top']['D'])}" for n in w["ranked"]))
    L.append(f"- **WINNER: {w['winner'] if w['winner'] else 'NONE (bake-off FAIL — LINES MATTER not supported)'}**")
    L.append("")
    L.append("## Viability arithmetic (charter §4; arithmetic, no measurement)")
    L.append("")
    L.append("`required bias = c_rt / (2 m) + 2.00pp`, `m` = median event-barrier ATR14(H1) of "
             "the winner's top-tercile resolved events.")
    L.append("")
    L.append("| symbol | c_rt x1 | median m (pips) | required bias | measured D_top |")
    L.append("|---|---|---|---|---|")
    win = w["winner"]
    if win:
        real, ctrl = _load_generator(win, symbols)
        for sym in symbols:
            rows = [r for r in real if r["symbol"] == sym and r["tercile"] == "top"]
            mm = float(np.median([r["m"] for r in rows])) if rows else float("nan")
            c_rt = pa_costs.C_RT_P90.get(sym)
            req = c_rt / (2.0 * mm / pa_costs.pip_size(sym)) + 0.02 if mm == mm else float("nan")
            L.append(f"| {sym} | {_fmt(c_rt,1)} | {_fmt(mm/pa_costs.pip_size(sym),2)} | "
                     f"{_fmt(req*100,2)}pp | {_fmt(summary[win]['sym_signs'][sym])} |")
    else:
        L.append("| — | — | — | — | no winner |")
    L.append("")
    L.append("## Notes")
    L.append("")
    L.append("- All 12 hypotheses (6 generators x {bounce, continuation}) are ledger trials "
             "(family=PHYSICS); the program trial count includes the historical T000001 smoke line.")
    L.append("- Sensitivity views NOT RUN this round: all-intact-live population, width 0.20 vs "
             "0.25, frozen-A barriers, block bootstrap (declared in PHYSICS_PREREG §0).")
    L.append("- No fills, no PnL, no costs are applied; this is a reaction-proportion experiment.")
    path = os.path.join(ROUNDS, "PHYSICS_RESULTS.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", path)
