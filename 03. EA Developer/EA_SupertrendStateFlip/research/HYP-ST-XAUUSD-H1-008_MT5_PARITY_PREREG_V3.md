# HYP-ST-XAUUSD-H1-008 - frozen inception-preloaded MT5 parity audit V3

Status: `FROZEN_PRE_MT5_DATA_ACQUISITION_ONLY_V3`  
Parent: `HYP-ST-XAUUSD-H1-007` (`KILL_MT5_PREHISTORY_UNAVAILABLE_AND_LOCALIZED_HQ_PARSE`)  
Parity target: `HYP-ST-XAUUSD-H1-003`

## Evidence-driven revision

ST007 proved that a tester start at 2018 exposes only about one prior year of
H1 cache, so the exact 2004 recursive Supertrend state cannot be rebuilt. HYP008
changes the tester acquisition start to `2005.01.01`, which requests cache
before the broker's first native H1 bar `2004.06.11 07:00` server time. State
advances on every completed native H1 bar. The EA persists parity rows only for
bars in the exact half-open server-time interval
`2018.01.01 02:00 <= t < 2023.01.01 02:00`.

The source revision is limited to correctness/audit hardening while keeping the
trading formula unchanged: the exact design start/end persistence guard;
expected first, last and last-next timestamp assertions; expected 29,460 row
assertion; and fail-closed initialization/summary handling. TR0, SMA10 seed,
Wilder RMA, band update order, initial DOWN state, strict comparisons, flat
bars, gap treatment and inner HYP003/ST003 identities remain unchanged. No
historical row is skipped in state evolution.

ST007 also exposed localized report text such as `100% <localized suffix>`.
AlphaFactory now extracts only an anchored leading invariant percentage for
History Quality; malformed text still fails and the strict gate remains `>97`.

Repeated MetaEditor compilation produced different EX5 bytes for identical
source. HYP008 therefore does not use cross-compile EX5 byte equality as a
correctness claim and does not pre-bind an unknown EX5 or compile-log hash. The
sole AlphaFactory run must bind the exact source snapshot, compiler evidence,
run manifest, 0-error/0-warning run-local compile log and canonical run-local
EX5 snapshot. The comparator must consume those exact run-local paths.

V2 was never authorized or executed. It is retained as disclosed unused
preflight evidence because it contained a contradictory narrative `00:00`
design-start reference and a stale Model4 cost-manifest label. V3 supersedes it
before any ST008 attempt is opened.

## Frozen contract

- Outer ID/attempts: `HYP-ST-XAUUSD-H1-008`; `ST008-MT5-001`,
  `ST008-ARTIFACT-COLLECT-001`, `ST008-COMPARATOR-001`, each once.
- Inner oracle/output: HYP003 / `ST003-MT5-PARITY-001` /
  `ST003_MQL5_PARITY_001.csv`.
- Source SHA-256: `580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF`.
- AlphaFactory SHA-256: `68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8`.
- Exact overrides: `InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpParityFileName=ST003_MQL5_PARITY_001.csv`.
- XAUUSD H1; acquisition/tester `2005.01.01`-`2023.01.01`; design/output
  server `[2018.01.01 02:00, 2023.01.01 02:00)`; Model 0; execution/delay 0;
  timeout 1800; control; telemetry none/off; 10000/100/current; empty spread
  CLI token.
- Authority `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`; fixed-window HQ
  `>97`, journal bounds, no-skip and exact M5/M1 provenance proof.
- Expected output is exactly 29,460 rows; first source epoch `1514883600`, last
  source epoch `1672437600`, and final next epoch `1672441200`.

## Acceptance and prohibitions

Before authority, freeze V3 packet/receipt/snapshot/non-repaint audit/tests and
independent review; common CSV and ST008 root must be absent. Any stage failure
consumes its ID.

PASS requires full exact inception rebuild, compile 0E/0W, one clean summary
`rows=29460/raw=690/executable=683/gaps=7/long=339/short=344`, exact full-bar
oracle parity, History Quality `>97`, and zero orders/deals.

No outcome, PnL, PF, economics, optimization, validation, holdout, paper or
live authority is opened. Economic work requires a fresh child after parity.

Model 0 is mandatory for this correctness audit: FivePercent real ticks begin
only in 2026, outside the design window, while the EA consumes completed H1
bars only. Model 4 would test unavailable real-tick provenance rather than MQL
formula parity. Model 0 performance remains explicitly unauthorized.
