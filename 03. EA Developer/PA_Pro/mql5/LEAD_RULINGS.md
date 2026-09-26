# EA LANE - LEAD RULINGS

Append-only; newest entries last. Re-read this file before each new component.

## Ruling 1 (04:32Z) - D1-D7 accepted; SF01 result; priorities for the rest of the box

- **D1-D7: all ACCEPTED as written.** Specific notes:
  - D2 (two tracks, st and stx, following the sf_ctx replay) is exactly the reference semantics.
  - D3 (H1 built from the EA's own M5 series) is the right parity doctrine.
  - D5 (every trade API call inside the one gated function, plus a static test) is the proof the Owner needs.
- **SF01 closed with 0 of 6 survivors** (`rounds/SF01/LEAD_RULINGS.md`, Review 3). None of the six setups beat matched-random entry.
  - Do NOT port F1-F6 setup logic beyond the existing interface and stubs.
  - The EA's value right now is the platform: zones at exact-replay parity, the session/risk/trade plumbing, the journal, the visual layer, and the parity and tester harness.
  - Setup modules get ported only after the SF lane reports a SURVIVOR and the Lead confirms it.
- **Priorities for the rest of the box:**
  1. **Parity harness.**
     - Build the Python exporter, the comparator and `mql5/parity/RUNBOOK.md`, targeting zone-view parity of at least 99.5% on DESIGN sample weeks.
     - Anything that needs MT5 to run must go through alpha.ps1 only.
     - Where alpha.ps1 cannot run it, prepare everything and write in the RUNBOOK the exact steps for the Owner/Lead. Never launch a terminal yourself.
  2. **`mql5/HUONG_DAN.md`:** a short Vietnamese guide for the Owner covering what the EA does, SIGNAL_ONLY, inputs, overlay and journal.
  3. **A salience hook in PA_Zones.**
     - The SF02 lane is likely to introduce a per-zone SALIENCE score and keep only the top 1-2 zones per side instead of up to 6 armed zones.
     - Shape the API now so that a score field and a top-k filter can be added without a refactor.
     - Do NOT implement a score until SF02 defines one in `rounds/SF02/`.
  4. **Keep the SUMMARY current**, as your resume prompt already requires.
- **Walls unchanged:**
  - SIGNAL_ONLY stays true;
  - no terminal launch outside alpha.ps1;
  - no git commit or push;
  - no deletes;
  - no MT5 trade tools.

## Ruling 2 (06:01Z) - the drawing layer is being rebuilt; switch the visual priority
- **Why the change.** The Owner judged the drawing not good enough. The Lead issued `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md` (Volman's own drawing grammar) and `docs/CHARTER_ADDENDUM_4.md`. A PERCEPTION lane builds the Python reference in `research/perception/`. Read the spec, especially §2 (object grammar) and §8.
- **PA_Zones.mqh stays as it is.** Do no further work on the generators or on zone parity. The new objects (BOX, RANGE_OPEN, CONTEXT_RANGE, PATTERN_LINE, CONTEXT_LINE, LEVEL_CARRIED, MINI_LEVEL, SQUEEZE, LABEL_TF, BRACKET) replace zones for drawing.
- **Priority 1: the drawing grammar in PA_Visual.**
  - Drive it from a snapshot CSV/JSON, i.e. the object list per bar in the `schema/perception_v1.json` format, once the perception lane writes it. Until then, use a small mock file you write yourself.
  - Styles, per spec §2:
    - solid rectangle;
    - two open lines;
    - dotted rectangle;
    - solid and dotted diagonals;
    - long-dashed carried level;
    - short mini-level;
    - dashed ellipse;
    - T/F letters;
    - M/W/SHS span brackets with a centred letter;
    - EMA25;
    - no 00/50 drawings.
  - Edges render as thin bands (±tol), per the Owner's rule that S/R is a small zone.
- **Priority 2:** a `PA_Perception.mqh` skeleton — structs and enums that mirror the schema, plus a snapshot importer for the parity tests.
- **Priority 3:** generalize the parity harness from zones to perception objects.
- **Port the engine logic only after P-FREEZE,** from `research/perception/PORT_NOTES_MQL5.md`.
- **Walls unchanged:**
  - SIGNAL_ONLY;
  - alpha.ps1 only;
  - no commit or push;
  - no deletes.
