"""R00 review — attack 1b: refined mutations that were invalid in pass 1."""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MUT = os.path.join(HERE, "mut2")

MUTATIONS = [
    ("no_bypass_body_return", "pa_metrics.py",
     [("def _require_token(token):\n    fn = _TOKEN_CHECKER.get(\"fn\")",
       "def _require_token(token):\n    return\n    fn = _TOKEN_CHECKER.get(\"fn\")")],
     ["test_no_bypass.py"]),
    ("resample_incomplete_ok", "pa_data.py",
     [("    dropped = int((agg[\"n\"] != n_src).sum())\n    agg = agg[agg[\"n\"] == n_src]",
       "    dropped = 0\n    agg = agg[agg[\"n\"] >= 1]"),
      ("    ok = (ends - starts) == n_src", "    ok = (ends - starts) >= 1")],
     []),
    ("ledger_write_devnull", "pa_ledger.py",
     [("        with open(_LEDGER_PATH, \"ab\") as f:", "        with open(os.devnull, \"wb\") as f:")],
     ["test_eval_ledger.py", "test_ledger.py"]),
    ("metrics_dd_linear", "pa_metrics.py",
     [("        eq *= (1.0 + 0.005 * rr[k])", "        eq += 0.005 * rr[k]")],
     []),
]


def fresh_copy():
    if os.path.isdir(MUT):
        shutil.rmtree(MUT)
    shutil.copytree(os.path.join(PA, "lib"), os.path.join(MUT, "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PA, "tests"), os.path.join(MUT, "tests"),
                    ignore=shutil.ignore_patterns("__pycache__"))


def run_pytest(tests):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    cmd += [os.path.join("tests", t) for t in tests] if tests else ["tests"]
    p = subprocess.run(cmd, cwd=MUT, capture_output=True, text=True, timeout=1200)
    out = (p.stdout or "") + (p.stderr or "")
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-2:]
    return p.returncode, " | ".join(tail)


for mid, fname, repls, tests in MUTATIONS:
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
    rc, tail = run_pytest(tests)
    print(f"[{mid}] {'CAUGHT' if rc else 'UNCAUGHT'} rc={rc}: {tail}", flush=True)
