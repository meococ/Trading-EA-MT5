# HYP-XBT-MM-TRADETHROUGH-004 — Source/expiry gate result

Verdict: `ENGINEERING_KILL_SOURCE_COVERAGE_AND_ZOMBIE_EXPIRY`  
Economic metrics: forbidden and not inspected.

## Fatal source receipt

Official BitMEX archives for 2018-02-02 produced a deterministic V4 manifest
with:

- quote invalid time: 1,093.617816 seconds;
- invalid quote ratio: 0.0126576136 (1.2658%);
- frozen maximum: 0.005 (0.5%);
- maximum XBTUSD quote gap: 817.577143 seconds;
- maximum XBTUSD trade gap: 1,072.116402 seconds;
- source gate: false.

The raw quote/trade files, event stream, and manifest were all hash-bound. A
second all-symbol scan found an exchange-wide trade-archive silence from
13:22:28.366201 to 13:40:03.319300 UTC. Its operational cause is unconfirmed.
Grok initially claimed a primary BitMEX outage post, but retracted that claim
when required to provide a resolvable primary URL and supporting excerpts.
Therefore this interval cannot be relabelled or whitelisted as a known market
halt.

Manifest:
`02. AlphaFactory/external/bitmex_xbtusd/manifests_v4/2018/02/20180202.event_manifest.json`

Bindings:

- quote SHA-256: `88586C0E156648B226A57E71860EC96ECADBF63F28B3C4283DF4561E4651B0E9`
- trade SHA-256: `D6C0F177DC4E22412154FBB6800052594C60547E6C21DD1A4FD573DDC95A4E1B`
- event SHA-256: `E0F70D9A6590CD360E07BD1150D1FDFB1A71C16815B8E0FBE8AE6101C0934DF1`
- event digest64: `D0569258F8349E8C`

## Fatal execution-model receipt

V4 `ExpireStaleOrders` calls `ResetOrder` after two seconds of quote age without
an outbound cancel request, latency, or exchange acknowledgement. A 2018 BitMEX
GTC/post-only order had no verified exchange-native two-second TTL. During a
feed/API outage, a real resting order can remain live and fill before a cancel is
acknowledged when connectivity resumes. V4 makes that zombie order disappear
locally, so the model is optimistic and not deployable.

## Disposition

- Seal V4 source, preregistration, and engineering runs.
- Do not run full-DESIGN economics, optimization, validation, or holdout.
- Do not repair V4 in place.
- A future identity may revisit the mechanism only with independently complete
  source for every invalid interval and acknowledged-cancel/zombie-order state.
  Relaxing the 0.5% threshold or whitelisting 2018-02-02 is forbidden.
