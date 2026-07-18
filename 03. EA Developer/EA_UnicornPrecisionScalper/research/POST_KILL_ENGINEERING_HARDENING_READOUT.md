# Post-kill engineering hardening readout

## Status

`ENGINEERING_HARDENING_COMPLETE_NO_ECONOMIC_AUTHORITY`

This work hardens the canonical MQL5 kernel after the terminal HYP-006 and
HYP-007 verdicts. It does not alter either historical result, authorize a new
performance run, or promote the Unicorn family. The exact Model-0 source stays
immutable at
`research/source_snapshots/EA_UnicornPrecisionScalper_HYP-006_CB51EB2A.mq5`
with SHA256
`CB51EB2A72CBD1567452F6EA33983C5EAB4C32506A6E3A1CD1E47DBFF182A7B8`.

## Hardened behavior

- Alert-only is truly non-mutating: it cannot place, modify or close trades.
- Research-auto for the retired HYP-006 identity fails closed unless the
  explicit retired-execution override and positive commission/slippage inputs
  are both supplied. This is an engineering interlock, not run authority.
- Startup seeds the current M5 time bucket and waits for the next bar, so an
  attach/restart cannot fire a stale previous-bar setup.
- Explicit execution FSM covers alert-only, idle, placing, waiting-fill,
  managing, risk-locked and recovery states. `OnTradeTransaction()` drives
  entry/final-close/partial-close transitions.
- Ownership requires symbol + magic + strategy comment. Foreign same-symbol
  exposure blocks a new request, including unsafe netting-account merges.
- Broker trade mode, account/terminal permissions, stops level, freeze level,
  filling mode and `OrderCheck()` fail closed before mutation.
- Position size includes the declared round-turn commission and adverse
  slippage estimate in addition to stop loss.
- Max trades/day counts unique entry position identifiers. Consecutive losses
  aggregate lifecycle P/L rather than treating each exit deal as a trade.
- Initial risk is captured from actual fill/SL geometry and survives partial
  entry callbacks. Peak equity persists across authorized non-tester restarts.
- Rejection reasons are counted and emitted as a bounded deinit summary instead
  of writing a high-volume per-bar trace.
- The active preset is `presets/ALERT_ONLY_HARDENED.set`; the old HYP-002 auto
  preset is retained only as a research snapshot and removed from active use.

## Verification

| Gate | Result |
|---|---|
| Focused + legacy package tests | PASS, 30/30 |
| AlphaFactory compile | PASS, 0 errors / 0 warnings |
| Canonical MQ5 SHA256 | `0B5F272AD849E281B85F574351C718BC554D6BE49B2DC7B6A274855665E94E30` |
| EX5 SHA256 | `D3A52BFB016D756E043CC3C7FC1F1BED0A19FFA4E7F19E7CF81166E0433A80F4` |
| MetaEditor log SHA256 | `B5991A0467C233471BC2C274432E9D5DCF1B2819F3A7D7293475714436D86E03` |
| Exact-source non-repaint | PASS, zero findings |
| Audit manifest SHA256 | `E1D2724D126FC1BA660F3B29D220CF3696CC42AF7C61202018303ADDF48729B9` |
| Non-repaint artifact SHA256 | `687EF278A26BFC7E1CDE5958D492E989ED7E3F080BC0161AAE613FC8E1E3D5A3` |
| Alert-only preset SHA256 | `45FA5FA1160B5EE0BBD43F5B6AB475F764E91A71DCD5DA39FFCD10B2ADCB3084` |

The first static audit iteration correctly rejected an `iTime(...,0)` startup
seed that it could not distinguish from decision access. The source was fixed
to derive the startup M5 bucket from server time; final V3 exact-source audit
passes without weakening the auditor.

## Runtime and storage closure

An alert-only one-day runtime smoke was requested through `alpha.ps1`, but the
harness rejected it before terminal launch because a fresh contract receipt was
not supplied. No bypass was used, no run directory was created and no economic
metric was read. This is the correct fail-closed outcome for a retired
hypothesis.

MT5 remains stopped. Install/data/tester are on the portable `D:` root and
`FILE_COMMON` remains forbidden. Protected C Common stayed at 137 files and
20,008,308 bytes through the rejected smoke attempts; there was no run-owned C
artifact to delete.

## Remaining boundary

The software kernel is materially safer and auditable, but the underlying
Unicorn market-entry edge remains terminal. Compile/non-repaint quality cannot
turn PF 0.498 into an economic pass. Any future performance claim needs a fresh
authorized hypothesis and contract-bound Model 0; this hardened build itself
has `promotion_eligible=false` and no live/paper authority.
