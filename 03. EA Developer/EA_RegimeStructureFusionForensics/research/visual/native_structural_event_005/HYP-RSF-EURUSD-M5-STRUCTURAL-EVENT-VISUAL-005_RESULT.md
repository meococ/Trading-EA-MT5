# HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-VISUAL-005 — native chart result

Status: **EVIDENCE CAPTURE COMPLETE — DIAGNOSTIC ONLY**

This closes the frozen eight-case native MT5 Visual Mode campaign. It does not
change the terminal economic kill of `HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-004`
or `HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010`.

## What was actually inspected

- Eight full-window Strategy Tester Visual Mode replays on EURUSD M5, Model 1.
- Compiled MBB and TB SMC indicators on the price pane.
- Compiled QQE MOD in its own pane.
- AIRD and VRC remained live calculation handles/telemetry inputs but were not
  duplicated visually. Showing their pane/dashboard objects on top of MBB, TB,
  order lines and tester markers made the price decision point materially less
  readable.
- Frozen reference entry, SL, TP and post-exit outcome marker for one loss and
  one win in each executed route.
- No Skip-To. Each frozen window ran from its warm-up start.

The canonical per-case interpretation is stored in
`NATIVE_MT5_SE005_FAILURE_MATRIX.csv`. It links the chart evidence to structure,
protected swing geometry, MBB phase, QQE phase and forward corridor without
inventing a favorable numeric threshold after observing the outcome.

## Artifact reconciliation

| Case | Run | Outcome R | PNG bytes | PNG SHA256 | Report SHA256 |
|---|---|---:|---:|---|---|
| C01 breakout long loss | `20260807_084953` | -1.1250 | 872707 | `67452B5E2E2DECBFCD240F67893B4672950813CB390279AE31905B192B912513` | `CEACCF7E8EB9EC6A61F8EC2D4E53492E2C6214468C2F45AE4FCCBD8B29E7C41A` |
| C02 breakout long win | `20260807_085218` | +1.5047 | 980273 | `9C35452A9AB2F41AA9F6F51689C6EEE4CC58E28252A169BDA89035E0226DDA6B` | `7522B24FAD403027951F4C9AFC13374A285A104E8CFE165BF45950A43DCE73EA` |
| C03 breakout short loss | `20260807_085351` | -1.1172 | 871243 | `08BDE03940EE3B3DBE930FA63A7FD7AA1C7942CA9B34EF371303C8ED421D5D12` | `D523304CB593985BBFF8702DB7C2DB45525F43EAA43DD801700A7E78151FD976` |
| C04 breakout short win | `20260807_085519` | +1.5200 | 908311 | `727DC695C57A4941301B8CD7E540D8257EDC4AD323FB421BC2BA5AA6806837B5` | `8E791E03BD0B3D2FA7B540005B6D6E97413E03D1A9D9337C9767DF595E1BC8C2` |
| C05 trend long loss | `20260807_085647` | -1.1036 | 911860 | `13A2908FF00B00A23E17AD59A132CACC196E74688ECC6FEC0C6E5435F35B89B1` | `09EA83C3E1271D9E1159E42FD840A1BD272ECB8177739FDD0878219BCF2C579E` |
| C06 trend long win | `20260807_085815` | +1.5974 | 798997 | `BB5966E553160E6BC54184D3F10B4E3A1F5412B22FD5A816E22BEB8EB8D33649` | `ED53DC4BBD121347C28A7C26BB52283586EB3ADE98B06648FA05F678E71B8CD7` |
| C07 trend short loss | `20260807_085938` | -1.1143 | 762410 | `9B317122BAECDB42D4E0A429500875290231A04FF79272BC6C8BE1946D065E00` | `9B9120A1CC82FC2C5E3675C9E480BF6383166AD8411148958F6692EE4632D960` |
| C08 trend short win | `20260807_090100` | +1.5000 | 881361 | `B1CA6F5BE281AAC16E5416E0AFC6480F4F6B8473A51B91F701A1E5BFDDFC9AC2` | `5461841206C55E1166E4AE11FD2FE9FE301E76FC78FB174161C19C853AEEAA57` |

Each PNG hash above equals the copy imported into the matching AlphaFactory run
directory. The eight reference outcomes also match the hash-bound selection
manifest frozen before chart viewing.

## Chart-derived failure anatomy

The failed entries are not explained by one bad indicator value. They fail at
the relationship level:

1. **Episode mismatch.** C05 and C07 keep a trend-side route after the visible
   structural episode has changed or decayed. An old directional state is not a
   fresh entry event.
2. **Momentum/structure conflict.** C01 and C03 act on an isolated structural
   tag while live price and QQE are moving in the opposite direction.
3. **Invalidation quality.** Failed trades often place the stop inside noise or
   lack a directionally coherent protected swing. Winners have a defended local
   swing that makes the thesis falsifiable.
4. **Corridor quality.** C01 has a nominal target but visible opposing supply is
   already in the path. A target price is not equivalent to an executable open
   corridor.
5. **Location/energy phase.** C07 enters in flat compression. C02, C04, C06 and
   C08 enter during expansion aligned with the structural event.

## Display decision

The least-cluttered evidence layout is now the canonical Visual Mode preset:

- price pane: candles + MBB + TB focus mode + entry/SL/TP/outcome;
- subwindow: QQE MOD;
- hidden-but-logged: AIRD and VRC buffers/state;
- one case per replay and one post-exit screenshot.

This preserves every EA input while keeping the actual structural decision
readable. It is a visual evidence preset, not a change to the trading rules.

## Statistical boundary

The sample is deliberately symmetric but only eight trades. The charts were
read after outcomes were known. Therefore:

- the matrix can diagnose the failure radius;
- it cannot authorize a threshold, route deletion, session filter or parameter
  rescue;
- any new episode/corridor/expansion rule needs a fresh hypothesis ID, a frozen
  closed-bar definition and a previously unopened validation window;
- the whole HYP-010 population remains the economic truth: 162 trades, PF
  0.714519 and negative mean R.

Terminal verdict for this diagnostic lane: **capture complete, economic-valid
false, promotion-ready false**.
