# CHARTER ADDENDUM 3 - compute cap, execution gate, reproduction, order of work (BINDING)

Amends `PA_PRO_CHARTER.md` section 6 (CPU-slots bullet), section 9 (heavy-python bullet) and the
physics-first ordering implied by sections 4 and 7. Issued by the Lead, 2026-09-21 ~02:45Z.

1. COMPUTE CAP 2 -> 4 (Owner-approved 2026-09-21). At most 4 of OUR heavy python processes at once,
   always through `lib/pa_slots.py` (`_N_SLOTS = 4`). `tests/test_slots.py` pins the value, so the test
   must change with it. Unchanged: 4 threads per process, BelowNormal priority. A lane holds at most 2
   slots at once unless the Lead assigns more. Raising the cap again needs the Owner.
   The change was made at 02:38Z while two R02 processes were running. Both had imported `pa_slots`
   before the edit. The R02 freeze hashes no `lib/` file, and R02 ledger rows carry no `code_sha256`,
   so R02 is unaffected. The originals are kept in `_scratch/originals_20260921/`.

2. EXECUTION GATE FOR EVERY FREEZE (new; source: R02 DEVIATION_D41). No freeze may be sealed or
   executed until one end-to-end synthetic execution of EVERY claim path has passed through the real
   runner. That run must use the same entry point, the same per-unit result writer and the same ledger
   append (redirected to a scratch ledger), on synthetic or small real inputs. Component unit tests do
   not count. The freeze records the sha256 of that run's log.
   Why: FREEZE v2 was sealed, reviewed and witnessed, and still could not run. Two latent defects sat on
   exactly the claim path: `KeyError 'w'`, and `json.dump` of an ndarray. Nothing had ever executed that
   path.

3. SEPARATION OF DUTIES AND REPRODUCTION (codifies R02 practice).
   - Builder, reviewer, executor and re-executor are four different agents or sessions.
   - Every number of a sealed round is reproduced by an independent fresh execution before any number
     reaches the Owner.
   - The comparison is automated and value-blind, and prints only MATCH or MISMATCH.
   - The executor's output hashes and the comparator are witnessed out-of-tree before the reproduction
     result exists.
   - A MISMATCH opens a deviation, and nothing is released.

4. ORDER OF WORK (Blueprint v2.0, Lead, 2026-09-21). Setup families are NOT gated on zone-vs-empty
   physics, for two reasons: with our controls the binary zone question is not identifiable (R01, R02),
   and zone "strength" is mostly recency. Setups are screened economically against matched random entry
   with identical geometry (section 8, SCREEN). Zone research continues, as a filter and context layer.

5. UNCHANGED: everything else, including:
   - DESIGN-only data before any unseal;
   - ledger rules;
   - gates;
   - budgets (at most 24 configs and 2 logic revisions per family);
   - the trading-tool ban and MT5 attach-only;
   - no commit or push without the Owner.
