## SUMMARY

VERDICT: **FAIL.** The R02-C re-hardening renamed the attack surface; it did not
remove it. Of the 7 historical bypasses, **0 are dead**: 3 are acknowledged
residuals (still bypass), and the **4 claimed "CLOSED" (#2/#3/#4/#7) all still
bypass** — every target moved one hop deeper into a closure, and Python closure
cells are readable *and writable* (`cell.cell_contents =`). Found **9 new or
re-opened holes** (N1–N9 below), two of them with no introspection at all.

- The checker's `state` + `_EvalToken` class are still diggable:
  `compute.__closure__ → _require_token → __closure__ → checker["fn"] →
  __closure__` — the exact R1 #4 dig, two hops deeper.
- `checker["fn"]` is still rewritable via its closure cell (R1 #5 lives).
- `cell.cell_contents = lambda t: None` on `_require_token` disarms all three
  aggregators at once (R1 #6 lives, new mechanism).
- `_evaluate_body(..., token=...)` is still reachable via
  `evaluate.__closure__` — full evaluation, **zero ledger lines** (R1 #7/#9
  lives).
- NEW: `sys._getframe` walk from a caller-supplied `entries_fn`/`data_provider`
  steals the live token and spends it mid-session — no closure digging.
- NEW: `sys.modules["pa_ledger"]` pre-seeded before `import pa_eval` makes
  `evaluate` return metrics and append to a fake module — real ledger +0 lines.
- The `.tail` fixes work: missing sidecar on non-empty ledger → `(False,last)`,
  never recreated. L4/L5 laundering is dead; L3/L8 still pass `verify()` alone
  but are caught by `check_anchor` — **if** an anchor the attacker can't
  rewrite exists.
- ANCHOR verdict: mechanism is real but (a) it protects only the covered
  prefix — rewriting/injecting lines AFTER `n_lines` is invisible to it
  (A2/A3 demonstrated); (b) it is only as strong as the artifact holding it —
  a writable FREEZE.json is re-anchored trivially (A1, plus `n_lines=0`
  forgery passes A4); (c) **it is currently deployed nowhere**: the real
  `rounds/R01/FREEZE.json` contains NO `ledger_anchor` and no round report
  except `REFEREE_HARDENING.md` itself carries the anchor line. Today's
  27-line history has zero ex-post detection coverage.
- `data_sha256` does NOT commit to the inputs it claims: `pip`, `starts`,
  `m5`, `m5_t`, `next_end`, `sess_mask`, `first_live_idx`, `c_rt_pips` are all
  unhashed yet decide outcomes — a swapped input table produces an identical
  commitment (D1–D3); a provider can also just assert any `data_sha256`
  verbatim (D5).
- Honest path intact: `evaluate()` on DESIGN appends exactly one line,
  `verify() (True, None)`, `data_sha256` recorded.
- Real `ledger/TRIALS.jsonl` sha256 `4f1d3af8…` + `.tail` `c272f270…`
  byte-identical before/after — verified. All attacks ran on the
  `_scratch/redteam2/` copy; one python process at a time, OMP_NUM_THREADS=4,
  BelowNormal, DESIGN split only.

Single most important residual limit: **the anchor is the only real integrity
mechanism, and right now nothing carries it** — R01's FREEZE.json was never
re-frozen, so a full rewrite of all 27 existing lines today leaves no artifact
in this repo that would disagree.

---

# R02 REVIEW_REFEREE_FIXES_2 — red-team round two on R02-C/D

Scope: `lib/pa_eval.py`, `lib/pa_metrics.py`, `lib/pa_ledger.py`,
`research/physics/phys_freeze.py`, `research/physics/phys_analysis.py`, as
re-hardened per `rounds/R02/REFEREE_HARDENING.md`. Attacks ran from
`_scratch/redteam2/` against a copy of the ledger (27 lines + 2 scratch
appends from the honest-path checks). Exact scripts: `rt2_gate.py`,
`rt2_fresh.py`, `rt2_sysmod.py`, `rt2_anchor.py` in that directory.

## 1. The 7 historical bypasses — re-run

Hardening numbering (pa_metrics docstring 1–7). Every "CLOSED" claim was
re-tested with the same dig aimed at wherever the target moved.

| # | hardening claim | re-run (exact code) | result |
|---|---|---|---|
| 1 | ACCEPTED residual | `open_session = next(c.cell_contents for c in pa_eval.evaluate.__closure__ if getattr(c.cell_contents,'__name__','')=='open_session')`; `tok,_ = open_session("DESIGN","x")`; `pa_metrics.compute([{...FILLED...}], tok)` | **BYPASS** — `N=1`. Confirmed residual. |
| 2 | CLOSED (`_token_check` gone) | `req = next(c.cell_contents for c in pa_metrics.compute.__closure__ if c.cell_contents.__name__=='_require_token')`; `chk = next(c for c in req.__closure__ if 'fn' in c.cell_contents)`; `fn=chk.cell_contents['fn']`; dig `fn.__closure__` → `state`, `_EvalToken`; `state['nonce']='x'; state['split']='DESIGN'; compute([], _EvalToken('DESIGN','f','x'))` | **BYPASS** — `N=0` (accepted). The class+state dig survives verbatim, two hops deeper. Claim is false. |
| 3 | CLOSED (no module cell) | same `chk` cell: `chk.cell_contents['fn'] = lambda o: True`; `pa_metrics.compute([], object())` | **BYPASS** — `N=0`. The cell moved from `__globals__` to `__closure__`; still mutable. Claim is false. |
| 4 | CLOSED (no module name) | `req_cell.cell_contents = lambda t: None`; `pa_metrics.compute([{...}], object())` | **BYPASS** — `N=1`. `cell.cell_contents` is writable (Py≥3.8); one write disarms `compute`, `_metrics_of`, `_agg`. Claim is false. |
| 5 | ACCEPTED residual | `importlib.reload(pa_metrics)`; `pa_metrics._register_token_checker(lambda o: True)`; `compute([], object())` | **BYPASS** — `N=0`. Confirmed residual. |
| 6 | ACCEPTED residual | fresh process: `import pa_metrics` (no pa_eval); `_register_token_checker(lambda o: True)`; `compute([{...}], object())` | **BYPASS** — `N=1`. Late `import pa_eval` fails closed with RuntimeError, but the permissive checker is already installed. Confirmed residual. |
| 7 | CLOSED (body in closure) | `body = next(c.cell_contents for c in pa_eval.evaluate.__closure__ if getattr(c.cell_contents,'__name__','')=='_evaluate_body')`; `tok,_ = open_session(...)`; `body(spec,'DESIGN',['SYNX'],'M5',['gross'],'sha','RT2','FAM',provider,'cand',1,20,False,30,None,0.005,tok)` | **BYPASS** — full metrics returned (`N=1`), **ledger delta 0**. The eval-without-append primitive is intact; it moved, it was not removed. Claim is false. |

Score: **0 of 7 dead.** The R02-C diff deleted module-level *names*; every
object those names pointed at still exists and is still reachable — and
`__closure__` cells are not just readable, their contents are assignable.

Still dead (confirmed again): the three raising decoys
(`_mint_token`/`_enter_eval`/`_leave_eval` → `EvalTokenError`), public-name
registration (`pa_metrics.register_token_checker` absent; second
`_register_token_checker` → RuntimeError), duck-typed/`__eq__` forgery
(`type(obj) is _EvalToken`), direct calls to `compute`/`_metrics_of`/`_agg`
without a valid token, `reload(pa_eval)` (fails closed, half-rebound).

## 2. New attacks

| # | attack (exact code run) | result | severity |
|---|---|---|---|
| N1 | the two-hop checker dig in row #2 above | re-opens claimed-CLOSED #2 | HIGH |
| N2 | `chk.cell_contents['fn'] = λ` via `compute.__closure__ → _require_token → __closure__` | re-opens claimed-CLOSED #3 | HIGH |
| N3 | `cell.cell_contents = lambda t: None` on the `_require_token` cell | re-opens claimed-CLOSED #4; disarms all 3 aggregators in one write | HIGH |
| N4 | `_evaluate_body` out of `evaluate.__closure__` + minted token | re-opens claimed-CLOSED #7; eval without append | CRITICAL (unchanged) |
| N5 | inside caller-supplied `entries_fn`: `f = sys._getframe()`; walk `f_back` until `"token" in f.f_locals`; `pa_metrics.compute([...], tok)` **while the session is live** | **BYPASS** — `N=1` stolen mid-eval; ledger +1 describes only `evaluate`'s own result. No closure digging, no monkeypatching — any callback the harness invokes (`entries_fn`, `data_provider`) sees the token in plain `f_locals` | HIGH, new mechanism |
| N6 | fresh process: `sys.modules['pa_ledger'] = fake_module` (with `append`, `verify`, `code_sha256`, `anchor`, `set_ledger_path`, `ledger_path` stubs) **before** `import pa_eval`; run `evaluate(...)` | **BYPASS** — `evaluate` returned `N=1`, `trial_ids=['T-FAKE']`, fake got the append, real ledger +0. `import pa_ledger` inside `pa_eval`/`pa_sealed` resolves the pre-seeded module | HIGH, new mechanism |
| N7 | `pa_eval.pa_ledger.append = lambda *a,**k: 'T-FAKE'` (R1 #11 re-run) | **BYPASS** — unchanged; `evaluate` returned metrics, ledger delta 0 | HIGH (not claimed fixed) |
| N8 | `data_sha256` coverage: `d2 = dict(d); d2['pip']=9.9` / `d2['starts']+=7` / `d2['m5']*2` / `d2['next_end']=...` / `sess_mask` inverted / `first_live_idx`, `c_rt_pips` changed → `_provider_data_sha256(d2) == _provider_data_sha256(d)` | **HOLE** — `hash_equal=True` for all of the above. `pip` (R conversion), `starts`/`m5`/`m5_t`/`next_end`/`sess_mask`/`first_live_idx` (fill & exit geometry) and `c_rt_pips` (costs) all feed the computation but none are hashed. A swapped input table keeps the same commitment. Control: `bars['c']+0.5` → hash differs | HIGH — the line does not commit to what it claims |
| N9 | `d['data_sha256'] = 'f'*64` provider-side | accepted verbatim (`d.get('data_sha256') or _provider_data_sha256(d)`) — the commitment field is caller-asserted whenever the provider chooses | MEDIUM (documented as feature; still means lines can carry arbitrary "commitments") |

## 3. Anchor attack (copies only)

Setup: copied real ledger (27 lines) → scratch; two honest evals → 29 lines;
`a = pa_ledger.anchor()` (`n_lines=29`, `sha256 2f67b12d…`) as FREEZE.json
would store it.

| attack | verify() | check_anchor(stored a) | verdict |
|---|---|---|---|
| L4 rerun: rewrite last line, **delete** `.tail` | `(False, 28)`, sidecar NOT recreated | — | **DEAD** — the laundering vector is genuinely closed |
| L5 rerun: truncate 3, delete `.tail` | `(False, 25)` | — | **DEAD** |
| L3: rewrite last line + rewrite `.tail` | `(True, None)` | `(False, mismatch)` | verify bypassed as before; **anchor catches it** — provided a surviving anchor exists |
| L8: rewrite line 5 + rechain + `.tail` | `(True, None)` | `(False, mismatch)` | same |
| **A1**: rewrite history, rechain, `.tail`, then `anchor()` again and write THAT into a FREEZE.json copy | `(True, None)` | `check_anchor(forged)` = `(True, None)` | **BYPASS when the artifact is writable** — the anchor detects only against a copy the attacker cannot touch |
| **A2**: append a fully-fabricated trial (`PF 9.99, WR 0.99`) with correct `prev_line_sha256` + `.tail` | `(True, None)` | `(True, None)` | **invisible** — anchor covers a prefix; appended fabrication is outside it |
| **A3**: append 3 lines, then rewrite post-anchor line 30 + rechain + `.tail` | `(True, None)` | `(True, None)` | **invisible** — post-anchor history can be rewritten wholesale; nothing protects lines beyond `n_lines` |
| **A4**: `check_anchor({"n_lines":0,"sha256":sha256(b""),"utc":"x"})` | — | `(True, None)` | a degenerate forged anchor always passes (only matters because FREEZE.json is writable) |
| L9 rerun: missing ledger file | `(True, None)` | `check_anchor` → `(False, "holds 0 lines")` | verify still blesses absence; anchor is the only backstop — see below |

**What the anchor genuinely buys:** for lines `0..n_lines-1` it converts "silent
recomputable checksum" into "detectable against an earlier-anchored copy" —
that is the whole gain, and it is real.

**What a party with write access can still change without any verifier
noticing:** (a) every line after `n_lines` — rewrite or fabricate, rechain,
rewrite `.tail` (A2/A3); (b) everything, if the artifacts holding the anchor
live in the same writable tree (A1/A4); (c) `data_sha256`-covered "inputs" that
aren't actually hashed (N8/N9). And crucially: **the only FREEZE.json in the
repo (`rounds/R01/FREEZE.json`) contains no `ledger_anchor` key at all** — the
hardening wired `phys_freeze.py:63` but never re-froze (admitted in the
report), and `grep` shows the only "Ledger anchor" line in any artifact is
inside `REFEREE_HARDENING.md` itself. The mechanism that is supposed to detect
history rewrite currently protects nothing that already exists.

## 4. data_sha256 commitment check

`_provider_data_sha256` hashes meta (`symbol|split|tf|utc_start|utc_end`) plus
`t,o,h,l,c,utc_min,srv_min,dow,warmup` under groups `m1` and `bars` only.
Verified by direct calls on the copy:

- swapped `pip`, `starts`, `m5`, `m5_t`, `next_end`, `sess_mask`,
  `first_live_idx`, `c_rt_pips` → **identical hash** (D1–D3). These fields
  decide fills, exits and costs — i.e. outcomes — so the commitment does not
  bind the computation to its real inputs.
- swapped `bars.c` → different hash (positive control works).
- provider-supplied `data_sha256` → accepted verbatim, never recomputed (D5).

`spec_sha256` still hashes callables by `__qualname__` only (acknowledged as
deliberately weak; with `data_sha256` incomplete, the line's effective input
commitment is weaker than advertised).

## 5. Honest path

`pa_eval.evaluate(spec, "DESIGN", ["SYNX"], "M5", ["gross"], …)` on the scratch
ledger: **+1 line** (`T000029`), `verify() (True, None)`,
`data_sha256`/`data_sha256_by_symbol` populated and consistent with
`_provider_data_sha256(d)`. Random path exercised in earlier tests. Normal use
is unbroken.

## 6. Environment integrity

- `ledger/TRIALS.jsonl` sha256 `4f1d3af88f2f833fc6f2cc49b1c6bd479d208abcd1ad1aa03fbd099d383a8776`
  and `.tail` `c272f27048f958ced216173d05f76c9b125f8cd3394b78202c3935ed5f8d4391`
  — **byte-identical before and after** (re-hashed at end).
- No file under `lib/`, `struct/`, `research/`, `rounds/` modified except this
  report; ledger attacks ran on `_scratch/redteam2/ledger/TRIALS.jsonl` only.
- One python process at a time, `OMP_NUM_THREADS=4`, BelowNormal (`start
  /belownormal`), DESIGN split, synthetic provider. No git state changes,
  nothing deleted.

## 7. What would actually close the remaining holes (ranked)

1. **Deploy the anchor, then protect it out-of-tree.** Re-run the freeze
   writer (or write `ledger_anchor` into the existing FREEZE.json /
   ROUND_REPORT.md as an addendum), and record `sha256(FREEZE.json)` in the
   ledger/report itself so the anchor's carrier is also pinned. Until the
   anchor exists in an artifact an attacker can't rewrite — archived outside
   `ledger/`+`rounds/` — it detects nothing.
2. **Anchor must cover the tail too, or re-anchor at every freeze.** Lines
   appended after the last anchor have only recomputable-checksum protection;
   either re-anchor each round (covering the new prefix) or record per-append
   anchors in the round's results artifact.
3. **Hash everything that decides outcomes** in `_provider_data_sha256`:
   `pip`, `starts`, `m5`, `m5_t`, `next_end`, `sess_mask`, `first_live_idx`,
   `c_rt_pips`, `utc_start`/`utc_end` (already in meta). Otherwise "commits to
   the data it claims" is not true.
4. Accept — in writing, once — that the gate is decorative against intent:
   every claimed-CLOSED bypass was reopened with the same technique the doc
   calls "unfixable." The honest contract is anchor + independent
   re-execution; the gate only needs to stay honest-worker-proof, which it is.
5. If N5/N6 matter for adversarial `entries_fn`/provider code: don't run
   caller callbacks inside the token scope, or run them in a subprocess —
   `f_locals` and `sys.modules` are unsecurable in-process.
