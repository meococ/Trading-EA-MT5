# HYP-CUSX-XAUUSD-M5-001 — source result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_TWO_SIDED_CUSUM_REGIME_SHIFT`

The sole outcome-blind source attempt completed with a full structured evidence
chain and deterministic replay. The exact `ATR48 / k=0.05 / h=3.00` alternating
polarity CUSUM is structurally too frequent for the 2–5/week EA envelope.

- DESIGN rows: `351,303` — PASS.
- Feature coverage: `99.6273%` — PASS.
- Raw/executable events: `8,494 / 8,325`.
- Exact-next coverage: `99.8352%` — PASS.
- LONG/SHORT: `4,167 / 4,158` — PASS.
- Pooled cadence: `31.9140/week` — FAIL.
- Annual cadence: `29.2623–33.6192/week` — all FAIL.
- Maximum year share: `21.0571%` — PASS.
- Conflicts: `0`; deterministic replay: PASS.

Evidence SHA256:

- start `0D363046EED9AF06838466D9BDBC55CD37E7E229AB0E58385E4ABDE9EC9D0CB0`;
- report `2BDA2465E37EF69F3031D99DEF876C23C31DAFD288BD335C2AF2131474F1B4AD`;
- ledger `ACBB8807299A43D245A04F029E24F8587F6E6F9A7E79765558DED74589B6C896`;
- receipt `48986D08546E0E6DDFE787FEC5485BB831B3F3F6A7155F71D86ED82804509CC8`;
- terminal `A9967A50661929C32B846A7000FE62A57B7237CCE769A6BA4257676A48267E6B`.

No post-decision price, return, simulated trade, PnL, cost, PF, MQL5, MT5,
validation or holdout was opened. Do not raise the threshold, change `k/ATR`,
add a cooldown/session/direction filter or change timeframe under this ID.
