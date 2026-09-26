# 2026-09-12 — CELL 6: EA_Ibsc EURUSD M5 kill + verified_m1_asof coverage mode

## Result

| Field | Value |
|---|---|
| Hypothesis | HYP-IBSC-EU-M5-001 (IBS 0.8/0.2 continuation + H4 EMA50) |
| Run | `20260912_082329` (governed, complete loop end-to-end) |
| Window | 1999.01.01 → 2026.09.10 (`verified_m1_asof`, first use) |
| History quality | **99%** (gate >97) |
| Trades | 33,822 — cadence **23.4/wk PASS** |
| Report PF / Net / DD | 0.79 / -8,813 USD / 88.2% |
| Cost PF x1.0 / x1.5 / x2.0 | **0.68** / 0.62 / 0.56 |
| MC p95 DD / Robustness | 88.7% / 14.3% |
| Overnight / weekend | 1 / 0 — FAIL |
| Verdict | REVIEW → **KILLED_AT_MODEL_0** |

## Structural finding: stub-era coverage

EURUSD on MetaQuotes-Demo syncs from **1971.01.04**, but per-year `.hcc`
audit shows 1971–1998 are daily-stub files (~76KB/yr); real M1 begins
**1999** (~20MB/yr). The frozen `all_available_asof` sentinel window
(1970→) therefore reports quality 49% and can never pass the >97 gate —
same mechanism as the GBPUSD 1993–1998 stub finding (82%).

## New coverage mode: verified_m1_asof

Added a second governed coverage mode (engine `research_loop_engine.ps1`
packet validation + `alpha.ps1` contract resolve/run-evidence gates):

- `requested_from` must be a real date > the 1970 sentinel and equal the
  packet/binding `from`.
- Post-run journal must still cover the request: `actual_from <=
  requested_from` (both alpha gate and engine manifest↔packet compare).
- Series proof equality changes: the tester pre-loads ~1y warm-up, so the
  M5 first date legitimately precedes `requested_from`. Invariant under
  verified mode: `journal_actual_from <= m5_first <= requested_from` and
  journal/M5/terminal/CopyTime still agree internally.
- `coverage_class = VERIFIED_M1_START` recorded in the gate object.
- `all_available_asof` sentinel semantics unchanged; data-acquisition
  receipt authority still requires the sentinel.
- Tests: 19/19 in `test_data_quality_gate.py` including new covered /
  uncovered / sentinel-misuse / contract-resolve cases.

Window amendment was made **pre-performance**: the first run died at the
quality gate (49%) before any economic output was read; the prereg
amendment and registry provenance record this.

## Economic reading

EURUSD cost evidence (measured 2026-09-11, isolate): spread p90 **0.1
pips**, slippage p90 0.2 pips RT @250ms — ~40x cheaper than XAUUSD. Even
so, IBS 0.8/0.2 continuation produced PF 0.68 at 1.0x cost — the
mechanism itself has no edge on EURUSD M5; costs were not the
disqualifier here.

## Cell tally (6 kills)

CRSI-R2 GBPUSD (data) · AMA XAU · VwapFade XAU · HourDrift XAU ·
GBBSqueeze XAU · **IBSC EURUSD**. No sleeve has passed. Next candidates:
CamarillaFade / Keltner / Dcmid / H1pb / H4pb / Hod on EURUSD.
