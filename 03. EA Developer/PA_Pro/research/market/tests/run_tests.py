"""DR-MARKET known-answer suite runner (Ruling 3 gate).

Runs every tests/test_*.py module: resolver (F1), bootstrap (F2),
look-ahead canary (F5), symbol decode (F3).  Each module also contains
verbatim pre-fix logic demonstrating that the OLD code fails the same
fixtures — so the suite is evidence, not ceremony.

Usage:  python tests/run_tests.py      (exit 0 = all pass)
"""
import importlib
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

MODULES = ["test_resolver", "test_contrast_boot", "test_lookahead",
           "test_decode"]


def main():
    total, failed = 0, 0
    for mod in MODULES:
        m = importlib.import_module(mod)
        for name in sorted(dir(m)):
            if not name.startswith("test_"):
                continue
            total += 1
            try:
                getattr(m, name)()
                print(f"  PASS {mod}.{name}")
            except Exception:
                failed += 1
                print(f"  FAIL {mod}.{name}")
                traceback.print_exc(limit=2)
    print(f"\n{total - failed}/{total} tests pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
