"""R00 FIXER — reproduce the reviewer's 5 uncaught mutations (E2) against the
NEW targeted tests.  Works on a copy under `_review/fixcheck/mut`; the real
tree is never modified.

Run:  python "03. EA Developer/PA_Pro/rounds/R00/_review/fixcheck/fixcheck_mutations.py"
"""

import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(HERE))))                                   # PA_Pro
MUT = os.path.join(HERE, "mut")

MUTATIONS = [
    ("resample_incomplete_ok", "pa_data.py",
     [("    dropped = int((agg[\"n\"] != n_src).sum())\n"
       "    agg = agg[agg[\"n\"] == n_src]",
       "    dropped = 0\n    agg = agg[agg[\"n\"] >= 1]"),
      ("    ok = (ends - starts) == n_src", "    ok = (ends - starts) >= 1")],
     ["test_data_completeness.py"]),
    ("design_split_extended", "pa_sealed.py",
     [("    \"DESIGN\": (\"2016-01-01\", \"2022-01-01\"),",
       "    \"DESIGN\": (\"2016-01-01\", \"2022-07-01\"),")],
     ["test_sealed_bounds.py"]),
    ("warmup_flag_min", "pa_data.py",
     [("        \"c\": g[\"c\"].last(), \"n\": g[\"c\"].count(), "
       "\"warmup\": g[\"warmup\"].max(),",
       "        \"c\": g[\"c\"].last(), \"n\": g[\"c\"].count(), "
       "\"warmup\": g[\"warmup\"].min(),")],
     ["test_data_completeness.py"]),
    ("fill_warmup_guard_off", "pa_fill.py",
     [("        if sig < first_live:\n            raise ValueError(",
       "        if False:\n            raise ValueError(")],
     ["test_fill_warmup.py"]),
    ("metrics_dd_linear", "pa_metrics.py",
     [("        eq *= (1.0 + 0.005 * rr[k])", "        eq += 0.005 * rr[k]")],
     ["test_metrics_dd.py"]),
]


def fresh_copy():
    if os.path.isdir(MUT):
        shutil.rmtree(MUT)
    shutil.copytree(os.path.join(PA, "lib"), os.path.join(MUT, "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PA, "tests"), os.path.join(MUT, "tests"),
                    ignore=shutil.ignore_patterns("__pycache__"))


def run_pytest(tests):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--tb=line"]
    cmd += [os.path.join("tests", t) for t in tests]
    p = subprocess.run(cmd, cwd=MUT, capture_output=True, text=True, timeout=1200)
    out = (p.stdout or "") + (p.stderr or "")
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-2:]
    return p.returncode, " | ".join(tail)


def main():
    print("== baseline: unmutated copy, targeted tests ==", flush=True)
    fresh_copy()
    rc, tail = run_pytest([t for _, _, _, ts in MUTATIONS for t in ts])
    print(f"baseline rc={rc}: {tail}", flush=True)
    results = []
    for mid, fname, repls, tests in MUTATIONS:
        fresh_copy()
        path = os.path.join(MUT, "lib", fname)
        text = open(path, encoding="utf-8").read()
        ok = True
        for old, new in repls:
            n = text.count(old)
            if n != 1:
                results.append((mid, "NOT-APPLIED",
                                f"{text.count(old)} occurrences, expected 1"))
                print(f"[{mid}] NOT-APPLIED ({n} occurrences)", flush=True)
                ok = False
                break
            text = text.replace(old, new)
        if not ok:
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        t0 = time.time()
        rc, tail = run_pytest(tests)
        caught = rc != 0
        results.append((mid, "CAUGHT" if caught else "UNCAUGHT", tail))
        print(f"[{mid}] {'CAUGHT' if caught else 'UNCAUGHT'} rc={rc} "
              f"({time.time()-t0:.1f}s): {tail}", flush=True)
    print("== summary ==", flush=True)
    for mid, status, info in results:
        print(f"{status:11s} {mid}", flush=True)


if __name__ == "__main__":
    main()
