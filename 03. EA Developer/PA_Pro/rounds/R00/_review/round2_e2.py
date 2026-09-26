"""R00 round-2 re-review — E2: re-run the 5 previously-UNCAUGHT mutations
against the CURRENT tests, on a copy under _review/r2mut, and check the
failure reason (test assertion, not a collection error)."""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MUT = os.path.join(HERE, "r2mut")

MUTATIONS = [
    ("resample_incomplete_ok", "pa_data.py",
     [("    dropped = int((agg[\"n\"] != n_src).sum())\n    agg = agg[agg[\"n\"] == n_src]",
       "    dropped = 0\n    agg = agg[agg[\"n\"] >= 1]"),
      ("    ok = (ends - starts) == n_src", "    ok = (ends - starts) >= 1")],
     "test_data_completeness.py"),
    ("warmup_flag_min", "pa_data.py",
     [("        \"c\": g[\"c\"].last(), \"n\": g[\"c\"].count(), \"warmup\": g[\"warmup\"].max(),",
       "        \"c\": g[\"c\"].last(), \"n\": g[\"c\"].count(), \"warmup\": g[\"warmup\"].min(),")],
     "test_data_completeness.py"),
    ("design_split_extended", "pa_sealed.py",
     [("    \"DESIGN\": (\"2016-01-01\", \"2022-01-01\"),",
       "    \"DESIGN\": (\"2016-01-01\", \"2022-07-01\"),")],
     "test_sealed_bounds.py"),
    ("fill_warmup_guard_off", "pa_fill.py",
     [("        if sig < first_live:\n            raise ValueError(",
       "        if False:\n            raise ValueError(")],
     "test_fill_warmup.py"),
    ("metrics_dd_linear", "pa_metrics.py",
     [("        eq *= (1.0 + 0.005 * rr[k])", "        eq += 0.005 * rr[k]")],
     "test_metrics_dd.py"),
]


def fresh_copy():
    if os.path.isdir(MUT):
        shutil.rmtree(MUT)
    shutil.copytree(os.path.join(PA, "lib"), os.path.join(MUT, "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PA, "tests"), os.path.join(MUT, "tests"),
                    ignore=shutil.ignore_patterns("__pycache__"))


def run_pytest(args):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--tb=line"] + args
    p = subprocess.run(cmd, cwd=MUT, capture_output=True, text=True, timeout=1800)
    out = (p.stdout or "") + (p.stderr or "")
    keep = [ln for ln in out.strip().splitlines()
            if ("FAILED" in ln or "failed" in ln or "error" in ln.lower()
                or "passed" in ln)]
    return p.returncode, keep[-6:]


print("== baseline: unmutated copy, FULL suite ==", flush=True)
fresh_copy()
rc, lines = run_pytest(["tests"])
print(f"baseline rc={rc}")
for ln in lines:
    print("   ", ln)

for mid, fname, repls, target in MUTATIONS:
    fresh_copy()
    path = os.path.join(MUT, "lib", fname)
    text = open(path, encoding="utf-8").read()
    ok = True
    for old, new in repls:
        if text.count(old) != 1:
            print(f"[{mid}] NOT-APPLIED: {text.count(old)} occurrences")
            ok = False
            break
        text = text.replace(old, new)
    if not ok:
        continue
    open(path, "w", encoding="utf-8").write(text)
    t0 = time.time()
    rc, lines = run_pytest(["tests", "--tb=line"])
    status = "CAUGHT" if rc == 1 else ("UNCAUGHT" if rc == 0 else f"rc={rc}")
    print(f"[{mid}] {status} rc={rc} ({time.time()-t0:.1f}s) target={target}")
    for ln in lines:
        print("   ", ln)
    # right-reason check: must be a test failure, not a collection error
    joined = " ".join(lines)
    print("    collection-error:", "error during collection" in joined)
