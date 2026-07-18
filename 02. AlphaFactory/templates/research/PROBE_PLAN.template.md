# PROBE PLAN — HYP-REPLACE-ME (frozen before any outcome read)

Status: FROZEN <date>, before any PnL/outcome of THIS object was computed.
SHA256 bound into the registry `idea|probe` row BEFORE the probe runs. A bound
plan is immutable; any pre-outcome amendment becomes `_V2.md` bound at the
next transition (never edit in place — the registry validator re-hashes ALL
historical rows). Post-outcome change = new hypothesis_id.

## 1. Identity
- hypothesis_id / ea_name (research-only; state whether any `.mq5` is authorized)
- Symbol / TF / thesis + primary-source citation
- Object under test (exact; unconditional vs conditional); Owner scope approval if any

## 2. De-dup (explicit)
- `do_not_repeat_failures.md` families + graveyard S-log IDs checked
- Per adjacent killed family: one line on why this object is materially distinct
- Design-only screens (no evidence) touching this class: cite + state override basis
- Adverse priors stated pre-outcome

## 3. Data (hash-bound)
- Bars source/broker, read-only mode, parquet/CSV path + SHA (or PULL_AUDIT ref)
- Server→UTC model (`tools/research/fivepercent_server_clock.py`) + verification
- Known-unusable columns (e.g. zero-filled historical spread)
- Splits: Train / Validation / Holdout (SEALED — 0 bars loaded, enforced at read)

## 4. Frozen decision surface (ONE config; tuning budget = 0 unless a declared grid)
- Every input/override; entry/exit/invalidation; closed-bar shift>=1; fill bar
- Cost model: x1 value + `UNVERIFIED_PROXY` status; stress ×1.5/×2 (missing = UNVERIFIED, never 0)

## 5. Trial accounting & deflation (frozen)
- Enumerate the full trial universe; N = EVERY executed simulation (cost tiers
  are NOT separate trials; controls ARE counted); pooled-primary vs split-diagnostic
- DSR (`tools/research/dsr.py`): per-trade SR, PSR(skew, non-excess kurt),
  V[SR] across all arms, floor 0.95

## 6. Kill gates (ALL required for SURVIVE) — table: # / gate / threshold
- Expectancy floor stated as the WEEKLY bar scaled to this object's cadence class
- KILL vs PARK criteria pre-listed ("almost passed" = KILL)

## 7. Exclusions (hard)
- No post-hoc hour/day/year/session veto; no TF/symbol/geometry drift; list
  family-specific forbidden regions

## 8. Artifacts
- Hash-bound probe JSON (`promotion_eligible=false`), trade ledger CSV,
  `trials/trial_log.jsonl` rows (hypothesis_id + prereg_sha256 on every row),
  readout, single registry transition, hot.md/do_not_repeat updates at verdict

## 9. (Exhaustive-grid variant only)
- Authority = Owner scope, closure-not-rescue; necessary-condition routing
  (net<=gross same-arm only — a different trade set is NOT bounded by it);
- Stage-2 conditional rule frozen; default verdict KILL_FAMILY_EXHAUSTIVE;
  adversarial critic review before freeze; label coverage honestly (simulated
  vs routed-away axes)
