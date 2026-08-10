# HYP-STBS-XAUUSD-M15-006 — Point-bounded observable geometry comparator

Preregistered at: `2026-08-09T06:40:00Z`

## Question and scope

Can a fresh comparator-only revision validate all observable HYP003 signal/ATR/geometry-readiness telemetry without claiming unidentifiable raw-double or runtime-tick-size parity?

HYP006 is a fresh engineering child of terminal `HYP-STBS-XAUUSD-M15-005`. It replays every inherited HYP005/HYP004 gate over the exact completed HYP003 artifacts. It performs no AlphaFactory call, compile, MT5 launch, source acquisition, order, outcome, performance or economics.

## Frozen identities

- Hypothesis: `HYP-STBS-XAUUSD-M15-006`.
- Attempt: `STBS006-COMPARATOR-001`, limit one, no retry.
- Parent indicator-parity object: `HYP-ST-XAUUSD-H1-012`.
- Terminal HYP005 raw registry row SHA256: `179BD0163632218A026E433FC68E416CF49EEE9BE8613593A1AF40ABA6261942`.
- Frozen HYP005 comparator: `03. EA Developer/EA_SupertrendBurstScalper/research/compare_stbs005_exact_orders_heading.py`, SHA256 `F55AF249A00D905DA1E183FC3CECE3F5D74D45965C9AC416AE15F8EADBFF77ED`.
- HYP005 authority raw SHA256: `2A06DAC8C758D95C870C85775A9496D0759FE972BC2ECD8E448F2671BC332444`.
- HYP005 attempt start SHA256: `B43F8B50DB8E9BADB4F6B7C6814FD91BAA7702B2458C9B5DD756B2C708E83EAA`.
- HYP005 failed terminal SHA256: `D0DA049862B26BAD9897798FF344B6944BCFADD970FF532D66AEB04B42356DF2`.
- HYP005 failure document SHA256: `2CA213847823372C480B8E965A608FD56467D5EB13EDDAEC0A45D5BD363ED5AE`.
- HYP005 post-failure review SHA256: `22FC569727E2E98637203B22E177252FF6AC005CD4FD619453AE37CD70B31572`.
- HYP004/HYP003 code, run, oracle and artifact bindings remain exactly inherited through the single-captured HYP005 dependency and its frozen base buffers.

The HYP006 wrapper captures HYP005 once, verifies its SHA, and compile/executes only that buffer. HYP005 in turn captures the exact HYP004 bytes once. The HYP006 receipt binds those same executed buffers without reopening either base path. All non-code evidence is opened only after the durable HYP006 claim and parsed from the captured bytes.

## Frozen observable geometry contract

Manifest-bound symbol point is `0.01`, digits are `2`, and telemetry prints ATR/entry/SL/TP/volume to eight decimal places. Freeze `POINT=0.01` and `TOL=0.5e-8 + 1e-9 = 6e-9` before execution.

For every one of the expected 683 executable signals:

- ATR, entry, stop, target and volume must be finite and strictly positive.
- LONG requires `stop < entry < target`; SHORT requires `target < entry < stop`.
- Entry, stop and target must each be point-aligned within `TOL`.
- Define `risk=abs(entry-stop)` and `reward=abs(target-entry)`.
- Require `-TOL <= risk - printed_ATR <= POINT + TOL`.
- Require `-TOL <= reward - 1.5*risk <= POINT + TOL`.

This tolerance derives only from the frozen eight-decimal telemetry precision plus a fixed numerical allowance; it is not fitted to observed extrema. This proves point-bounded observable consistency/readiness only. It does not prove the unprinted ATR double, runtime `SYMBOL_TRADE_TICK_SIZE`, exact normalized prices or exact 0.25% position sizing.

Every other frozen HYP005/HYP004 gate remains unchanged: exact English/NFC-Vietnamese heading, Orders structure, BOM/duplicate-key rules, manifest/DQ/series proof, zero-trade summary, journal multiplicity, dual UTC/server clocks, full referenced next oracle row, signal/direction/exact-next/gap mapping, count reconciliation, Alpha stdout/stderr, deterministic replay and zero-authority boundary.

## Output and verdict boundary

The inherited analyzer must return exact HYP004 schema before HYP006 emits fresh schema `stbs006_point_bounded_geometry_comparator_report.v1`. Required fields include:

- `point_bounded_telemetry_consistency=true`
- `geometry_point=0.01`
- `geometry_tolerance=0.000000006`
- `exact_raw_double_geometry_proven=false`
- `runtime_tick_size_proven=false`
- `exact_position_sizing_proven=false`

PASS may state only `ENGINEERING_VALID_STBS_MODEL0_SIGNAL_ATR_POINT_BOUNDED_GEOMETRY_AUDIT_PASS`. It cannot state PF, expectancy, cost realism, robustness or deployment readiness.
