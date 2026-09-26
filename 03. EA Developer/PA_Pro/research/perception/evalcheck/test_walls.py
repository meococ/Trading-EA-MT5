"""test_walls.py — planted-violation tests for walls_check positive
checks (mandate W4 / Ruling 13 §13.7).

Builds synthetic .py fixtures in a temp dir and runs scan_file_a /
scan_file_b directly: an exempted-pattern file (imports a door, npz
io, HOLD prose) must still be caught when it plants a real violation.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import walls_check as W                       # noqa: E402


def _mk(td, name, body):
    p = os.path.join(td, name)
    open(p, "w", encoding="utf8").write(body)
    return p


def run():
    res = []
    with tempfile.TemporaryDirectory() as td:
        # 1. clean cache file: door import + npz io + HOLD docstring
        p = _mk(td, "ok_cache.py",
                '"""Reads cached bars.  HOLD is never touched."""\n'
                'import book_loader\nimport numpy as np\n'
                'np.savez("c.npz", x=1)\nz = np.load("c.npz")\n')
        res.append(("clean cache file",
                    not W.scan_file_b(p, "ok_cache.py")[1]
                    and not W.scan_file_a(p, "ok_cache.py")[1]))

        # 2. npz io WITHOUT a door import -> violation
        p = _mk(td, "bad_cache.py",
                'import numpy as np\nnp.load("bars.npz")\n')
        res.append(("np-io without door import caught",
                    W.scan_file_b(p, "bad_cache.py")[1]))

        # 3. door-importing file planting a direct parquet path ->
        #    caught anyway (positive pattern does not exempt paths)
        p = _mk(td, "sneaky.py",
                'import book_loader\n'
                'bars = open("EURUSD_M1_2012.parquet", "rb")\n')
        res.append(("direct parquet path caught despite door import",
                    W.scan_file_b(p, "sneaky.py")[1]))

        # 4. HOLD in a comment line -> ignored; in code -> caught
        p = _mk(td, "hold_comment.py", "# never reads HOLD files\n")
        res.append(("HOLD comment ignored",
                    not W.scan_file_a(p, "hold_comment.py")[1]))
        p = _mk(td, "hold_doc.py",
                '"""TUNE only; HOLD is never read."""\nx = 1\n')
        res.append(("HOLD docstring ignored",
                    not W.scan_file_a(p, "hold_doc.py")[1]))
        p = _mk(td, "hold_code.py", 'split = "HOLD"\n')
        res.append(("HOLD code string caught",
                    W.scan_file_a(p, "hold_code.py")[1]))

        # 5. evalcheck-style file: 'import cache' counts as a door
        p = _mk(td, "via_cache.py",
                'import cache as CA\nimport numpy as np\n'
                'np.load("x.npy")\n')
        res.append(("evalcheck cache import counts as door",
                    not W.scan_file_b(p, "via_cache.py")[1]))

        # 6. out-of-window year literal without door -> caught
        p = _mk(td, "year.py", 'RANGE = "2013-01-01"\n')
        res.append(("non-TUNE year without door caught",
                    W.scan_file_b(p, "year.py")[1]))

    ok = True
    for name, good in res:
        print("  %-55s %s" % (name, "PASS" if good else "FAIL"))
        ok &= bool(good)
    print("test_walls:", "ALL PASS" if ok else "FAILURES")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
