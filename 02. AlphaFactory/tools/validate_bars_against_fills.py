# validate_bars_against_fills.py — GATE A tool.
# Cross-checks hcc_reader bars against REAL governed fills (the ground
# truth for tradable prices). A reader bar that cannot contain the fill
# it hosted is fabricated — per the RGR-001 lesson.
#
# Usage:
#   python validate_bars_against_fills.py --run-dir <run_dir> --symbol USDCHF
#   python validate_bars_against_fills.py --lifecycle <csv> --symbol USDCHF
#
# Output: mismatch rate overall + by minute-of-day + worst examples.
import argparse
import csv
import datetime as dt
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hcc_reader import read_hcc_year_flagged, HISTORY_DIR  # noqa: E402


def load_fills(path):
    opens = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        if r["action"] == "OPEN":
            opens[r["position_id"]] = r
    return opens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir")
    ap.add_argument("--lifecycle")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--years", default="2010-2026")
    args = ap.parse_args()

    if args.lifecycle:
        f = args.lifecycle
    else:
        hits = glob.glob(str(Path(args.run_dir) / "logs" / f"{args.symbol}_LifecycleTrades_*.csv"))
        if not hits:
            sys.exit(f"no lifecycle CSV under {args.run_dir}/logs")
        f = hits[0]
    opens = load_fills(f)
    y0, y1 = (int(x) for x in args.years.split("-"))

    bars, suspect, _ = {}, set(), None
    for y in range(y0, y1 + 1):
        fp = HISTORY_DIR / args.symbol / f"{y}.hcc"
        if not fp.exists():
            continue
        b, s, _ = read_hcc_year_flagged(fp)
        bars.update(b)
        suspect |= s

    tot = inside = outside = in_suspect = 0
    by_min = {}
    worst = []
    for o in opens.values():
        et = dt.datetime.strptime(o["event_time"], "%Y.%m.%d %H:%M:%S")
        key = int(et.replace(tzinfo=dt.timezone.utc).timestamp()) // 60 * 60
        bar = bars.get(key)
        if not bar:
            continue
        tot += 1
        px = float(o["price"])
        ok = bar[2] - 1e-9 <= px <= bar[1] + 1e-9
        inside += ok
        outside += (not ok)
        in_suspect += (key in suspect)
        m = et.hour * 60 + et.minute
        by_min.setdefault(m, [0, 0])
        by_min[m][0] += 1
        by_min[m][1] += (not ok)
        if not ok:
            worst.append((abs(px - bar[0]), o["event_time"], px, bar[0], bar[1], bar[2]))

    print(f"fills checked: {tot}  inside-bar: {inside}  OUTSIDE: {outside} "
          f"({outside / max(1, tot):.1%})  fills-in-suspect-region: {in_suspect}")
    print("outside-rate by minute-of-day:")
    for m in sorted(by_min):
        n, o = by_min[m]
        if o:
            print(f"  {m // 60:02d}:{m % 60:02d}  {o}/{n} outside ({o / n:.0%})")
    worst.sort(reverse=True)
    print("worst divergences:")
    for w in worst[:10]:
        print(f"  {w[1]} fill={w[2]:.5f} bar=[{w[4]:.5f},{w[3]:.5f}] dev={w[0] * 1e4:.1f}p")


if __name__ == "__main__":
    main()
