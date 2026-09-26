VERDICT: FAIL

# R02 REVIEW_REFEREE_FIXES — red-team on the R02-A token gate + ledger tail

Scope: `lib/pa_eval.py`, `lib/pa_metrics.py`, `lib/pa_ledger.py` as described in
`rounds/R02/REFEREE_FIXES.md` (F2 token-gate rewrite, F9 `.tail` sidecar). All
attacks were run from `scratch_redteam/` against a **copy** of the ledger; the
real `ledger/TRIALS.jsonl` (sha256 `4f1d3af8…`) and `.tail` (`c272f270…`) are
byte-identical before and after — verified. No lib/struct/research/rounds file
was modified except this report. One python process at a time, DESIGN split,
synthetic market only.

Summary: the two **named** historical bypasses are dead, and the honest path is
intact. But the gate is bypassed in **seven independent ways**, most requiring a
single line of ordinary Python introspection — and the new sidecar has a worse
failure mode than the bug it fixed: deleting it makes `verify()` *bless* a
tampered last line.

## Attack table

| # | attack (exact code run) | result | severity |
|---|---|---|---|
| 1 | `pa_eval._enter_eval()` / `_mint_token("DESIGN")` / `_leave_eval()` | `EvalTokenError` each — **dead** | — |
| 2 | `pa_metrics.register_token_checker` / `._register_token_checker(λ)` | attr gone / `RuntimeError` on 2nd registration — **dead as designed** | — |
| 3 | `open_session = [c.cell_contents for c in pa_eval.evaluate.__closure__ if getattr(c.cell_contents,'__name__','')=='open_session'][0]`; `tok,consume = open_session("DESIGN","x")`; `pa_metrics.compute(trades, tok)` | **BYPASS** — `compute` returned `N=1`, zero ledger lines. `evaluate.__code__.co_freevars == ('open_session',)`: the mint moved into the closure but is still reachable through it | **CRITICAL** |
| 4 | dig `state` dict + `_EvalToken` out of `pa_eval._token_check.__closure__` (free vars `('_EvalToken','state')`, and `_token_check` is a module attribute); `state["nonce"]="x"; state["split"]="DESIGN"; pa_metrics.compute([], _EvalToken("DESIGN","x","x"))` | **BYPASS** — forged token accepted, no ledger line | **CRITICAL** |
| 5 | `pa_metrics._TOKEN_CHECKER["fn"] = lambda o: True`; `pa_metrics.compute([], object())` | **BYPASS** — historical bypass (b) verbatim; the one-shot handshake guards the *function*, not the mutable module-level cell it writes to | **HIGH** |
| 6 | `pa_metrics._require_token = lambda t: None`; `pa_metrics.compute(trades, None)` | **BYPASS** — removes the gate from `compute`, `_metrics_of` and `_agg` at once | **HIGH** |
| 7 | `importlib.reload(pa_metrics)`; `pa_metrics._register_token_checker(lambda o: True)`; `pa_metrics.compute([], object())` | **BYPASS** — reload resets the "one-shot" handshake to `{"fn": None}` | **HIGH** |
| 8 | fresh process: `import pa_metrics` (no pa_eval); `_register_token_checker(lambda o: True)`; `compute([], object())` | **BYPASS** — first-come-first-served handshake; whoever registers first wins. `import pa_eval` afterwards raises `RuntimeError`, but the permissive checker is already installed | **HIGH** |
| 9 | `pa_eval._evaluate_body(spec, split, syms, tf, tiers, sha, rnd, fam, provider, cand, seed, K, rnd_en, wu, notes, rpt, token=<forged>)` | **BYPASS primitive** — the entire eval body is a module-level function taking a raw `token` param; combined with #3/#4/#5/#6 it yields a full evaluation with **no append at all** | **CRITICAL** |
| 10 | in-session theft: `entries_fn` (arbitrary caller code running *inside* `evaluate` while the nonce is live) reads `state` via `_token_check.__closure__`, mints `_EvalToken`, calls `pa_metrics.compute` on its own trades | **BYPASS** — thief got `N=1` metrics; ledger got +1 line describing only `evaluate`'s own result, not the stolen computation | **HIGH** |
| 11 | `pa_eval.pa_ledger.append = lambda *a, **k: "T-FAKE"` then `pa_eval.evaluate(...)` | **BYPASS** — `evaluate` returned metrics normally; ledger got **+0 lines**. The "always appends" guarantee is itself one monkeypatch deep | **HIGH** |
| 12 | duck-typed forgery: class with `__eq__→True`, spoofed `__class__`/slots fields | `EvalTokenError` — `type(obj) is _EvalToken` is strict; unreachable class kills spoofing — **dead** | — |
| 13 | `pickle.dumps(tok)` inside session | `AttributeError`: closure-local class is unpicklable — **dead** | — |
| 14 | `copy.copy(tok)` (works on local classes), `consume()`, then `compute([], copy)` | `EvalTokenError` — `state["nonce"] is None` check defeats replay — **dead**; the `finally`-clear genuinely works | — |
| 15 | `importlib.reload(pa_eval)` | `RuntimeError` mid-exec (re-registration refused) — **fail-closed**, though the module is left half-rebound | — |
| 16 | two threads → `pa_eval.evaluate(...)` concurrently | one thread: `EvalTokenError` + ERROR ledger line; other: OK — shared `state` dict means concurrent sessions clobber each other. Fail-**closed** (DoS, not bypass), but see #10: a *live* nonce is stealable concurrently | — |
| 17 | `evaluate.__wrapped__` / `func_globals` | no `__wrapped__` exists (no decorators); `__globals__` only exposes module attrs already covered | — |
| 18 | `pa_metrics.compute`/`_metrics_of`/`_agg` called directly with `None`/`object()` | `EvalTokenError` — all three aggregators re-check — **dead** (until #5/#6) | — |
| **Ledger (copies only)** | | | |
| L1 | flip field in middle line 5, keep sidecar | `(False, 6)` — **detected** by chain | — |
| L2 | rewrite last line's `n`, keep `.tail` | `(False, 26)` — **detected** by sidecar | — |
| L3 | rewrite last line + `open(p+".tail","w").write(sha256(new_last))` | `(True, None)` — **BYPASS**: sidecar is an unauthenticated sha256; recompute it and the last line is freely editable | **HIGH** |
| L4 | rewrite last line + `os.unlink(p+".tail")` | `(True, None)` **and** `verify()` regenerated `.tail` over the *tampered* line — **BYPASS + laundering**: the check actively blesses the tamper | **CRITICAL** |
| L5 | truncate newest 3 lines + delete `.tail` | `(True, None)` — **silent deletion** of the most recent trials | **HIGH** |
| L6 | truncate newest 3, keep `.tail` | `(False, 23)` — **detected** | — |
| L7 | swap lines 10/11 | `(False, 10)` — **detected** | — |
| L8 | rewrite line 5, recompute `prev_line_sha256` for lines 6..end, rewrite `.tail` | `(True, None)` — **arbitrary mid-ledger rewrite**; the chain is a recomputable checksum, not a MAC (inherent, but must be stated) | **HIGH** |
| L9 | `verify()` on missing ledger file | `(True, None)` — absence passes silently | low |
| L10 | hand-forged well-formed line (correct `prev_line_sha256`) + `.tail` | `(True, None)` — anyone can inject a fabricated "valid" trial (append is unauthenticated by design) | by design, stated |

## What I could NOT break

- The two named historical bypasses (#1, #2) — decoys raise, handshake refuses re-registration.
- Duck-typing/`__eq__`/`__class__` spoofing of the token — `type() is` + closure-local class + 16-byte `secrets` nonce is genuinely unforgeable *without* reaching into the closure.
- Token replay after `finally: consume()` — copies die with the session; single-use semantics hold.
- `reload(pa_eval)` fails closed; concurrent `evaluate()` calls fail closed (DoS, not bypass).
- Middle-line edits, line reordering, and truncation are all caught **as long as the sidecar survives and the attacker doesn't recompute the chain**.
- Honest path: `evaluate()` on DESIGN with a synthetic provider appended exactly **one** OK line, `verify()` `(True, None)` — the fix did not break normal use.

## Honest residual limits (the part that must not be assumed away)

1. **A same-interpreter attacker cannot be stopped in pure Python.** Every layer
   of this fix is reachable: `__closure__` hands out the mint, the token class and
   the live session state; `_TOKEN_CHECKER`, `_require_token` and
   `pa_ledger.append` are writable module globals; `importlib.reload` resets the
   one-shot. The fix raised the bar from "call a public function" to "one line of
   introspection" — i.e. from *accidental* to *deliberate* bypass. That is real
   value (intent becomes provable in review) but it is not enforcement.
2. **The ledger is a checksum, not evidence.** Chain + sidecar contain no secret
   and no external anchor. A motivated party with write access to `ledger/` can:
   edit the last line + rewrite `.tail` (L3); edit/truncate **anything** + delete
   `.tail` and let `verify()` launder it (L4/L5); rewrite any suffix + `.tail`
   for arbitrary mid-history edits (L8); or inject fabricated trials outright
   (L10). The only edit class detected is one that leaves the two files
   inconsistent. `verify()` on a missing file returns `(True, None)`.
3. **`verify()` mutates on read.** The bootstrap-on-missing-sidecar branch is the
   laundering vector: one `verify()` call after a delete turns a tampered file
   into a permanently blessed one.
4. **A ledger line does not commit to what was computed.** It records
   `spec_sha256` (callables hashed by `__qualname__` only — trivially colliding),
   caller-supplied `params`, and no hash of provider data. `entries_fn` /
   `data_provider` are arbitrary code whose outputs are never fingerprinted.
5. **`evaluate`'s session state is a shared mutable dict** — concurrent
   evaluations corrupt each other (fail-closed) and a live nonce is observable
   process-wide while any caller-supplied callback runs.

## Hardening, ranked by value-for-effort

1. **Anchor the ledger head into downstream artifacts** (~cheap, biggest real
   win): record `sha256(ledger)+n_lines` inside `FREEZE.json` / round reports at
   freeze time. L3/L4/L5/L8/L10 all become detectable ex-post even though the
   files are still rewritable. This is the only fix that survives a fully
   motivated attacker.
2. **Stop blessing missing sidecars**: treat `.tail` absence as `(False, last)`
   for any ledger with ≥1 line, or write a one-byte `.fmt` marker at first
   `append` meaning "sidecar mandatory". One `if`, kills the L4/L5 launder.
   Bootstrap once at migration, not on every verify.
3. **Don't store the checker at module scope**: `pa_eval` should not bind
   `_token_check`/`_decoy_mint`/`_evaluate_body` as module attributes; move
   `_evaluate_body` inside the closure (it currently takes a raw `token` param —
   a complete eval-without-append API). In `pa_metrics`, build `compute` inside a
   `_build_gate()` closure so the checker cell never sits in `__globals__`.
   Raises #3–#9 from one-liners to closure-digging (still possible — see #4).
4. **`pa_metrics` module `__setattr__` guard** (`sys.modules[__name__].__class__ = _Frozen`): refuse rebinding `_require_token`/`_TOKEN_CHECKER`/`compute`. ~15 lines; turns silent monkeypatch into an exception. Evadable via `module.__dict__` writes — loud, not absolute.
5. **Bind inputs in the ledger line**: add `data_sha256` over provider arrays and
   `inspect.getsource` hash of callables, so a line commits to what was actually
   computed (closes residual #4).
6. **Serialize `open_session`/`consume`** under a `threading.Lock` (or per-call
   nonce set) — removes the concurrent-eval DoS and shrinks the theft window.
7. Accept and document the residual: treat `result["ledger_trials"]` presence +
   `verify()` + anchored head hash as the integrity contract for consumers;
   the token gate is an accident-guard, not a security boundary.
