# Baseline result - HYP-EPC-USDJPY-M15-002

Verdict: `KILL_NEGATIVE_EDGE_OVERTRADING_FULL_WINDOW_NO_OOS`.

AlphaFactory run `20260812_015906`, USDJPY M15 Model 0, current broker spread, HQ100, full 2018-2021 design window. Engineering passed: fresh compile `0 errors, 0 warnings`, runtime parity/throughput checks `10/10`, complete 4.79 MB untruncated journal, runtime_failed=false, and maximum logged margin use 0.0301%.

Performance: 1,520 trades; net `-$326.14`; PF `0.8584`; WR `46.8%`; expectancy `-$0.21/trade`; max DD `0.3498%`; maximum losing streak 10. The 1,520 entries across 865 days, with up to five entries/day, exceed the preregistered 580-trade maximum by 940. Low drawdown reflects the 3.5x notional cap forcing 0.03 lots, not signal quality.

Telemetry: 87,634 closed bars, 2,427 high-efficiency triggers, 2,068 persistence signals, 1,520 entries, 46 spread rejects, 481 overlap skips, and 21 order rejects. Journal price PnL summed to `-$143.74`; report-level costs reduced net by another `$182.40`. The signal is therefore negative before costs and worse after costs. Exit decomposition: 731 `SL`-reason exits netted `-$722.69`; 616 time stops `+$526.23`; 137 daily flats `+$49.70`; 36 Friday flats `+$3.02`.

Chart readback: a persistent stair-step decline with isolated recovery spikes, a sharp loss in early 2020, partial recovery into late 2020, and renewed decline through 2021. Equity ends near the path-worst drawdown. The New York PF 1.06 and Wednesday PF 1.03 subgroups do not authorize post-hoc filtering.

Kill the exact ER10 >=0.68 trigger, later same-direction ER >=0.55 persistence, 0.30 ATR reversal cap, efficiency-window structural stop, BE/ATR trail, and 12-bar time-stop object. No session/day filter, cooldown, ER/ATR/exit tuning, control, OOS, or holdout.

Evidence hashes: source `7D81F8BE16897713AA4600CD33BBDF13BA92644127D541709D733B3DE4573684`; EX5 `0746AB6A0A7BC201464DE337089FD86450819B4FFCA58901FB35914DCA8D4723`; report `359671669E4F39C741E3986F026717B31C3F2FB1A208C5C98FC85D4473D7D957`; journal `1EB053F0BBAC89ACEACBE16B3E91162760FA5F98F341B1D0CC3F71405FFA0646`; chart `C38BE5F5B2F804BDDEA983578B06A83C13F025EDC4D24537AEDB1A0C83B1DDB0`.
