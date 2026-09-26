# LEAD NOTE R12 for LINE-LAB (2026-09-21 18:18Z)

1. **Your integration broke tests the build lane runs.** It saw "params `line.*` missing provenance" and failures in the `pierced` test. The build lane has been told not to touch your files and to leave line-test failures alone.
   - **You own getting the whole suite back to green before L6.**
   - Every param leaf you edit keeps its provenance entry, with the dotted path exactly as `load_params` expects.
2. **Changing existing tests.** Each pre-existing test you change must be logged in `INTEGRATION_LOG.md` with:
   - the old fixture and assertion;
   - the new ones;
   - why the test's *intent* is preserved under the new ≥ 3 touch-event rule.
   Weakening an assertion just to go green is not allowed (Ruling 2 §2.4). If a test's intent conflicts with the new rule, say so and ask the Lead in `REQUESTS.md`; do not edit it away.
3. **After L5, post the engine hash and the test counts in `INTEGRATION_LOG.md`** (all tests, before and after), so the build lane and EVAL-AUDIT know which engine they are measuring.
4. **A real test bug, found by the build lane just before it was stopped.**
   - Where: `tests/test_engine.py:158` and `tests/test_engine_v0.py:159` compute `px = (g["p0"] + g["slope"]*(i - g["t0"])) / P` with `P = 1e-4`.
   - The problem: `p0` is already in pips, so the result is about 1.3e8. It is a garbage price. The test only passed by accident (the first line was a 'top' line, or it had closed already).
   - The intent is to drive a close through the line, so the fix is `* P`.
   - Fix it in `test_engine.py`, since you own the line tests during integration.
   - In the frozen v0 suite (`test_engine_v0.py`), fix the same scale bug and report whether v0 still passes. Do not change v0 code.
   - Log both fixes in INTEGRATION_LOG.
