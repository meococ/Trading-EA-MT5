"""_suite_keeps.py — R42 §42.3: run the UNMODIFIED suite on each keep
configuration (K1..K4), independently of the build lane's "72/72".

The seven theory fixtures on disk currently call ``gen_engine()``
(which forces fam_budget/fam_caps OFF).  The unmodified fixtures used
the default engine.  This runner restores that semantics WITHOUT
editing the test file:

  * ``engine.load_params`` is patched to return the keep's params
    (extracted verbatim from the keep's ON-arm cached pickle e.p), so
    every ``E.PerceptionEngine()`` in the suite runs the keep config;
  * ``test_engine.gen_engine`` is replaced by a plain default-engine
    factory — identical to the original fixture bodies under the keep.

One subprocess per config (params are process-global).  Prints a
pytest summary plus one line per failure (nodeid + first error line).

Usage:
  python evalcheck/_suite_keeps.py K1        # one config
  python evalcheck/_suite_keeps.py ALL       # K1..K4 + disk defaults
"""
import copy
import os
import pickle
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

# keep -> (ON-arm variant, A/B hash) — params come from the pickle
CONFIGS = {
    "K1": ("labscore_on", "afba83c5f74d96c4"),
    "K2": ("deforig_on", "e62f2dc9ee7fa6e2"),
    "K3": ("bxcombo_on", "dd96c5fe49c28d74"),
    "K4": ("bxsup_on", "cfb862d40c805a25"),
    "K5": ("lnfloor_on", "75a9650ca6ae7f79"),
    "BXP": ("bxprio_on", "cd00d0bede994c8e"),
    "FAMOFF": ("famoff_on", "e1edc511918a0410"),
    "FAMCTX": ("famctx_on", "88438120dc55043f"),
    "FAMCTX2": ("famctx_nocr_on", "4dcc44d73e081c02"),
    "K6": ("cong_on", "df79ade35a496978"),
    # C-round 2 keeps (PLAYBOOK_C2)
    "K7": ("bmoff_on", "66f596dc8234b436"),
    "K8": ("pedg_on", "81f7503f346dab9f"),
    "K9": ("ltfcap_on", "759d9036b20969a8"),
    "EVB": ("evb_on", "be204b980694216e"),
    "EVB2": ("evb2_on", "b07b8af4837476fb"),
    "UIP": ("uip_on", "6d9557837a66f462"),
    "UIP2": ("uip2_on", "6d9557837a66f462"),
    "LVF": ("uip2_lvfree", "23504c937e36e622"),
    "LVFPB": ("uip2_lvfree_pb", "23504c937e36e622"),
    "EVB2350": ("evb_off", "23504c937e36e622"),
    "PBBIRTH": ("uip2_pbbirth", "8361fe85e73f9437"),
    # R73 L-1 arms @8b330117
    "L1V1": ("l1_close", "8b33011772e43474"),
    "L1V2": ("l1_soft", "8b33011772e43474"),
    # R73 L-2 @2e8a7007 / L-3,L-4 @66c6ea8a
    "L2V1": ("l2_near", "2e8a70072cc9aa2a"),
    "L2V2": ("l2_near_ret24", "2e8a70072cc9aa2a"),
    "L3V1": ("l3_ink", "66c6ea8a87befdc1"),
    "L3V2": ("l3_revise", "66c6ea8a87befdc1"),
    "L4V1": ("l4_snap", "66c6ea8a87befdc1"),
    "L4S2": ("l4_snap", "15682ea374404104"),
    "L4V2": ("l4_promsnap", "15682ea374404104"),
}

_CHILD = r"""
import copy, pickle, sys, os
sys.path.insert(0, r"%s")            # perception root
sys.path.insert(0, r"%s")            # evalcheck
_pd = os.environ.get("PERF_DIR")
if _pd:
    sys.path.insert(0, _pd)          # patched engine/swings win imports
import engine as E

pkf, label = sys.argv[1], sys.argv[2]
params = pickle.load(open(pkf, "rb")).p       # the keep's exact params

_orig_load = E.load_params
def _arm_load(path=None):
    return copy.deepcopy(params)
E.load_params = _arm_load

class _Restore:
    # after collection, point gen_engine at the default engine so the
    # seven fixtures run the keep config (their pre-06:15Z bodies)
    def pytest_collection_modifyitems(self, session, config, items):
        te = sys.modules.get("test_engine")
        if te is not None:
            te.gen_engine = lambda: E.PerceptionEngine(
                params=copy.deepcopy(params))

import pytest
rc = pytest.main(["-q", "--tb=short", "tests/"], plugins=[_Restore()])
sys.exit(rc)
""" % (PERC, HERE)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    import common as C
    import cache as CA
    recs = C.load_tune()
    rec = recs[0]
    w1 = rec["window"]["x1"] or 1439

    todo = list(CONFIGS) if which == "ALL" else [which]
    if which == "ALL":
        todo = ["DISK"] + todo
    for key in todo:
        if key in ("DISK", "DISKTT"):
            # current on-disk params_v1_1.json, no patch beyond the
            # gen_engine restore -> the suite as the Lead wants it on
            # the kept defaults.  Post-A3 engines can't be pickled
            # (FamilyPipe.__getattr__ recursion) - store e.p only.
            import engine as E
            import types
            pkf = os.path.join(HERE, "_suite_disk_params.pkl")
            e = types.SimpleNamespace(p=E.PerceptionEngine().p)
            if key == "DISKTT":
                e = types.SimpleNamespace(
                    p=dict(E.PerceptionEngine().p, trade_tags=1))
            pickle.dump(e, open(pkf, "wb"))
            label = "DISK(params_v1_1.json as-is)" if key == "DISK" \
                else "DISKTT(trade_tags=1)"
        else:
            var, h = CONFIGS[key]
            f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                             % (var, h, rec["date"], w1))
            pkf = f
            label = "%s (%s@%s)" % (key, var, h[:8])
        print("\n" + "=" * 70)
        print("SUITE on %s" % label)
        print("=" * 70)
        r = subprocess.run(
            [sys.executable, "-c", _CHILD, pkf, key],
            cwd=PERC, capture_output=True, text=True, timeout=1200)
        out = (r.stdout or "") + (r.stderr or "")
        # summary lines + failures
        for line in out.splitlines():
            if line.startswith(("FAILED", "ERROR")) or \
               "passed" in line or "failed" in line or \
               line.startswith("==="):
                print(line)
        print("(exit %d)" % r.returncode)


if __name__ == "__main__":
    main()
