# HYP-AROON-XAUUSD-M15-002 — Source Result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_AROON25_POLARITY_CROSS`

The sole vectorized outcome-blind attempt completed in 14.3 seconds with deterministic replay and a complete receipt/terminal chain.

Results:

- represented M15 rows through 2022: 424,166;
- design rows: 117,790; complete: 115,746;
- feature-usable: 88,486; coverage 75.1218% — FAIL versus 99%;
- raw/executable/gap-rejected: 3,665 / 3,647 / 18;
- exact-next coverage: 99.5089% — PASS;
- cadence: 13.9808/week — FAIL versus 2–5/week;
- LONG/SHORT: 1,840 / 1,807 — PASS;
- yearly events: 629 / 676 / 676 / 671 / 995;
- every-year cadence: 12.063–19.082/week — FAIL versus 1.25–6.50/week;
- sample size, direction balance, year concentration and conflicts pass.

The failure radius is only the exact Aroon-25 polarity crossover on deterministically aggregated complete M5 triplets, scored 2018–2022. No post-event OHLC, trades, returns, PnL, profit factor, validation or holdout data was read. This is not an economic no-edge result.

No threshold, filter, cooldown, debounce or same-ID retry is authorized. No MQL5 build is authorized.
