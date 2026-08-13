# Frozen source prereg — HYP-KST-XAUUSD-M15-001

Frozen before reading DESIGN rows or computing any KST crossover count.

## Thesis and de-dup

- EA: `EA_KnowSureThingCross`; FivePercent `XAUUSD`, M15.
- DESIGN: 2018-01-01 inclusive through 2023-01-01 exclusive; outcomes and
  2023+ remain sealed.
- TradingView describes Know Sure Thing as a weighted composite of four
  smoothed price ROC cycles and identifies signal-line crossovers as changes in
  underlying momentum. Official defaults are
  `10,15,20,30,10,10,10,15,9`:
  `https://www.tradingview.com/support/solutions/43000502329-know-sure-thing-kst/`.
- TradingView is formula provenance only. MT5-native broker bars, direct MQL5
  and AlphaFactory are the acceptance authority.
- Repository de-dup found no prior KST/Summed Rate of Change object. This is a
  four-horizon momentum composite, not Line Break state, single-horizon TRIX,
  Coppock, cross-asset momentum, oscillator extreme reentry or indicator vote.

## Data and exact formula

- Use the same exact FivePercent XAUUSD M5 source and causal native-M15
  aggregation frozen for TLB001. No paid data.
- Frozen M15 aggregation dependency:
  `03. EA Developer/EA_ThreeLineBreakReversal/research/analyze_tlb_source.py`,
  SHA256 `92174C77F64609F20A392C274E208097E0F4E3AF8DD45FFA5B71D8865CF6F8FA`.
- For completed M15 close `C_t`, `ROC_n(t)=100*(C_t/C_(t-n)-1)` for
  `n in {10,15,20,30}`.
- `RCMA1=SMA10(ROC10)`, `RCMA2=SMA10(ROC15)`,
  `RCMA3=SMA10(ROC20)`, `RCMA4=SMA15(ROC30)`.
- `KST=RCMA1 + 2*RCMA2 + 3*RCMA3 + 4*RCMA4`.
- `Signal=SMA9(KST)`.
- Rolling windows require every constituent finite; no partial warmup.

## Exact event

- LONG on completed M15 `t` only when prior `KST<=Signal`, current
  `KST>Signal`, and current KST is strictly negative.
- SHORT is exact inverse: prior `KST>=Signal`, current `KST<Signal`, and
  current KST is strictly positive.
- Equality only arms the next strict cross and never emits on the current bar.
- Decision is completed M15 `t`; availability must be the exact next M15 open
  at `t+900` seconds. Inspect next timestamp only, never price.
- No zero-line event, divergence, threshold, session, weekday, ATR, volume,
  cooldown, debounce, direction deletion or parameter grid.

## Gates and authority

- M15 rows >=115,000; exact-bucket coverage >=98%; feature coverage >=99% of
  rows after the exact 53-row warmup; exact-next >=97%;
- executable N>=500; cadence 2–5/week; each direction >=30%;
- maximum decision-year share <=30%; every year 1.25–6.5/week;
- zero conflicts and deterministic replay.

Sole attempt `KST001-SOURCE-001` must claim/fsync before source data access and
write structured report/ledger/receipt/terminal. No outcome, trade, return,
cost or PF field is permitted.

Any failed gate parks this exact default KST sign-conditioned crossover. Do not rescue
it with alternate ROC/SMA lengths, zero-line signals, session, cooldown,
direction or threshold. PASS authorizes only unchanged direct MQL5 build,
compile/non-repaint and one separately frozen untuned baseline. Optimization,
validation, holdout, promotion, paper and live remain closed.
