"""result_row.py - one machine-readable row per measured arm (LEAD_RULINGS R67).

Every A/B result, independent verification or lab count that reports M1 numbers gets ONE row here,
in addition to the lane's prose log. The Lead reads this table by script at every check.

Append a row (run from the PA_Pro folder):
    python research/perception/tools/result_row.py add --lane build --arm uip2_lvfree --hash 6d955783 \
        --parent 4c2df34d --box 16/119 --level 7/76 --line 23/193 --bracket 29/85 --clutter 4.67 \
        --margin 95/179 --births 1.0 --suite 71/72 --offid 1728/1728 --verdict FAIL --by self \
        --note "level -1 ok; suite new failure test_x"
Show the last rows:
    python research/perception/tools/result_row.py show [-n 20] [--lane build] [--arm uip2]

Rules: the time comes from the system clock; counts are "hits/total"; verdict is one of
PASS, FAIL, INERT, INFO, KEEP, REVERT; --by is "self" for the lane's own number or the name of the
lane that verified it independently. Rows are never edited: a correction is a new row with a note.
"""
import argparse
import datetime as _dt
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(TOOLS, '..', 'status', 'results.jsonl'))
FRAC = re.compile(r'^\d+/\d+$')
VERDICTS = ('PASS', 'FAIL', 'INERT', 'INFO', 'KEEP', 'REVERT')
FRAC_FIELDS = ('box', 'level', 'line', 'bracket', 'margin', 'suite', 'offid')
COLS = ('t', 'lane', 'arm', 'hash', 'parent', 'box', 'level', 'line', 'bracket', 'clutter', 'margin',
        'births', 'suite', 'offid', 'verdict', 'by', 'note')


def now():
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def add(a):
    row = {'t': now()}
    for k in COLS[1:]:
        v = getattr(a, k, None)
        if v is not None:
            row[k] = v
    for k in FRAC_FIELDS:
        if k in row and not FRAC.match(str(row[k])):
            sys.exit('bad %s=%r: use hits/total, e.g. 16/119' % (k, row[k]))
    for k in ('clutter', 'births'):
        if k in row:
            try:
                row[k] = float(row[k])
            except ValueError:
                sys.exit('bad %s=%r: number expected' % (k, row[k]))
    if row.get('verdict') not in VERDICTS:
        sys.exit('verdict must be one of %s' % (VERDICTS,))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=True) + '\n')
    print('row added: %s %s %s %s' % (row['t'], row['lane'], row['arm'], row['verdict']))
    return 0


def show(a):
    if not os.path.exists(OUT):
        print('(no rows yet)')
        return 0
    rows = []
    with open(OUT, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if a.lane and r.get('lane') != a.lane:
                continue
            if a.arm and a.arm not in str(r.get('arm', '')):
                continue
            rows.append(r)
    rows = rows[-a.n:]
    cols = [c for c in COLS if c != 'note']
    print(' | '.join(cols) + ' | note')
    for r in rows:
        print(' | '.join(str(r.get(c, '')) for c in cols) + ' | ' + str(r.get('note', ''))[:120])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('add')
    p.add_argument('--lane', required=True)
    p.add_argument('--arm', required=True)
    p.add_argument('--hash', required=True)
    p.add_argument('--parent')
    for k in ('box', 'level', 'line', 'bracket', 'clutter', 'margin', 'births', 'suite', 'offid'):
        p.add_argument('--' + k)
    p.add_argument('--verdict', required=True)
    p.add_argument('--by', required=True)
    p.add_argument('--note')
    s = sub.add_parser('show')
    s.add_argument('-n', type=int, default=20)
    s.add_argument('--lane')
    s.add_argument('--arm')
    a = ap.parse_args()
    return add(a) if a.cmd == 'add' else show(a)


if __name__ == '__main__':
    sys.exit(main())
