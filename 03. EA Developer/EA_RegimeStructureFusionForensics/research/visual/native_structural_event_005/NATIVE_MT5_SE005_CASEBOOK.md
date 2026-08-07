# Native MT5 structural-event casebook

Generated: 2026-08-07

## Evidence contract

These are native MetaTrader 5 Strategy Tester Visual Mode screenshots, not
Python-rendered or simulated charts. Each frame contains the compiled Modern
Bollinger Bands, QQE MOD and TB Smart Money Concept indicators plus actual case
entry, stop, target and outcome markers. Resolution is 1906 x 1025.

| Case | Outcome | SHA256 |
|---|---|---|
| C01 breakout long | loss | `67452B5E2E2DECBFCD240F67893B4672950813CB390279AE31905B192B912513` |
| C02 breakout long | win | `9C35452A9AB2F41AA9F6F51689C6EEE4CC58E28252A169BDA89035E0226DDA6B` |
| C03 breakout short | loss | `08BDE03940EE3B3DBE930FA63A7FD7AA1C7942CA9B34EF371303C8ED421D5D12` |
| C04 breakout short | win | `727DC695C57A4941301B8CD7E540D8257EDC4AD323FB421BC2BA5AA6806837B5` |
| C05 trend long | loss | `13A2908FF00B00A23E17AD59A132CACC196E74688ECC6FEC0C6E5435F35B89B1` |
| C06 trend long | win | `BB5966E553160E6BC54184D3F10B4E3A1F5412B22FD5A816E22BEB8EB8D33649` |
| C07 trend short | loss | `9B317122BAECDB42D4E0A429500875290231A04FF79272BC6C8BE1946D065E00` |
| C08 trend short | win | `B1CA6F5BE281AAC16E5416E0AFC6480F4F6B8473A51B91F701A1E5BFDDFC9AC2` |

## Pairwise chart reading

### Breakout long: C01 loss versus C02 win

- C01 buys the rebound after a sharp bearish displacement. Price is already
  approaching a visible bearish origin/supply cell, the TB state still shows
  bearish context, and QQE rolls back below zero immediately after the entry.
  The nominal forward target exists, but the usable corridor is obstructed.
- C02 follows a fresh bullish BOS from a defended local low. The protected low
  is close and structurally coherent with the stop, MBB basis/bands are turning
  upward, and QQE has crossed into positive expansion. The path to the marked
  target is comparatively clean.

### Breakout short: C03 loss versus C04 win

- C03 sells into an active recovery: the MBB basis is rising, price is pressing
  the upper band and QQE is strongly positive at the trigger. The MSS label by
  itself does not outweigh the opposing price/oscillator state; price extends
  upward into the stop.
- C04 enters after rejection from the upper structure, with a protected high
  above, falling MBB basis, negative QQE and a subsequent bearish BOS. The stop
  anchor and downside path agree with the visible structure.

### Trend long: C05 loss versus C06 win

- C05 attempts a long after a mature top has broken down. A protected high is
  overhead, TB context is bearish, a bearish MSS is visible below the entry and
  QQE turns negative. The label `TREND_LONG` is therefore stale relative to the
  current structural episode.
- C06 occurs inside an established higher-price sequence. A fresh BOS appears
  at entry, the protected low is nearby, price holds around the rising MBB
  basis and QQE turns positive. The trade participates in continuation rather
  than trying to repair a broken trend.

### Trend short: C07 loss versus C08 win

- C07 sells after the earlier down impulse has decayed into a narrow horizontal
  band. MBB is flat/compressed, QQE repeatedly crosses zero, and the stop sits
  close inside local noise. The old macro downswing is not a fresh entry event.
- C08 sells the actual release from a local range within a broader downtrend.
  Price breaks the lower structure while QQE expands deeply negative, and the
  target lies in the direction of the active displacement.

## Cross-case diagnosis

The common distinction is not a magic indicator threshold. Winners align four
relationships at the decision point: fresh structure, a defensible protected
swing, momentum expansion and a visually open corridor. Losses frequently use
an old regime label or isolated BOS/MSS tag after structure has already degraded
or while price/QQE points the other way.

This is outcome-locked forensic evidence. It explains why the tested decision
surface loses, but it cannot be converted into new filters under the same
hypothesis. The full HYP-010 population remains PF 0.714519 with negative mean
R, so any successor must define these relationships prospectively under a new
ID and pass outcome-blind feasibility before economics.

## MT5-only workflow boundary

All visual evidence, indicator state, trade diagnosis, and acceptance decisions
in this campaign come from native MetaTrader 5 and AlphaFactory artifacts. No
browser charting platform is part of the workflow or promotion gate.
