"""phys_freeze — write rounds/R01/FREEZE.json BEFORE any outcome exists.

SHA256 of: PHYSICS_PREREG.md, CHARTER_ADDENDUM_2.md, sorted struct/zones/*.py,
sorted research/physics/*.py, sorted lib/*.py, and every EVENTS/CONTROLS CSV
written by `run_bakeoff.py build`; plus per-generator pooled-core q33/q67,
coverage, extraction counters, seed, split and data-file stamps.
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import phys_common as pc  # noqa: E402
import pa_ledger  # noqa: E402  (lib/ is on sys.path via phys_common)

OUT = os.path.join(HERE, "bakeoff")
ROUNDS = os.path.join(pc.PA_PRO, "rounds", "R01")
CACHE = os.environ.get("PA_M1_CACHE", os.path.normpath(os.path.join(pc.PA_PRO, "..", "..", "02. AlphaFactory", "lab", "cache")))


def _anchor_record():
    """Append the current ledger head to ``ledger/ANCHORS.jsonl`` and return
    the FREEZE.json view of the same record (R02-F: the freeze writer emits
    the anchor; the mechanism is only real when the artifact exists)."""
    rec = pa_ledger.append_anchor(note=f"freeze {ROUNDS} (phys_freeze.main)")
    return {k: rec[k] for k in ("ledger", "n_lines", "sha256", "utc")}


def main():
    names = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(pc.ZONES_DIR, "*.py")))
    import registry

    gens = registry.names()
    free = {
        "utc": pc.utc_now(),
        "round": "R01",
        "phase": "physics-zone-bakeoff",
        "seed": pc.SEED,
        "split": "DESIGN",
        "tf": "M5",
        "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
        "prereg_sha256": pc.sha256_file(os.path.join(ROUNDS, "PHYSICS_PREREG.md")),
        "addendum2_sha256": pc.sha256_file(os.path.join(
            pc.PA_PRO, "docs", "CHARTER_ADDENDUM_2.md")),
        "addendum1_sha256": pc.sha256_file(os.path.join(
            pc.PA_PRO, "docs", "CHARTER_ADDENDUM_1.md")),
        "charter_sha256": pc.sha256_file(os.path.join(
            pc.PA_PRO, "PA_PRO_CHARTER.md")),
        "runbook_sha256": pc.sha256_file(os.path.join(
            ROUNDS, "00_LEAD_RULINGS_READ_FIRST.md")),
        "shortlist_sha256": pc.sha256_file(os.path.join(
            pc.PA_PRO, "research", "zones", "SHORTLIST.md")),
        "zones_review_sha256": pc.sha256_file(os.path.join(
            pc.PA_PRO, "research", "zones", "REVIEW_ZONE1.md")),
        "parity_sha256": pc.sha256_file(os.path.join(ROUNDS, "PARITY.md")),
        "zones_code_sha256": pc.dir_code_sha256(pc.ZONES_DIR),
        "lib_code_sha256": pc.dir_code_sha256(pc.LIB_DIR),
        "physics_code_sha256": pc.dir_code_sha256(HERE),
        "zone_modules": names,
        "generators": {},
        "tables": {},
        "data_files": {},
    }
    # R02-C/R02-F: anchor the ledger head INTO the freeze AND into
    # ledger/ANCHORS.jsonl, so a later rewrite/truncation of the covered
    # prefix is detectable ex post (charter section 6).
    free["ledger_anchor"] = _anchor_record()
    # data file stamps (cheap; content hashes of 100-200MB parquet are not)
    for f in sorted(glob.glob(os.path.join(CACHE, "*_M1_2010_2026.parquet"))):
        st = os.stat(f)
        free["data_files"][os.path.basename(f)] = {
            "size": int(st.st_size), "mtime": int(st.st_mtime)}
    # tables + tercile bounds (pooled core)
    import phys_extract as px

    for gen in gens:
        strengths = []
        bounds = None
        for sym in free["symbols"]:
            epath = os.path.join(OUT, f"EVENTS_{sym}_{gen}.csv")
            cpath = os.path.join(OUT, f"CONTROLS_{sym}_{gen}.csv")
            for p in (epath, cpath):
                if os.path.exists(p):
                    free["tables"][os.path.basename(p)] = pc.sha256_file(p)
            if os.path.exists(epath):
                for e in px.read_events_csv(epath):
                    strengths.append(float(e["strength"]))
        if strengths:
            bounds = list(px.tercile_bounds(strengths))
        cov = None
        counters = {}
        for sym in free["symbols"]:
            cj = os.path.join(OUT, f"COUNTERS_{sym}.json")
            if os.path.exists(cj):
                with open(cj, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if gen in data:
                    counters[sym] = {"extract": data[gen]["extract"],
                                     "controls": data[gen]["controls"],
                                     "coverage_med": data[gen]["coverage_med"],
                                     "n_events": data[gen]["n_events"]}
                    cov = data[gen]["coverage_med"]
        free["generators"][gen] = {
            "tercile_bounds": bounds, "coverage_med": cov,
            "per_symbol": counters,
        }
    path = os.path.join(ROUNDS, "FREEZE.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(free, f, indent=1, sort_keys=True)
    print("wrote", path)
    print("freeze_file_sha256", pc.sha256_file(path))
    for gen in gens:
        g = free["generators"][gen]
        print(f"{gen}: q33/q67={g['tercile_bounds']} cov={g['coverage_med']}")


if __name__ == "__main__":
    main()
