# PA-PRO CHARTER — ADDENDUM 4 (Lead, 2026-09-21T05:59Z)

## A4.1 Perception comes first, with its own gate
- Setups consume the frozen Perception v1 Snapshot API (`docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md`).
- No setup family may be screened on a perception layer that has not passed P-v1 (spec §6).
- **Why:** SF01 showed that setups built on dense, unstable zones carry no information. The Owner judged the drawing layer not good enough and made it the priority on 2026-09-21.

## A4.2 BOOK carve-out
- **Window:** EURUSD, 2012-02-13 00:00 → 2012-09-07 23:59 CET. This is the Volman casebook period, 1 Mar – 31 Aug 2012, plus 2 weeks on each side.
- **Allowed use:** perception fidelity only. Load bars, compute the EMA and perception objects, and compare them with the golden labels.
- **Forbidden:** trade simulation, PnL, outcomes, MFE/MAE, setup screens or census counts of trades.
- **Loader:** access goes only through `research/perception/golden/book_loader.py`. It asserts the symbol, asserts the window, and refuses to run if any outcome or referee module (`pa_fill`, `pa_eval`, `pa_random`, `arrival_outcome`, `phys_resolve`) is imported in the process.
- **Permanent exclusion:** the window is excluded from CONFIRM-PRE forever. Any CONFIRM tooling must mask it and test that it does. The casebook itself shows these sessions' outcomes, so they can never serve as a blind confirmation.
- **Other years:** no other 2010–2015 bar may be read, for any purpose.

## A4.3 Book material stays private
- Page images, OCR text and reading notes stay under `EA_VolmanPA/PLAN/book/_private/` (gitignored); the perception notes are in `_private/notes_perception/`.
- Golden labels are numeric coordinates, not text or images. They may live in `research/perception/golden/` but are gitignored until the Owner says otherwise.
- Quotes of 15 words or fewer, at most a few.
