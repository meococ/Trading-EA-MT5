"""R00 review — attack 1: mutation testing driver.

Copies PA_Pro/lib + PA_Pro/tests into _review/mut, applies one mutation at a
time, runs pytest, and records whether the suite catches the mutation.
"""
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC_LIB = os.path.join(PA, "lib")
SRC_TESTS = os.path.join(PA, "tests")
MUT = os.path.join(HERE, "mut")

MUTATIONS = [
    # id, file, count, old, new, tests (list of test files; [] = full suite)
    ("dst_shift_one_hour", "pa_clock.py", 1,
     "summer = (naive >= mar_last + pd.Timedelta(hours=1)) & (\n            naive < oct_last + pd.Timedelta(hours=1)\n        )",
     "summer = (naive >= mar_last + pd.Timedelta(hours=2)) & (\n            naive < oct_last + pd.Timedelta(hours=1)\n        )",
     ["test_clock.py"]),
    ("sl_first_disabled", "pa_fill.py", 1,
     "            if d > 0:\n                if ml[i] <= SL:\n                    exit_i, exit_px, reason = i, SL, \"SL\"\n                    break\n                if mh[i] >= TP:",
     "            if d > 0:\n                if mh[i] >= TP:\n                    exit_i, exit_px, reason = i, TP, \"TP\"\n                    break\n                if ml[i] <= SL:",
     ["test_fill.py"]),
    ("pf_inf_not_none", "pa_metrics.py", 1,
     "    pf = (gross_profit / gross_loss) if gross_loss > 0 else None",
     "    pf = (gross_profit / gross_loss) if gross_loss > 0 else float(\"inf\")",
     ["test_metrics.py"]),
    ("ledger_chain_genesis", "pa_ledger.py", 1,
     "        prev_hash = _sha256_hex(lines[-1]) if lines else GENESIS",
     "        prev_hash = GENESIS",
     ["test_ledger.py"]),
    ("sealed_guard_off", "pa_sealed.py", 1,
     "    s = _norm_split(split)\n    if s == \"DESIGN\":",
     "    s = _norm_split(split)\n    if True:",
     ["test_sealed.py"]),
    ("no_bypass_off", "pa_metrics.py", 1,
     "    if token is None:\n        raise EvalTokenError(",
     "    if False:\n        raise EvalTokenError(",
     ["test_no_bypass.py"]),
    ("append_removed", "pa_eval.py", 1,
     "        trial_ids.append(pa_ledger.append({\n            \"round\": rnd, \"family\": fam, \"spec_sha256\": spec_sha,\n            \"params\": {\"fill_spec\": pa_fill.resolve_spec(spec),",
     "        trial_ids.append(\"T-SKIPPED\") if False else None\n        if False: pa_ledger.append({\n            \"round\": rnd, \"family\": fam, \"spec_sha256\": spec_sha,\n            \"params\": {\"fill_spec\": pa_fill.resolve_spec(spec),",
     ["test_eval_ledger.py"]),
    ("random_side_mix_050", "pa_random.py", 1,
     "    p_long = float((side > 0).mean())",
     "    p_long = 0.5",
     ["test_random_parity.py"]),
    # expected-uncaught candidates -> full suite
    ("resample_completeness_off", "pa_data.py", 1,
     "    n_src = int(min_src) if min_src is not None else sec // 60",
     "    n_src = int(min_src) if min_src is not None else 1",
     []),
    ("warmup_flag_min", "pa_data.py", 1,
     "        \"c\": g[\"c\"].last(), \"n\": g[\"c\"].count(), \"warmup\": g[\"warmup\"].max(),",
     "        \"c\": g[\"c\"].last(), \"n\": g[\"c\"].count(), \"warmup\": g[\"warmup\"].min(),",
     []),
    ("design_split_extended", "pa_sealed.py", 1,
     "    \"DESIGN\": (\"2016-01-01\", \"2022-01-01\"),",
     "    \"DESIGN\": (\"2016-01-01\", \"2022-07-01\"),",
     []),
    ("fill_warmup_guard_off", "pa_fill.py", 1,
     "        if sig < first_live:\n            raise ValueError(",
     "        if False:\n            raise ValueError(",
     []),
]


def fresh_copy():
    if os.path.isdir(MUT):
        shutil.rmtree(MUT)
    shutil.copytree(SRC_LIB, os.path.join(MUT, "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(SRC_TESTS, os.path.join(MUT, "tests"),
                    ignore=shutil.ignore_patterns("__pycache__"))


def run_pytest(tests, label):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    cmd += [os.path.join("tests", t) for t in tests] if tests else ["tests"]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=MUT, capture_output=True, text=True, timeout=1200)
    out = (p.stdout or "") + (p.stderr or "")
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-3:]
    return p.returncode, " | ".join(tail), round(time.time() - t0, 1)


def main():
    print("== baseline: unmutated copy, full suite ==", flush=True)
    fresh_copy()
    rc, tail, secs = run_pytest([], "baseline")
    print(f"baseline rc={rc} ({secs}s): {tail}", flush=True)
    results = []
    for mid, fname, count, old, new, tests in MUTATIONS:
        fresh_copy()
        path = os.path.join(MUT, "lib", fname)
        text = open(path, encoding="utf-8").read()
        n = text.count(old)
        if n != count:
            results.append((mid, "NOT-APPLIED", f"found {n} occurrences, expected {count}"))
            print(f"[{mid}] NOT-APPLIED (found {n})", flush=True)
            continue
        open(path, "w", encoding="utf-8").write(text.replace(old, new))
        rc, tail, secs = run_pytest(tests, mid)
        caught = rc != 0
        results.append((mid, "CAUGHT" if caught else "UNCAUGHT", tail))
        print(f"[{mid}] {'CAUGHT' if caught else 'UNCAUGHT'} rc={rc} ({secs}s): {tail}",
              flush=True)
    print("== summary ==")
    for mid, status, info in results:
        print(f"{status:11s} {mid}")


if __name__ == "__main__":
    main()
