"""mk_ledger.py — emit market_study ledger rows from out/*.json.

F6 remediation (REVIEW_2): ledger rows are now produced by this script,
not ad-hoc interactive calls.  Idempotent: a row is skipped when a line
with the same (family, run_tag) already exists in the ledger.

Run AFTER the analyzers have written out/*_results.json.  Every emitted
row carries spec_sha256 (study plan or addendum hash), the event-table
sha256 per symbol, headline metrics, run_tag, and `supersedes` rows.

Usage:  python mk_ledger.py <run_tag> <supersedes_csv_or_dash>
        e.g.  python mk_ledger.py r2 T000380,T000381,T000382,T000383,T000384,T000385,T000386,T000387,T000391
"""
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "lib"))
import mk_common as K          # noqa: E402
import pa_ledger               # noqa: E402

OUT = K.OUT
PLAN_SHA = "abc8b5ba5a80d04928b78204e2d690a5cdb74b091f515a6ff8669cfb499f962c"


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _event_shas(prefix):
    """sha256 of out/<prefix>_<SYM>.npz per symbol (12-hex abbrev)."""
    out = {}
    for s in K.CORE:
        p = os.path.join(OUT, f"{prefix}_{s}.npz")
        if os.path.exists(p):
            out[s] = _sha_file(p)[:12]
    return out


def _load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _clean(o):
    """NaN/inf -> None so key_metrics stays strict-JSON safe."""
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def _already(family, run_tag):
    for ln in pa_ledger.read_lines():
        km = ln.get("key_metrics") or {}
        if (ln.get("round") == "DR-MARKET" and ln.get("family") == family
                and km.get("run_tag") == run_tag):
            return ln.get("trial_id")
    return None


def emit(family, results_file, event_prefix, run_tag, supersedes,
         headline=None, spec_sha=PLAN_SHA, kind="market_study"):
    if _already(family, run_tag):
        print(f"  {family} run_tag={run_tag}: already in ledger, skip")
        return None
    res = _load(results_file) if results_file else {}
    km = {"run_tag": run_tag, "supersedes": supersedes}
    if headline:
        km.update(headline(res or {}))
    km = _clean(km)
    n = (res or {}).get("n_events") or (res or {}).get("n")
    tid = K.ledger_row(
        kind, family,
        {"results": results_file, "spec_sha256": spec_sha},
        km, n=n,
        extra={"data_sha256": _event_shas(event_prefix)
               if event_prefix else None})
    print(f"  {family} run_tag={run_tag}: -> {tid}")
    return tid


# ------------------------------------------------- headline extractors
def _fr(res):
    fr = res.get("families", {}).get("F-R", {})
    out = {}
    for k in ("S1", "S2", "PDHPDL", "ASIA", "RND"):
        r = fr.get(f"{k}_x1") or {}
        p = r.get("pooled") or {}
        out[f"{k}_x1_D"] = p.get("D")
        out[f"{k}_x1_q"] = r.get("q")
        out[f"{k}_x1_stable"] = r.get("stable")
    return out


def _metrics(res):
    """Generic headline extractor: every family/test row that carries a
    pooled D.  Keys are '<family>.<test>_{D,q,stable}'."""
    out = {}
    for fam, fv in (res.get("families") or {}).items():
        if not isinstance(fv, dict):
            continue
        for k, v in fv.items():
            if not isinstance(v, dict):
                continue
            p = (v or {}).get("pooled") or {}
            if "D" in p:
                out[f"{fam}.{k}_D"] = p.get("D")
                out[f"{fam}.{k}_q"] = (v or {}).get("q")
                out[f"{fam}.{k}_stable"] = (v or {}).get("stable")
    return out


def _fm(res):
    fm = res.get("families", {}).get("F-M", {})
    out = {"n_tests": len(fm)} if isinstance(fm, dict) else {}
    for k, v in list(fm.items())[:6]:
        if isinstance(v, dict):
            out[f"{k}_D"] = v.get("D") or (v.get("pooled") or {}).get("D")
    return out


ROWS = [
    ("M3", "m3_results.json", "m3_events", _fr),
    ("M4", "m4_results.json", "m4_events", _metrics),
    ("M4B", "m4b_results.json", "m4b_events", _metrics),
    ("M5", "m5_results.json", "m5_events", _metrics),
    ("M6", "m6_results.json", None, _fm),
]


def main():
    run_tag = sys.argv[1] if len(sys.argv) > 1 else "r2"
    sup = (sys.argv[2].split(",") if len(sys.argv) > 2
           and sys.argv[2] != "-" else [])
    only = (sys.argv[3].split(",") if len(sys.argv) > 3
            and sys.argv[3] != "-" else None)
    for fam, rfile, epfx, hl in ROWS:
        if only and fam not in only:
            continue
        if rfile and _load(rfile) is None:
            print(f"  {fam}: {rfile} missing, skip")
            continue
        spec = PLAN_SHA
        if fam == "M4B":
            # addendum hash = sha256 of STUDY_PLAN_ADDENDUM_M4B.md
            ap = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "STUDY_PLAN_ADDENDUM_M4B.md")
            spec = _sha_file(ap) if os.path.exists(ap) else PLAN_SHA
        emit(fam, rfile, epfx, run_tag, sup, headline=hl, spec_sha=spec)


if __name__ == "__main__":
    main()
