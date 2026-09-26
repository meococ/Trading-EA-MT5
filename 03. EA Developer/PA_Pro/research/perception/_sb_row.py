"""_sb_row.py — append a scoreboard row for a pinned hash + arm variant.

scoreboard.py computes eng_hash from the live tree; for one-hash A/B
the arm caches sit under the A/B's pinned hash, so measure() must be
called with that hash explicitly.  Rows append to evalcheck/
SCOREBOARD.md + _scoreboard_rows.jsonl (the mandated reporting channel,
R34 §34.8.1.3 "scoreboard rows as before").

Usage: python _sb_row.py <eng_hash> <variant> [lane]
"""
import os
import sys

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")

import datetime
import common as C
import engine as ENG
import scoreboard as SB
import pa_slots


def main():
    eng_hash, variant = sys.argv[1], sys.argv[2]
    lane = sys.argv[3] if len(sys.argv) > 3 else "build"
    recs = C.load_tune()
    ruler_hash = SB.file_hash(os.path.join(SB.HERE, "eval_v2.py"))
    with pa_slots.slot("evalcheck-scoreboard", timeout=600):
        row = SB.measure(ENG.PerceptionEngine, eng_hash, recs,
                         variant=variant)
    utc = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%MZ")
    line = SB.append_row(utc, "v1", eng_hash, ruler_hash, row,
                         lane=lane, variant=variant)
    print(line)


if __name__ == "__main__":
    main()
