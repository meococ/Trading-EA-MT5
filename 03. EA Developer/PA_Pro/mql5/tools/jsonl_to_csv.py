"""jsonl_to_csv.py - project perception_v1 JSONL snapshots onto the
perception_csv_v1 wire format the MQL5 side reads (PA_Perception.mqh).

The canonical engine output (research/perception, post-P-FREEZE) is
JSONL: one Snapshot per line, matching schema/perception_v1.json.
Schema times are M5 bar INDICES; the CSV wire format carries SERVER
EPOCHS so the epoch stays the join key and bar indices never cross the
wire.

Index -> epoch mapping: each JSONL line carries `t` (bar index) and
`t_cet` (CET wall clock).  Server epoch = CET-as-UTC + 1h (perception
D2: server = CET + 1h whenever markets are open).  Every line contributes
one map entry; object t_left/t_right/geometry indices resolve through
it.  Indices missing from the map (objects born before the export
window) fall back to nearest + 300 s/bar with a warning count.

A flat file (no bar_t) is emitted with --flat; default output carries
the leading bar_t column (per-bar parity mode).  Non-empty
`stand_aside[]` codes emit a provisional STAND_ASIDE pseudo-row for the
bar (t1=t2=bar epoch, why=first code).

    python jsonl_to_csv.py <snapshots.jsonl> <out.csv> [--flat]

Pure stdlib; no pa_slot needed (no data files touched).
"""

import csv
import datetime as dt
import json
import sys

SERVER_MINUS_CET = 3600  # server wall clock = CET + 1h (perception D2)


def cet_to_epoch(iso):
    """'YYYY-MM-DDTHH:MM[:SS]' CET wall time -> server epoch.

    pa_data/MqlRates `t` values are epochs whose UTC reading equals the
    broker's server wall clock.  Server wall = CET + 1h (D2), so the
    server epoch is the t_cet wall reading plus one hour.
    """
    s = iso.replace(" ", "T")[:19]
    naive = dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    return int(naive.replace(tzinfo=dt.timezone.utc).timestamp()) \
        + SERVER_MINUS_CET


def idx2epoch(idx_map, warn, i):
    if i in idx_map:
        return idx_map[i]
    if not idx_map:
        raise SystemExit(
            "no t_cet seen yet and no --bars map: cannot resolve idx %d" % i)
    warn.append(i)
    near = min(idx_map, key=lambda k: abs(k - i))
    return idx_map[near] + (i - near) * 300


def row(bar, o, idx_map, warn):
    """-> csv row dict for one schema object (or None if unmappable)."""
    e = lambda i: idx2epoch(idx_map, warn, i) if i is not None else 0
    typ = o["type"]
    g = o.get("geometry", {})
    t1 = e(o.get("t_left"))
    t2 = e(o.get("t_right"))
    p1 = p2 = 0.0
    letter = side = ""
    if typ in ("BOX", "CONTEXT_RANGE", "RANGE_OPEN"):
        p2, p1 = g["top"], g["bottom"]
    elif typ in ("PATTERN_LINE", "CONTEXT_LINE"):
        a1, a2 = g["anchor1"], g["anchor2"]
        t1, t2, p1, p2 = e(a1["t"]), e(a2["t"]), a1["price"], a2["price"]
        if g.get("extends_to") is None:
            t2 = 0                      # open -> project right
    elif typ == "LEVEL_CARRIED":
        p1 = g["price"]
        t2 = 0                          # projects right
    elif typ == "MINI_LEVEL":
        p1 = g["price"]
    elif typ == "SQUEEZE":
        t1, t2 = e(g["t0"]), e(g["t1"])
        p1, p2 = g["price_lo"], g["price_hi"]
    elif typ == "LABEL_TF":
        letter, t1, side = g["letter"], e(g["t_bar"]), g.get("side", "")
        p1 = g.get("price") or 0.0
    elif typ == "BRACKET":
        letter, t1, t2 = g["letter"], e(g["t0"]), e(g["t1"])
        side = g.get("side", "")
        p1 = g.get("mid_price") or 0.0
    elif typ == "FALSE_EXT":
        t1, p1, side = e(g["t_bar"]), g["price"], g.get("side", "")
    return {
        "bar_t": bar, "id": o["id"], "type": typ,
        "state": o.get("state", "ACTIVE"), "role": o.get("role", ""),
        "t_birth": e(o.get("t_birth")), "t1": t1, "t2": t2,
        "p1": p1, "p2": p2, "letter": letter, "side": side,
        "why": o.get("why", "")}


def main():
    src, out = sys.argv[1], sys.argv[2]
    flat = "--flat" in sys.argv
    idx_map, warn, rows = {}, [], []
    n_lines = 0
    with open(src, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            snap = json.loads(line)
            n_lines += 1
            bar_idx = snap["t"]
            bar_ep = cet_to_epoch(snap["t_cet"]) if "t_cet" in snap else None
            if bar_ep is not None:
                idx_map[bar_idx] = bar_ep
            else:
                bar_ep = idx2epoch(idx_map, warn, bar_idx)
            for o in snap.get("objects", []):
                r = row(bar_ep, o, idx_map, warn)
                if r:
                    rows.append(r)
            codes = snap.get("stand_aside") or []
            if codes:
                rows.append({
                    "bar_t": bar_ep, "id": "stand_aside_%d" % bar_idx,
                    "type": "STAND_ASIDE", "state": "ACTIVE", "role": "",
                    "t_birth": bar_ep, "t1": bar_ep, "t2": bar_ep,
                    "p1": 0.0, "p2": 0.0, "letter": "", "side": "",
                    "why": codes[0]})
    cols = (["bar_t"] if not flat else []) + [
        "id", "type", "state", "role", "t_birth", "t1", "t2",
        "p1", "p2", "letter", "side", "why"]
    with open(out, "w", newline="", encoding="ascii") as f:
        w = csv.DictWriter(f, fieldnames=cols,
                           extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("wrote %s: %d rows from %d snapshots%s" % (
        out, len(rows), n_lines,
        "" if not warn else "  (%d idx->epoch fallbacks!)" % len(set(warn))))


if __name__ == "__main__":
    main()
