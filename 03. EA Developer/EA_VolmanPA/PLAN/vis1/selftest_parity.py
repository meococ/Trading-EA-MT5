"""Self-test for `compare_parity.py` — synthetic M5 series, no MT5, no pandas.

Stages:
  1. build a deterministic ~4000-bar M5 series (random.Random(7), EURUSD-like
     ~1.10, 5-decimal OHLC, contiguous 300 s, server start 2019-02-25 00:00)
     and write `_selftest/VPA_Vision_bars.csv` (schema A);
  2. run the frozen DR3 detector on that series and write the Python mirrors
     `_selftest/VPA_Vision_events.csv` + `_selftest/VPA_Vision_barriers.csv`
     (schemas B/C) with the same writers the comparator uses;
  3. run `compare_parity.py` on `_selftest` with `--min-match 1.0`; require
     exit 0, last line `PARITY: PASS`, `match_rate=1.000000`;
  4. copy the three files to `_selftest/mut`, perturb one `entry` (+0.0001) and
     one `verdict`, re-run; require exit 2, last line `PARITY: FAIL` and
     `total_mismatched=2`.

Prints `SELFTEST: PASS` only when stages 3+4 behave as expected, else exits
non-zero with `SELFTEST: FAIL`.

Run from this directory: `python selftest_parity.py`.
"""

import calendar
import os
import random
import re
import shutil
import subprocess
import sys
from datetime import datetime

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from compare_parity import (  # noqa: E402
    EVENT_FIELDS,
    build_py_barriers,
    build_py_events,
    run_detector,
    srv_utc_minutes,
    write_barriers_csv,
    write_bars_csv,
    write_events_csv,
)

SELFTEST_DIR = os.path.join(HERE, "_selftest")
MUT_DIR = os.path.join(SELFTEST_DIR, "mut")
COMPARATOR = os.path.join(HERE, "compare_parity.py")

N_BARS = 4000
PIP = 1e-4
TICK = 1e-5
START = datetime(2019, 2, 25, 0, 0)
T0 = calendar.timegm(START.timetuple())


def build_bars():
    """Deterministic 4000-bar M5 series with alternating volatility regimes."""
    rng = random.Random(7)
    t, o, h, l, c = [], [], [], [], []
    px = 1.10000
    for i in range(N_BARS):
        phase = (i // 250) % 4
        sd = (0.00006, 0.00012, 0.00025, 0.00010)[phase]
        drift = (0.000004, 0.0, -0.000006, 0.000002)[phase]
        o_i = px
        c_i = o_i + rng.gauss(drift, sd)
        up = abs(rng.gauss(0.0, sd * 0.8)) + TICK
        dn = abs(rng.gauss(0.0, sd * 0.8)) + TICK
        h_i = max(o_i, c_i) + up
        l_i = min(o_i, c_i) - dn
        o_i, h_i, l_i, c_i = (round(x, 5) for x in (o_i, h_i, l_i, c_i))
        t.append(T0 + i * 300)
        o.append(o_i)
        h.append(h_i)
        l.append(l_i)
        c.append(c_i)
        px = c_i
    srv, utc = [], []
    for x in t:
        s, u = srv_utc_minutes(x)
        srv.append(s)
        utc.append(u)
    return {"symbol": "EURUSD", "t": t, "o": o, "h": h, "l": l, "c": c,
            "utc_min": utc, "srv_min": srv, "pip": PIP, "tick": TICK}


def run_comparator(directory, min_match, out_path):
    cmd = [sys.executable, COMPARATOR, "--dir", directory,
           "--min-match", str(min_match), "--out", out_path]
    print("$ %s" % " ".join(cmd))
    proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print("stderr:")
        print(proc.stderr.rstrip())
    return proc


def parse_summary(stdout):
    rate = re.search(r"match_rate=([0-9.]+)", stdout)
    mism = re.search(r"total_mismatched=(\d+)", stdout)
    return (float(rate.group(1)) if rate else None,
            int(mism.group(1)) if mism else None)


def last_line(stdout):
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def mutate_events(src_path, dst_path):
    """Perturb one `entry` (+0.0001) and one `verdict`; returns the row pair."""
    with open(src_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    header, data = lines[0], lines[1:]
    assert header == ",".join(EVENT_FIELDS), "events header mismatch"
    i_entry = EVENT_FIELDS.index("entry")
    i_verdict = EVENT_FIELDS.index("verdict")
    row_e = next(i for i, ln in enumerate(data)
                 if ln.split(",")[i_entry] != "")
    row_v = len(data) - 1
    assert row_v != row_e, "fixture too small for the mutation test"
    cells = data[row_e].split(",")
    cells[i_entry] = "%.8f" % (float(cells[i_entry]) + 0.0001)
    data[row_e] = ",".join(cells)
    cells = data[row_v].split(",")
    cells[i_verdict] = "SKIP" if cells[i_verdict] == "ACCEPT" else "ACCEPT"
    data[row_v] = ",".join(cells)
    with open(dst_path, "w", newline="\n", encoding="utf-8") as f:
        f.write("\n".join([header] + data) + "\n")
    return row_e, row_v


def main():
    os.makedirs(SELFTEST_DIR, exist_ok=True)
    bars_path = os.path.join(SELFTEST_DIR, "VPA_Vision_bars.csv")
    events_path = os.path.join(SELFTEST_DIR, "VPA_Vision_events.csv")
    barriers_path = os.path.join(SELFTEST_DIR, "VPA_Vision_barriers.csv")

    print("== stage 1: synthetic series ==")
    bars = build_bars()
    write_bars_csv(bars_path, bars)
    print("bars=%d  first=%s  last=%s"
          % (len(bars["t"]), bars["t"][0], bars["t"][-1]))

    print("== stage 2: python DR3 mirror ==")
    d, recs, counters = run_detector(bars)
    events = build_py_events(recs)
    barriers = build_py_barriers(d, recs, len(bars["t"]) - 1)
    write_events_csv(events_path, events)
    write_barriers_csv(barriers_path, barriers)
    n_acc = sum(1 for r in events if r["verdict"] == "ACCEPT")
    n_entry = sum(1 for r in events if r["entry"] is not None)
    kinds = {}
    for b in barriers:
        kinds[b["end_kind"]] = kinds.get(b["end_kind"], 0) + 1
    print("records=%d events=%d accept=%d with_entry=%d barriers=%d kinds=%s"
          % (len(recs), len(events), n_acc, n_entry, len(barriers),
             sorted(kinds.items())))
    assert len(events) > 100, "fixture produced too few events"
    assert n_entry > 0, "fixture produced no evaluable entry"
    assert len(barriers) > 10, "fixture produced too few barriers"

    print("== stage 3: comparator on the python mirror ==")
    proc3 = run_comparator(SELFTEST_DIR, 1.0,
                           os.path.join(SELFTEST_DIR, "PARITY_REPORT.md"))
    rate3, mism3 = parse_summary(proc3.stdout)
    ok3 = (proc3.returncode == 0 and last_line(proc3.stdout) == "PARITY: PASS"
           and rate3 is not None and abs(rate3 - 1.0) < 1e-12
           and mism3 == 0)
    print("stage 3: exit=%d rate=%s mismatched=%s last=%r -> %s"
          % (proc3.returncode, rate3, mism3, last_line(proc3.stdout),
             "OK" if ok3 else "BAD"))

    print("== stage 4: mutation test ==")
    os.makedirs(MUT_DIR, exist_ok=True)
    shutil.copyfile(bars_path, os.path.join(MUT_DIR, "VPA_Vision_bars.csv"))
    shutil.copyfile(barriers_path,
                    os.path.join(MUT_DIR, "VPA_Vision_barriers.csv"))
    row_e, row_v = mutate_events(events_path,
                                 os.path.join(MUT_DIR,
                                              "VPA_Vision_events.csv"))
    print("mutated event rows: entry row=%d, verdict row=%d" % (row_e, row_v))
    proc4 = run_comparator(MUT_DIR, 1.0,
                           os.path.join(MUT_DIR, "PARITY_REPORT.md"))
    rate4, mism4 = parse_summary(proc4.stdout)
    ok4 = (proc4.returncode == 2 and last_line(proc4.stdout) == "PARITY: FAIL"
           and mism4 == 2)
    print("stage 4: exit=%d rate=%s mismatched=%s last=%r -> %s"
          % (proc4.returncode, rate4, mism4, last_line(proc4.stdout),
             "OK" if ok4 else "BAD"))

    if ok3 and ok4:
        print("SELFTEST: PASS")
        return 0
    print("SELFTEST: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
