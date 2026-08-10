# HYP-ST-XAUUSD-H1-001 — Source-validation result

## Verdict

`KILL_SOURCE_VALIDATION_EXACT_STRICT_GEOMETRY`

The sole durable attempt was claimed, opened only the preregistered native XAUUSD H1 source through `<2023`, and stopped before indicator analysis because the frozen frame validator required `high > low` on every bar.

## Evidence

- Attempt marker: `ST001-SOURCE-ATTEMPT-001`, SHA-256 `96B27CCE1DDFFBE3D39CD30DDCD19C8660B45DC9D9DA98916DA08D84E71BA932`.
- Analyzer failure: `ValueError: all inception-through-design price rows must be geometrically valid`.
- Source-only diagnostic: 107,679 rows before 2023; zero non-finite rows, zero inverted high/low rows, zero closes outside the bar, and 194 finite flat bars with `H=L=C`.
- Three flat bars occur in the 2018–2022 score window. The earliest flat bar is in the recursive prehistory, so deleting only design rows would not repair the frozen full-chain contract.
- No source report, event ledger, receipt, or terminal artifact was emitted. The durable start marker makes same-ID retry illegal.

## Interpretation and failure radius

This kills only the exact ST001 input contract: native FivePercent XAUUSD H1, recursive inception-through-2022 state, Supertrend 10/3, with strict `high > low` required on every source row. It says nothing about Supertrend event cadence or economics because neither was reached.

Flat, finite OHLC bars are valid inputs to TR/ATR and the recursive bands. A fresh hypothesis may change only the input-validity predicate to `high >= low` with `low <= close <= high`, explicitly accept `H=L=C`, and retain the exact frozen formula, state machine, source, score window, next-bar rule and gates. That revision must use a new ID and a new one-shot authority.

## Prohibitions

- No retry or artifact repair under `HYP-ST-XAUUSD-H1-001`.
- No deletion, interpolation or reset at flat bars.
- No parameter, seed, state, filter, cooldown, session, cost or outcome change justified by this failure.
- No economic, MT5, MQL5 or promotion claim from this packet.
