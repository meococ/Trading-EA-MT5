"""C1 pre-check (MIGRATION_PLAN rev2): did joint rate_total ever bind?
Counts 'rate_limited' vetoes in cand_log across all cached C-3 pickles.
rate_limited covers cap_r(per-family)+ctx_full+mini_full+joint_full;
zero/rare => joint cap provably non-binding on canonical set."""
import pickle, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "evalcheck"))
import cache as CA

pkls = sorted(Path("_scratch").rglob("uip2_pbbirth@8361fe85*.pkl"))
print("cache files:", len(pkls))
tot = collections.Counter(); panels_with = 0
for p in pkls:
    try:
        e = pickle.loads(p.read_bytes())
    except Exception as ex:
        print("ERR", p.name, ex); continue
    n = 0
    for row in getattr(e, "cand_log", []):
        if isinstance(row, dict) and row.get("outcome") == "rate_limited":
            tot[row.get("kind", "?")] += 1; n += 1
        elif isinstance(row, (list, tuple)) and len(row) >= 4 and row[3] == "rate_limited":
            tot[row[0] if isinstance(row[0], str) else "?"] += 1; n += 1
    if n: panels_with += 1
print("rate_limited vetoes by kind:", dict(tot))
print("panels with any:", panels_with, "/", len(pkls))
