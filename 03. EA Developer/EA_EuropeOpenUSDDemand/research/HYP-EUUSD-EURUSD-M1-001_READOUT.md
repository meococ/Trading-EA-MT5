# HYP-EUUSD-EURUSD-M1-001 — TRAIN readout

## Verdict

`KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`

The source-ranked EURUSD direction produced a real but insufficient gross
effect. All 5 structural gates passed; only 2 of 8 economic gates passed. No
MQL5, Model 0, validation, holdout, optimization, promotion, paper, or live
authority is opened.

## Frozen object and engineering validity

- EURUSD completed-Bid M1 close-only DESIGN, 2016-2020
- Europe/Berlin `07:59` completed close to `14:14` completed close
- Always SHORT EURUSD; one complete weekday trade
- Round-trip costs 1.50 / 2.25 / 3.00 pips
- Exact matched reverse; eight x1 DSR arms

| Check | Result |
|---|---:|
| Complete trades | 1,296 |
| Weekday coverage | 99.3865% |
| Trades per elapsed calendar week | 4.965517 |
| Largest year share | 20.0617% |
| Exact fixed-short boundary contract | PASS |
| Structural gates | 5 / 5 |

The plan, registry authority, evaluator, tests, parquet/manifest, three prior
ledgers, common helper, DSR module, attempt marker, trade ledger and terminal
result are SHA-bound. Validation 2021-2024 and every 2025+ payload stayed sealed.

## Economics

| Metric | Gross | x1 cost | x1.5 cost | x2 cost |
|---|---:|---:|---:|---:|
| Primary PF | 1.136519 | 0.968723 | 0.894502 | 0.826053 |
| Primary expectancy, pips/trade | +1.201312 | -0.298688 | -1.048688 | -1.798688 |

- Total primary pips: `+1,556.9` gross versus `-387.1` at x1 cost.
- Reverse x1 PF: `0.749592`; the source-ranked direction clearly beat reverse.
- Positive x1 years: `2/5`.
- One-sided random-sign p-value: `0.045395` (passes the preregistered 5% gate).
- Eight-arm DSR: `0.000269`.
- Economic gates: `2/8` (sign-flip significance and reverse comparison only).

Annual x1 PF was `0.9180`, `0.9929`, `1.0183`, `0.8672`, and `1.0031` from
2016 through 2020. Thus even the positive years were nearly flat rather than
close to the `1.30` target. Wednesday x1 PF was `1.3479`, and several months
looked positive, but those are post-outcome anatomy and cannot be converted
into a same-family rescue or veto under this ID.

## Why it failed

The primary-source ranking added useful signal: gross PF improved from the
USDJPY cell's `1.0512` to `1.1365`, gross expectancy improved to `+1.2013`
pips/trade, and the random-sign test crossed 5%. It still failed the Owner's
economic target because:

1. frozen x1 cost (`1.50` pips) was `1.25x` the mean gross effect;
2. x1 PF remained below one and all three cost PF gates failed;
3. only two years were positive, and both were essentially flat;
4. DSR remained near zero after eight declared arms;
5. the worst and best 1% contributed `-1,146.6` and `+1,233.9` x1 pips,
   respectively—no asymmetric tail explains a hidden robust survivor.

This is evidence that the unconditional daily EURUSD leg is too weak for the
required retail-cost proxy, not evidence that the institutional fix mechanism
does not exist.

## Failure radius and next legal mechanism

Killed exactly: EURUSD, FivePercent completed-Bid M1 close-only DESIGN
2016-2020, Europe/Berlin `07:59` to `14:14`, always short, every complete
weekday, no filter, fixed 1.50/2.25/3.00-pip costs, matched reverse.

Forbidden rescue: choosing Wednesday, February/March/July/October, shifting the
clock, reducing cost, changing direction, adding a stop/target, or accessing
validation/holdout.

The same paper independently preregisters a mechanism-level conditional claim:
fix reversal returns are stronger when intermediary constraints/market
volatility are high, using lagged VIX. A fresh hypothesis may therefore combine
the same source-ranked EURUSD direction with a **pre-entry, external lagged-VIX
high-volatility state**. That requires a new ID and a hash-bound VIX data
contract. It must not use current weekday/month/year outcomes or tune a
threshold from current returns.

## Bound evidence

- Plan SHA256: `D8585C793F0F742D96471BC25330F0368714CCCD1E1E66DEAF4AA79C2A242B4C`
- Armed evaluator SHA256: `0FB3FF4AE1326958FC911B7228DF9AF8526201A9506EF97C6DAFF7E9FBA9BFEE`
- Test SHA256: `7B477164AED038F582213CCE3DBD381D53F15EF904772F783428B9956D3DC63E`
- Authority row SHA256: `A9F887EBEC45DA4CC760C9E79473CE84EDC95BFDF0DA4AD650F8690D693F2B5C`
- Attempt-start SHA256: `8BCB79E331D99F33B81D23395655CF507D3BB555BD0F4E1372E755A3A79CC468`
- Trade ledger SHA256: `204050AAA213DB1BC468FD022733425DC3E2E70EF33A742A0A7D620EF8B166E8`
- Terminal SHA256: `123B2C209A18AF35506D0CFA876793FCC18094AA643C9EFBA50C3753E40F848D`
- Diagnostic chart SHA256: `2D0D232F3F90B8C89D07B4E4D3A2E06CC6F77C9A275227E549DDBF1A64E14854`
