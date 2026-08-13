# HYP-CME6E-OPT-PIN-EURUSD-M15-002 - source design kill

Status: `KILL_SOURCE_DESIGN_EARLY_MATHEMATICAL`

## Frozen gate

The source preregistration fixed 516 non-overlap DESIGN events and required at
least 95% source-valid coverage. A stable listed option contract without an
admissible normalized open-interest record is `UNKNOWN`; it cannot be filled
as zero or removed from the surface.

Passing therefore requires at least 491 source-valid events and permits at
most 25 invalid events.

## Outcome-blind observation

The first 30 completed payloads in the one-shot acquisition manifest were
selected by acquisition ordinal, not by their values. The authority-bound
strict analyzer found:

- 0 source-valid events;
- 30 invalid events;
- all 30 events had at least one contract with unknown normalized OI;
- zero post-decision rows, unresolved aliases, or OI delete rows in this
  audited prefix.

Even if every unaudited event passed, the best possible result would be
486/516 = 94.1860465%, below the frozen 95% gate. HYP002 is consequently
terminal without opening any futures direction, EURUSD target, return, PnL,
MQL5, MT5, optimization, validation, or promotion evidence.

A subsequent fail-only monotonic audit checked all 291 completed payloads. It
found 0 source-valid, 291 source-invalid, and 291/291 with unknown normalized
OI. With only 225 unacquired events, the best-case completed population would
be 225/516 = 43.6046512%. Partial data is permitted to kill this gate but can
never pass it.

## Acquisition stop

The paid one-shot acquisition was stopped after 291 completed payloads because
the preregistered gate was already mathematically impossible. The original
manifest remains unmodified with status `IN_FLIGHT`, 291 completed calls and
291 hash-bound payloads. One interrupted `.partial` file is preserved in place
as evidence. Retry and partial resume remain forbidden.

The quote for all 516 requests was USD 0.364300683141. Actual provider billing
for the completed and interrupted calls is not inferred here.

## Evidence

- `design_source_early_stop_analysis_pit.json` SHA-256
  `DADDD0B09098D68E266F4203BC2AF8067FC7130BD6437418A69D537C954BAB77`;
- `design_source_early_stop_receipt_pit.json` SHA-256
  `3476C2E6EA72A0668C37C503EA6970DF1AEB643619FF5F46FC8B9E58426240BC`;
- stopped manifest SHA-256
  `1D6689220CEA30D11DCE62A23DEA7FDB74D24B128041FA8B5F3F123AB2DD0027`;
- authority-bound strict analyzer SHA-256
  `8C66234139CA3690DC1DF974E6D9CCEF0D87F9ED26494863C19C4631EDB57338`;
- all-291 monotonic audit SHA-256
  `0DA455B22ABCC08FA2CA4CDCC0E69B194313E1EA754276E0B85762B3F6DCC17F`;
- terminal acquisition receipt SHA-256
  `0DB2B4750A34D16B6C9DB3C908DDA0825827DC8E7C329905DDB96B6F675DAD47`.

## Research consequence

HYP002 cannot be revived by treating missing normalized OI as zero, dropping
contracts, selecting only high-coverage expiries, changing the 95% gate, or
using HYP001 futures/target material. Any continuation requires a new
hypothesis ID and a materially different source contract or market mechanism.
HYP002 artifacts may be used only as outcome-blind source-capability and
failure evidence.
