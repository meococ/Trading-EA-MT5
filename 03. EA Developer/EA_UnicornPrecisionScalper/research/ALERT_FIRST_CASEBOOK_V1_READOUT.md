# ALERT_FIRST_CASEBOOK_V1 research and implementation readout

## Verdict

`NO_LEGAL_TRADING_CANDIDATE / CASEBOOK_INSTRUMENTATION_COMPLETE`

The terminal Unicorn family was not reopened. Grok 4.5 and a primary-source
review found no defensible free-data mechanism that is both independent of the
killed OHLC family and usable for XAUUSD M5. The canonical EA was improved only
as a bounded pre-outcome data-acquisition tool. No signal threshold, entry,
stop, target, session, score or management rule changed. No Strategy Tester or
economic outcome run was executed.

## Research synthesis

- New York Fed order research supports stop-loss clustering and price cascades,
  but a bar-pattern sweep cannot establish the underlying order mechanism.
- Short-horizon price impact literature supports order-flow imbalance and book
  depth as relevant independent information. Historical COMEX depth is not
  currently licensed in this workspace.
- CFTC COT is a weekly Tuesday-to-Friday aggregate and is therefore a timescale
  mismatch for an M5 entry mechanism.
- Reusing the same OHLC surface for more RR, session, score, sweep or FVG
  variants would increase multiple-testing risk without introducing new data.

Primary sources and exact links are recorded in
`ALERT_FIRST_CASEBOOK_V1_CONTRACT.md`.

## Grok 4.5 council

The user-requested Grok call completed successfully through the file-based
runner (`model=grok-4.5`, exit code 0, non-empty response, zero stderr). It
returned `NO_LEGAL_CANDIDATE` and independently ranked an alert-first labeled
casebook as the only useful next step.

- Request SHA256:
  `8E93587168225EF82E3D3FEF6C773B29AADD39306B72904E1D10D48EB111970A`
- Response SHA256:
  `CEB95AD1EB1C152A415CC9854F7D209AA641864F9BDDBF0B0F65DB754C195502`
- Runner summary SHA256:
  `2D427B80FF2132C445CADCF4F6E8FADCDB22A717E10FB2EDB95F37950340C0A2`

Artifacts: `.context/unicorn_fresh_causal_research_20260716/`.

## Implemented instrumentation

- New opt-in inputs: `InpEnableAlertCasebook=false` and bounded
  `InpAlertCasebookMaxRows=200`.
- Casebook can initialize only in non-mutating alert-only mode and only when
  `TERMINAL_DATA_PATH` is on `D:`.
- `FILE_COMMON` is not used.
- Lifecycle telemetry now defaults off, so the safe alert preset does not
  create empty trade lifecycle logs.
- Each valid closed-bar alert is logged before any mutation path with a stable
  event id, UTC/server decision time, configured UTC offset, direction, score,
  correctly normalized sweep age/extreme,
  displacement ATR, FVG bounds/midpoint, overlap, H4/D1 bias,
  premium-discount state and spread.
- A separate metadata CSV binds the source-contract id, run id, broker/server,
  terminal build/data path and exact detector inputs even when lifecycle
  telemetry is disabled.
- Human-label columns are blank. The EA writes no PnL, future return, MFE, MAE
  or other outcome field.
- Rows are capped at 200 per attachment and flushed immediately.
- Post-audit engineering fixes also make new-bar/history/risk state fail closed,
  verify close/modify broker retcodes, block same-symbol pending exposure,
  recheck spread before send and remove the prior 5% risk-sizing tolerance.

## Verification

| Gate | Result |
|---|---|
| Package contracts | PASS, 41/41 |
| AlphaFactory compile | PASS, 0 errors / 0 warnings |
| Canonical source SHA256 | `DF86D6CDB00B28CBAFD7FC9540497C60EDE8CD922F9B54470BB8AAD14D11C166` |
| EX5 SHA256 | `F2CD23B0AFFC41EE00821A1EA7F9564795D07B15B3FBF9C38266C6C18C1CCFB3` |
| Compile log SHA256 | `5A615A1094D3B8DE8FC144BDBE585D618B7EE27291251032CF17E6A962B444B1` |
| Safe preset SHA256 | `F3543C8BEA0154FC3396DB9E97644FEC5DF39BEC4F179B3D47E2FB662331CFE1` |
| Exact-source non-repaint | PASS, zero findings |
| Audit manifest SHA256 | `98C60885D0619814A713607ED4C18FFBA81D4953392D2E165FA6D7F9A54688D0` |
| Audit artifact SHA256 | `8E215DF140B949E3D824E3DAFCF00B35A040CDADC3BB69B49D67D63D4EB1BB08` |
| C-profile cleanup | PASS, 360,407,524 run-created bytes removed; protected Common unchanged |

## Next legal gate

Collect at least 100 pre-outcome labels under the frozen contract. Do not join
forward outcomes until a separate analysis plan is sealed. Prefer two
independent reviewers and require predeclared agreement before any new feature
hypothesis. If accepted density is below 25%, close the detector-to-memo gap
without lowering thresholds. A future economic candidate requires a new
hypothesis id, a new window and either validated labels or an independently
licensed information set.

## v1.22 correctness addendum — 2026-07-16

The report-to-code fidelity audit found that event-sweep invalidation did not
explicitly scan the two completed displacement/FVG bars closest to the
decision. v1.22 fixes that closed-bar coverage without changing thresholds,
entry, stop, target, session or score. A no-outcome identity replay found zero
candidate changes from this correction on 2024-01-01 through 2025-12-25, so no
post-outcome economic rerun was authorized.

The same replay also found a separate preflight identity drift: the HYP-005
build probe scanned eight breaker bars while the Model-0 source/input used six,
creating a 17-identity symmetric difference (251 versus 234 candidates). This
does not rescue the killed source. It means the probe cannot be cited as an
exact source-equivalent build preflight.

Verification: 44/44 tests, compile 0/0 and exact-source non-repaint PASS.
Current source SHA256:
`A1AD68BC668C277D5EF85E54F61C28F0688D6FF9AC037A43368CECF45383B003`.
Identity audit:
`evidence/20260716_UNICORN_SIGNAL_IDENTITY_AUDIT.json`.

## v1.23 engineering and collection addendum — 2026-07-16

V1.23 does not change signal identity. It binds the exact source SHA256 into
casebook rows and metadata, adds a blank true-breaker label, makes mutation
tester-only, fails closed on incomplete exposure/history enumeration, binds
deviation to the declared slippage budget and reconciles money risk to actual
fill. The exact source compiled 0/0, passed 58/58 package tests and passed the
snapshot-bound non-repaint audit.

Zero-trade collection `20260716_155111` passed with 200 unique V1.3 rows, blank
labels, exact source-hash agreement and no protected C-root change. The V1.2
corpus remains preserved but diagnostic-only for labeling. See
`20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_READOUT.md`.
