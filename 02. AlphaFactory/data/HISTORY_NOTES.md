# Price history availability — MetaQuotes-Demo (Owner live terminal)

Measured 2026-08-31 against the Owner's already-running MT5 terminal
(`D:\Meta 5\terminal64.exe`, PID 12300, build 6151, account MetaQuotes-Demo,
data dir `%APPDATA%\MetaQuotes\Terminal\9CA16B8382AE4CF692710FB36B9DA355`).

Method: read-only `mcp__mt5__get_chart_history` probes, binary-searched
backwards with 1–3 bar windows. No process was started, no symbol was added to
or removed from Market Watch, no chart was opened or closed, no file was written
to the terminal, and the Strategy Tester was not run.

**Scope change note.** This file replaces an earlier plan to warm the factory
isolate at `02. AlphaFactory/runtime/mt5-portable-mqdemo/`. Under the Owner's
no-launch rule that isolate is unusable as a backtest target: it has no account
(`config/accounts.dat` absent), it holds zero `.hcc` history files, and a
terminal that is never launched can never download any. That line of work is
cancelled, not deferred.

---

## 1. Measured availability

### 1a. The binding constraint is a chart-series cap, not the broker

The terminal is configured with **Max bars in chart = 100,000**. This is
directly visible in `list_open_charts`: the XAUUSD H1 and EURUSD M5 charts both
report `total_bars: 100000` exactly (saturated), while GBPUSD/USDJPY/USDCHF H1
report 93,4xx–93,5xx (still filling).

That cap — not the broker — sets how far back each timeframe can be read
through the chart API. Because 100,000 bars is a *bar count*, the reachable
calendar depth scales with the timeframe:

| Timeframe | Confirmed **served** | Confirmed **empty** | Approx. depth | 100k-bar prediction |
|-----------|----------------------|---------------------|---------------|---------------------|
| M1        | 2026-06-05           | 2026-05-25          | ~3 months     | ~97 weekday days → 2026-05-26 |
| M5        | 2025-06-02           | 2025-04-01          | ~15 months    | ~486 days → 2025-05 |
| M15       | 2023-01-03           | 2022-06-01          | ~3.7 years    | ~4.0 years → 2022-09 |
| H1        | 2011-01-04 (EURUSD)  | 2010-01-04 (EURUSD) | ~15.7 years   | ~16 years → 2010-09 |

Every predicted boundary falls inside its measured bracket. The cap explains
all four floors.

The M1/M5/M15 floors were pinned on EURUSD and then **confirmed served on all
eight GOAL symbols** at the same probe dates (M1 @ 2026-06-05, M5 @ 2025-06-02,
M15 @ 2023-01-03) — all eight returned real bars.

### 1b. Deepest H1 bar confirmed per symbol

H1 is the only timeframe that reaches the 2016 evidence window, so it was
measured per symbol:

| Symbol | Server claim (`data_available_from`) | Deepest H1 bar confirmed served | M1 `.hcc` years on disk | 2016 on H1 |
|--------|--------------------------------------|----------------------------------|-------------------------|------------|
| XAUUSD | 2004-06-11 | 2013-01-07 11:00 | 2009–2026 | yes |
| EURUSD | 1971-01-04 | 2011-01-04 11:00 | 2010–2026 | yes |
| USDJPY | 1971-01-04 | 2012-01-03 11:00 | 2011–2026 | yes |
| GBPUSD | 1993-05-12 | 2013-01-07 11:00 | 2011–2026 | yes |
| USDCHF | 1971-01-04 | 2012-01-03 11:00 | 2011–2026 | yes |
| USDCAD | 1993-04-28 | 2014-01-06 11:00 | 2011–2026 | yes |
| AUDUSD | 1993-04-27 | 2014-01-06 11:00 | 2011–2026 | yes |
| NZDUSD | 1994-02-01 | 2014-01-06 11:00 | 2011–2026 | yes |

Two columns that must not be conflated:

- **Server claim** is the `data_available_from` field MT5 reports per symbol. It
  is the server's assertion about its own archive. It was **not** verified —
  nothing here proves a 1971 EURUSD bar can actually be retrieved, and the
  100k cap means it cannot be read through the chart API regardless.
- **Deepest H1 bar confirmed served** is a real OHLC record that came back from
  a probe. That is evidence.

**These floors moved during measurement and are a snapshot, not a limit.**
Reading a range MT5 has not cached returns empty *and queues a background
download*. Over the session the on-disk M1 store went from
`XAUUSD 2026 only / EURUSD 2022–2026 / USDCAD, AUDUSD, NZDUSD absent` to
**2009–2011 starts for all eight**. Symbols probed earlier therefore show
deeper floors than symbols probed later; the differences above are download
frontier plus cap, **not** per-symbol broker limits. Left alone with a request
for older data, every symbol should converge on the same ~100k-bar cap.

### 1c. The lazy-download trap

Any future tooling that reads MT5 history must not trust the first read. A
first `copy_rates_range` / `get_chart_history` over an uncached range returns
an **empty array**, which is indistinguishable from "no such data" unless you
retry. Every empty result above was re-probed at least once before being
recorded as empty, and several "empty" results became populated minutes later.

---

## 2. 2016 reachability

**On H1: yes, for all eight GOAL symbols** — verified with real bars at
2011–2014, well before 2016.

**On M1, M5 and M15: no, not through the chart API** — the 100k cap puts the
floors at ~2026-06, ~2025-06 and ~2023-01 respectively.

The important qualifier: the **underlying M1 store on disk reaches 2009–2011
for all eight symbols**. MT5 keeps raw minute history in
`bases/MetaQuotes-Demo/history/<symbol>/<year>.hcc`, and those year files now
exist continuously from 2009–2011 to 2026, ~22 MB each (~21 MB for XAUUSD).
The chart-series cap is a *display/API* limit layered on top of that store; the
Strategy Tester reads the store directly and is not bound by it.

So for GOAL.md the accurate wording is **not** "broker-limited to 2023". It is:

> MetaQuotes-Demo serves all eight target symbols back past 2016. The 2016
> evidence window is reachable. Direct M1/M5/M15 reads via the chart API are
> capped at 100,000 bars per timeframe (a terminal setting, not a broker
> limit); the M1 store that the Strategy Tester consumes reaches 2009–2011.

That the tester can actually consume it is an **inference from how MT5 stores
history, not a measured fact** — see section 6.

---

## 3. GOAL symbols absent from Market Watch

**None.** All eight are present and visible in the Owner's Market Watch:

XAUUSD, EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD.

This corrects an earlier assumption. USDCAD, AUDUSD and NZDUSD had **no cached
history** at session start, which is a different thing from being absent — they
were in Market Watch the whole time and began downloading as soon as they were
read. Nothing had to be added.

Also present, outside the GOAL universe and not measured: USDCNH, USDSEK, AMD,
MSFT, INTC, NVDA.

---

## 4. Feed caveat — this is not the funded broker

MetaQuotes-Demo is MetaQuotes' own demo feed. The funded account is
**The5ers / Five Percent Online LTD**, server `FivePercentOnline-Real`,
account #26451822. They are different venues with different books.

Spreads sampled from the probes above, in points, show how unstable this feed's
cost structure is even within itself:

| Sample | Spread |
|--------|--------|
| EURUSD M1 2026-06-05 | 2 |
| EURUSD H1 2016-01-04 | 7 |
| EURUSD H1 2014-06-02 | 1 |
| EURUSD M5 2025-06-02 | 8 |
| USDCHF M5 2025-06-02 | 21 |
| USDCAD M5 2025-06-02 | 22 |
| XAUUSD H1 2016-01-04 | 24–27 |
| XAUUSD H1 2013-01-07 | 43–44 |
| NZDUSD H1 2016-01-04 | 21 |

A 1-point EURUSD H1 spread in 2014 next to 7 points in 2016 and 8 points on M5
in 2025 is not a market fact, it is an artifact of how this demo feed recorded
its own history. Consequences:

- **Never take a cost assumption from this feed as the funded cost.** Commission
  is absent here entirely; The5ers' commission, swap and slippage model is not
  represented at all.
- Any edge measured here must be **stress-tested across a spread range**, not
  run once at the historical spread. An edge that dies at 2x the recorded spread
  is not an edge on a funded account.
- Fills are demo fills. No rejections, no requotes, no partial fills, no
  weekend gap risk priced the way a real counterparty prices it.

---

## 5. Hedge vs Netting

The Owner's live terminal runs in **Hedge** mode. The factory isolate, being
freshly created with no account, defaults to **Netting** — its window title
reads `MetaTrader 5 - Netting - EURUSD,H1`.

This matters because it changes position accounting outright: under Netting,
opposing orders on one symbol collapse into a single net position; under
Hedging they coexist as separate positions with separate tickets, SL/TP and
swap. A strategy that opens opposing or scaled positions produces **different
equity curves** under the two models — not a rounding difference, a structural
one.

Any result produced on the live terminal is therefore a Hedge-mode result, and
must be labelled as such. The reconciliation is now moot for the isolate (it is
cancelled), but it remains live for the funded account: confirm The5ers'
account mode before treating any test as representative.

**Not independently verified in this pass.** Hedge mode is recorded here as
stated by the Owner. `get_trading_account_info` (which returns `margin_mode`)
was outside the read set authorised for this measurement, so it was not called.
Confirm before relying on it.

---

## 6. History quality and the >97% gate

MT5's Strategy Tester "history quality" percentage is computed from **M1 bar
density** over the tested range — how many of the expected minute bars actually
exist in the `.hcc` store, before the tester synthesises ticks from them.

What can be said from what was measured:

- The M1 `.hcc` year files exist **continuously** from 2009–2011 through 2026
  for all eight symbols. No gap years.
- File sizes are uniform (~22.4 MB for FX, ~21.1 MB for XAUUSD) across 2016,
  2020 and 2025 alike. MT5 preallocates these files, so **size is structural
  and is not a density measurement** — it rules out truncation, nothing more.
- H1 bars for 2016 return real OHLC with plausible `tick_volume` (EURUSD 7,548–
  12,015 per hour; XAUUSD 5,984–9,039). In MT5 an H1 bar is aggregated from the
  M1 store, so **minute data for 2016 must exist** to produce them. That is
  solid indirect evidence of real 2016 minute coverage.

What **cannot** be said:

- **No per-symbol history-quality figure was measured, and none should be
  quoted.** The chart API cannot read M1 before ~2026-06 (the cap), and running
  the tester — the only thing that computes the actual percentage — is
  forbidden under the no-launch rule.
- The >97% gate is therefore **plausible but unproven** for every symbol. On a
  MetaQuotes demo feed, 2016+ M1 coverage is typically dense enough to clear
  97%; older ranges (pre-2010) thin out badly. Nothing here upgrades that from
  expectation to evidence.

Treat "history quality >97%" as an **open gate** per symbol until a tester run
reports it. Do not record it as satisfied on the strength of this document.

---

## 7. Backtest route under the no-launch rule

No MetaTrader process may be started by any route. That eliminates:

- `alpha.ps1 backtest` — launches the isolate terminal.
- `mt5.initialize(path=...)` from Python — the MetaTrader5 package **launches**
  the terminal at that path if it is not already running.
- `terminal64.exe` invoked directly.

The only remaining route is **`mcp__mt5__tester_run_backtest` on the Owner's
already-running live terminal** (PID 12300), which starts nothing.

Its standing constraints:

- It runs on the **Owner's GUI terminal**, competing with live charts, against
  **this broker's history** — not the pinned portable isolate.
- It is therefore **not reproducible** on another machine: the numbers depend on
  the Owner's local cache state, which, as section 1b shows, changes as a side
  effect of merely reading it.
- It runs in **Hedge** mode (section 5), and on a **demo feed with no
  commission** (section 4).

**Exploration only. Never a decision number.** Any result from this route may
inform what to try next; it may not be recorded as evidence that a strategy is
profitable, and it may not satisfy a GOAL gate.

---

## Provenance

- Terminal: build 6151, MetaQuotes-Demo, PID 12300, already running throughout.
- Server time at measurement: 2026-08-31 17:55 (UTC+3); UTC 14:55.
- Probe times in this document are **server time**, as returned by MT5.
- Tooling: `mcp__mt5__get_chart_history`, `get_marketwatch_symbols`,
  `list_open_charts`, `get_time_information`, `get_workspace_info` — all
  read-only. No `mcp__mt5__trade_*` tool was called.
- Side effect to be aware of: these read probes caused the terminal to download
  roughly 2009–2011 → 2026 of M1 history for eight symbols into
  `bases/MetaQuotes-Demo/history/`. That is added cache, not modified state, but
  it grew that directory to **2.6 GB** (measured after the session; it held only
  a handful of recent years' files beforehand).
