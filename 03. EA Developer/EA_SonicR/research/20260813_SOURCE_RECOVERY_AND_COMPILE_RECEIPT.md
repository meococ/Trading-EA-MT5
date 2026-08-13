# EA_SonicR source recovery and compile receipt

Date: 2026-08-13  
Verdict: `SOURCE_RECOVERED / ENGINEERING_BUILD_PASS / ECONOMICS_UNVERIFIED`

## Recovery identity

- ZIP:
  `C:\Users\ADMIN\.codex\visualizations\2026\08\09\019fe528-57e7-7f63-8b80-9d1aff3841f9\sonicr_legacy_source_b709309.zip`
- ZIP SHA256:
  `9F61C13CA24145A138C8997FC37ACCC9275789DA40007DA702822C3DC394B27E`
- ZIP created/modified UTC: `2026-08-09 06:44:17`
- Main source SHA256:
  `BCE6ABCF55DDFD503651482ED6FA1643A0302098D7FA3D559B538743A745893D`
- Restored file set: one `.mq5` plus seven `.mqh` files. All eight canonical
  copies matched their ZIP-stage hashes byte-for-byte.
- No file from the ZIP's legacy `research/` directory was restored. In
  particular, its old candidate registry did not replace or merge into the
  canonical registry.

The source declares `#property version "2.00"` and the unique input
`InpUseAutoSleeveConfig`. This connects it structurally to the historical
manifests that invoked `InpUseAutoSleeveConfig=true`; it does not by itself
prove byte identity with the early-July executable.

## Safety review

The source/include closure contains no `#import`, DLL reference, WebRequest,
shell/process launch, network URL, file delete/move/copy, terminal close or
expert-removal operation. File access is limited to calendar reads and
FILE_COMMON telemetry writes.

Preliminary no-lookahead audit:

- decision series use `CopyRates(..., 1, ...)` and
  `CopyBuffer(..., buffer, 1, ...)` through closed-bar helpers;
- explicit H4/H1/M15 reads also start at shift 1;
- `iTime(..., 0)` in `OnTick` is only a new-bar clock; it triggers construction
  of a context from shift-1 data;
- no entry/filter path using bar-zero OHLC was found.

Verdict: `NONREPAINT_STATIC_PASS_PRELIMINARY`. Runtime parity/replay is still
required before this can be called a reproduced executable.

## Compile proof

Command:

`02. AlphaFactory/alpha.ps1 compile EA_SonicR`

Fresh artifacts:

- log: `03. EA Developer/EA_SonicR/EA_SonicR.log`
- log result: `0 errors, 0 warnings`, elapsed `5413 ms`, target `X64 Regular`
- EX5: `03. EA Developer/EA_SonicR/EA_SonicR.ex5`
- EX5 bytes: `432574`
- EX5 SHA256:
  `A75D552FE7E814C8C8EE7DB61ECD8463E08F7F3C21A1198C728B2362FA6FC1BD`
- EX5 timestamp UTC: `2026-08-13 02:08:12`

This is compile/engineering evidence only. The archived EX5 remains a separate
binary with SHA256
`B9CF2CE8D351EDE658A88907A28C4AAF1A7DCDBC4C5C3C56CCA63ABB92320C0A`.

## Historical evidence boundary

The recovered source is highly parameterized and its XAU auto-sleeve enables a
multi-component Dynamic SMC/Sonic configuration. Historical catalog rows show
127 trades and PF about 1.40 on 2024-2025, but 335 trades and only PF 1.15-1.16
on 2021-2025. Those outcomes were already known and are not promotion proof.

The next intended market action is exactly one **reproduction**, not
optimization, and it may run only after the historical calendar sidecar is
recovered exactly:

- XAUUSD M5;
- 2024.01.01 through 2025.12.25;
- Model 0, execution mode 0, current tester spread;
- deposit USD 100,000, leverage 1:100;
- `InpUseAutoSleeveConfig=true`;
- telemetry off for the reproduction unless the frozen receipt requires the
  historical profile;
- compare population/trade timestamps and headline metrics to run
  `20260701_134204`.

The run may establish source/run lineage only. It cannot make the recovered EA
economic-valid or promotion-ready, and it cannot authorize tuning from the
known results.

## Independent Grok Build source audit

A bounded, read-only Grok Build review of the recovered source and the exact
historical run surface completed with:

- `verdict=PASS_TO_REPRODUCTION_CONTRACT`;
- `source_identity_confidence=MEDIUM` because the freshly compiled EX5 is not
  byte-identical to the archived executable;
- `nonrepaint_verdict=PASS` for static closed-bar signal reads;
- `telemetry_off_signal_equivalent=true`;
- no fatal source-level blocker.

Accepted artifacts:

- `.context/grok-sonic-source-recovery-review-20260813/run2/summary.json`
- `.context/grok-sonic-source-recovery-review-20260813/run2/grok-response.json`

This independent result authorizes only the frozen lineage-reproduction
contract. It does not authorize optimization, OOS, promotion or live trading.
Local artifacts remain authoritative over the advisory result.

## Reproduction preflight: exact calendar sidecar missing

The historical run meta binds the replay to:

- file `SNR_FX_EVENTS.csv` through `FILE_COMMON`;
- snapshot ID `SNR_FX_EVENTS_AUTO`;
- SHA256 `b62eab34e6630f6255f97aedc280bde438d53ef1643ef1ee29effc9f5d6634c7`;
- 448 events covering `2019.01.04 15:30:00` through
  `2026.12.25 15:30:00`;
- classes `CPI,FOMC,GDP,NFP,PCE,RATE`;
- provenance
  `legacy_news_events_csv_normalized_by_build_calendar_snapshot_ps1`.

Current preflight found neither `SNR_FX_EVENTS.csv` nor the legacy
`news_events.csv` in the portable runtime's Common Files or the MetaQuotes
profile Common Files. A renamed-file scan across the task artifacts, MetaQuotes
profile, user Desktop/Documents/Downloads/OneDrive, the EA workspace and
`D:\Downloads` found no CSV matching either recorded historical size (34,630
bytes for `SNR_FX_EVENTS.csv`, 17,326 bytes for `news_events.csv`). The source
fails closed when the news calendar is unavailable, so running now would
produce a non-comparable zero/altered signal population. A one-event 342-byte
engineering fixture used in a prior session is not the historical 448-event
snapshot and is forbidden as a substitute. Disabling the news filter is also
forbidden because it changes strategy identity.

Runtime status also shows the Owner's FivePercent portable terminal already
running as PID 42864 with the `EURUSD,M5` chart. It must not be killed or
repurposed. A later bounded forensic pass searched exact name, same-size and
renamed candidates across task artifacts, likely user/storage roots, MetaQuotes,
the workspace and Recycle Bin. Session transcripts prove the file existed
through 2026-07-08, but do not preserve its complete bytes. The terminal verdict
is `EXACT_RECOVERY_NOT_PROVEN`; the frozen replay is unavailable unless the
exact hash-bound bytes reappear. No economic conclusion follows from this
missing file, and the overall EA goal remains `ACTIVE / UNMET`.

The follow-up Grok decision and the AlphaFactory input-escrow correction are
recorded in
`04. Memory/research/20260813_SONIC_CALENDAR_RECOVERY_FRONTIER_AND_INPUT_ESCROW.md`.

## Git-independent operation

The Owner directed Git to remain outside the active loop. AlphaFactory and its
research loop now accept `ALPHAFACTORY_FORCE_NOGIT=1`, which binds deterministic
hashes of `AGENTS.md`, `01. GOAL/GOAL.md` and the active source without invoking
Git. Two focused tests pass. The mode does not bypass the execution receipt or
any market-evidence gate.
