# HYP-EIBB-XAUUSD-M15-001 — Economic failure

Verdict: `KILL_BASE_PF_AND_EXPECTANCY_FAIL_CADENCE_DD_PASS`

## Frozen scope

- EA: `EA_EuropeInitialBalanceBreakout`
- Run: `20260811_151212`
- FivePercent XAUUSD native M5, Model 0, `2018.01.01`–`2023.01.01`
- Signal: exact M5 reconstruction of the four-bar 07:00–07:45 UTC M15 initial balance; first 08:00–15:45 completed-M15 close outside the balance; one event/day.
- Stop: opposite initial-balance edge; target: `1.50R`; risk: `0.10%` equity; maximum hold: 48 M5 bars.

## Engineering reconciliation

- Source screen: raw/executable `1287/1287`, LONG/SHORT `664/623`, `4.9337/week`.
- Runtime summary: raw `1287`, LONG/SHORT `664/623`, entries `1287`, rejects `0`, risk-lock skips `0`, invalid inputs `0`, runtime failure `false`.
- MT5 report: 1,287 completed trades. The source opportunity population and executed population therefore reconcile exactly.
- History Quality `99%`; 351,303 M5 bars and 135,208,676 ticks; journal was not truncated (`8,357,520` raw bytes under the frozen 16 MiB cap).
- Compile: 0 errors / 0 warnings; static non-repaint audit PASS.

## Economic result

- Profit factor: `0.9188839355` — FAIL versus strict `>1.30`.
- Expectancy: `-$3.3447008547/trade` — FAIL versus strict `>0`.
- Net profit: `-$4,304.63`.
- Commission: `-$930.99`; swap: `-$37.42`.
- Cadence: `4.9337/week` — PASS versus `2–5/week`.
- Maximum drawdown: `6.4196%` — PASS versus `<=8%`.
- Validation, OOS, holdout, optimization and promotion remain unopened.

## Evidence identities

- Run manifest: `BE827F8F45F4153A25C1CBAD0CB28F33BBD5FBCD9D6BD28BE3572BF862C604A7`
- MT5 report: `1A9C3DA4663DBEC91970B30C72447EBBF6A252C8612F88E83419C3EF75970F6A`
- Journal: `5D23D2E9EC1DD28125CDCB8041117F563DC619B30AB114BDB83F3B0D622354C7`
- Analysis summary: `B14CED114BEFEE711D483F1DB46CBFECFA670B207F88494F75A30CF89010C515`
- Source snapshot: `F24FDDC36D51AAED2A27A69CA646058EBB5AA5B1D557C1B7B011B606311A3ABE`
- Run EX5 snapshot: `49C2837BC29833CC642055659E8F2C5EBCF216E96CD19B6244E9F8EA06C6E341`
- Contract receipt: `289C983CE57688E73F57C37FD6AE9A3DE43C8B29A1E5106CB2EDE1D3931BD613`

## Failure radius and no-rescue boundary

This kills only the exact XAUUSD M5-built M15, 07:00 UTC four-bar initial-balance first-close breakout with the frozen structural stop, 1.50R target and 48-M5-bar hold. It is a valid economic failure, not an implementation failure.

Do not rescue this object by deleting Wednesday/New York/years, changing the session, selecting a direction, shifting the balance window, adding volatility/trend filters, or changing stop/target/hold/risk after reading the report. Any later work must be a materially fresh market mechanism with a new preregistration. The overall EA goal remains active.
