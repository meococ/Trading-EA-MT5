# HYP-BKSR-XAUUSD-M5-001 - Independent Pre-Run Review

Verdict: `PASS`

Reviewed exact frozen identities:

- preregistration SHA256: `97E807BDE74ADB213AE01E026603C5149D2E958B8DE37D8FA8F412C3A0CB3E7C`
- analyzer SHA256: `CC393F09795346901353DE120D6C9B94E94078AF4EFFC260E4DC43E1E86F8164`
- tests SHA256: `9BCE42530E3880D42EC1E0BC25B107675B27BF31CE01A9005F9BB58332465E2E`
- focused tests: `26 PASS`

The direct H1 formula is causal and matches the preregistration: BB20 uses SMA and population deviation with multiplier 2; KC20 uses SMA-seeded EMA, exact TR0/subsequent true range and SMA-seeded Wilder ATR with multiplier 1.5. The first strict off bar after a consecutive strict BB-inside-KC cluster is the only release bar, with direction from release close versus current BB basis.

The outcome-blind ledger proves the final squeeze bar is strict-inside, the release bar is strict-off, the bars are adjacent, and cluster length is internally exact. The decision mapping requires native M5 UTC `+1h` and source epoch `+3600`; the M5 read contract contains no price columns. Raw clock gaps are consumed.

Canonical de-dup found zero Bollinger-Keltner, BBKC or squeeze-release hypotheses. The object is materially distinct from existing fixed-compression breakouts and all prior oscillator/flip mechanisms.

Authorize exactly one outcome-blind source-feasibility attempt. Do not authorize MT5, MQL5, outcomes, economics, validation, holdout, optimization, promotion or live trading.
