# Frozen source prereg — HYP-ISVA-XAUUSD-M5-001

Frozen before opening XAUUSD DESIGN rows or computing any ISVA event count.

## Market mechanism

- EA: `EA_IntradaySemivarianceAbsorption`.
- Symbol/timeframe: FivePercent `XAUUSD`, native M5.
- DESIGN: `2018-01-01T00:00:00Z` inclusive to `2023-01-01T00:00:00Z`
  exclusive; all outcomes and all 2023+ rows remain sealed.
- At one fixed daily checkpoint, compare realized downside versus upside
  semivariance of the completed 00:00–15:55 UTC path with where price closes
  inside that path's high-low range. Downside variance dominance plus a strong
  close is treated as absorbed selling and emits LONG; upside variance
  dominance plus a weak close is the exact SHORT inverse.
- This is a joint path-shape object. The failure catalog closes signed
  semivariance and close-location as single-object rebrands, but explicitly
  leaves context-conditional multi-factor mechanizations untested. No prior
  repository object uses their strict joint daily state.

## Data capability

- Manifest SHA256:
  `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- Data:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet`.
- Data SHA256:
  `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`.
- Manifest proves native XAU M5, complete UTC, strict unique source chronology
  and DESIGN coverage. No paid data is required.

## Exact causal formula

For each UTC Monday–Friday date `d`:

1. Require exactly 192 source rows at UTC times `00:00, 00:05, ... 15:55`,
   each separated by 300 seconds. An incomplete date emits nothing.
2. For closes `C_0..C_191`, define 191 within-session log returns
   `r_i=log(C_i/C_{i-1})`, `i=1..191`.
3. `RVplus=sum(r_i^2 where r_i>0)` and
   `RVminus=sum(r_i^2 where r_i<0)`. Zero returns contribute to neither.
4. Let `H=max(high_0..high_191)`, `L=min(low_0..low_191)` and
   `CLV=(C_191-L)/(H-L)`. A nonpositive range or nonfinite component makes the
   date unusable.
5. LONG raw event iff `RVminus>RVplus` and `CLV>=2/3`.
6. SHORT raw event iff `RVplus>RVminus` and `CLV<=1/3`.
7. Equality never satisfies variance dominance. LONG and SHORT cannot both
   occur. There is no ratio threshold, ATR/ADX/volume/VWAP/trend filter,
   alternate checkpoint, cooldown, quota or parameter grid.

The decision is the completed `15:55` bar. Availability is the next source row
and must be exactly `16:00` UTC/source epoch +300. Friday 16:00 is allowed; no
new entry is allowed at/after Friday 20:00. Decision year is availability year.

Ledger allowlist: IDs, UTC date, decision/availability clocks, direction,
`RVplus`, `RVminus`, `CLV`, session H/L/close, exact-next and session-complete.
No post-16:00 price, return, cost or outcome is allowed.

## Frozen source gates

- DESIGN rows >=300,000;
- exact-session coverage over calendar weekdays >=95%;
- exact-next coverage among raw events >=97%;
- executable events >=500;
- cadence 2.0–5.0 per elapsed calendar week;
- LONG and SHORT each >=30%;
- maximum decision-year share <=30%;
- every year 2018–2022 cadence 1.25–6.5/week;
- zero conflicts;
- deterministic byte-identical replay.

Any failure parks only this exact daily joint semivariance/CLV absorption
mapping. No checkpoint, CLV fraction, variance inequality, direction, session,
symbol or timeframe rescue is allowed under this ID.

## Evidence boundary

- Sole durable attempt: `ISVA-SOURCE-001`.
- Claim/fsync precedes bound input reads. A normal PARK still writes report,
  ledger, receipt and COMPLETE terminal. Any exception writes structured
  failure context with hashes, observed counts and known gates.
- PASS authorizes only direct unchanged MQL5 build/parity/compile/non-repaint
  and a later separately frozen untuned baseline. Economics, optimization,
  validation, holdout, paper, promotion and live remain unauthorized.
