# CME EUR/USD Options Acquisition Contract

Date: 2026-07-16

Owner decision: option `1` approved; retain the dataset inside
`D:\Trading EA MT5`.

Status: `DATABENTO_ACCOUNT_REGISTERED_API_KEY_NOT_CONFIGURED`

## Databento amendment (frozen before any paid request)

The Owner registered a Databento account on 2026-07-16. Acquisition now uses
the licensed `GLBX.MDP3` historical API instead of scraping or ordering through
CME DataMine. The account registration is not evidence that an entitlement or
historical request succeeded; those claims require API readback.

The paid request is limited to point-in-time `definition` and `statistics`
records for the official EUR/USD option parent families plus `6E.FUT`, over
`2020-01-02` through `2026-06-30`. Definitions supply strike, expiry, put/call,
underlying, scaling, and the exact listing timeline. Statistics supply exchange
settlement, cleared volume, and open interest with publication timestamps.

Databento does not expose the CME CVOL benchmark as a required field of
`GLBX.MDP3`. Therefore the six CVOL codes remain an optional licensed
cross-check, not a raw-data gate. Implied volatility, skew, term structure, and
convexity must be derived later from the causally joined option/futures
settlements under a separately frozen feature contract. This amendment occurs
before any option outcomes were retrieved and does not reopen DRAT-001.

Cost safety is fail-closed:

```powershell
& "02. AlphaFactory/runtime/python-databento/Scripts/python.exe" `
  "02. AlphaFactory/tools/databento_fx_options_acquire.py" plan
```

`plan` uses only free metadata/symbology calls. A paid batch submission requires
an explicit Owner ceiling via `submit --approve-max-usd <USD>` and re-estimates
the live cost immediately before submission. The API key is never persisted in
the repository, plan, job manifest, or logs.

This contract reopens external-data acquisition only. It does not reopen the
killed `HYP-DRAT-ONNX-ICT-M15-EUR-001`, authorize a replacement hypothesis, or
permit EA source/ONNX/Strategy Tester work before the data gate passes.

## Licensed data order

Acquire a one-time historical CME DataMine delivery for internal research with
both parts below.

### A. EUR/USD options-implied benchmark state

- Dataset family: CME Group CVOL Daily Benchmarks.
- Underlying: EUR/USD options on futures.
- Required series: `EUVL`, `EUUP`, `EUDN`, `EUSK`, `EUAM`, `EUCV`.
- Meaning: 30-day CVOL, up variance, down variance, skew, ATM volatility, and
  convexity.
- Coverage: `2020-01-02` through `2026-06-30`, inclusive.
- Preferred format: CSV with a trade/valuation date and one column per series.

### B. Full EUR/USD option chain history

- Product family: CME Euro FX / EUR/USD options on futures.
- Coverage: `2020-01-02` through `2026-06-30`, inclusive.
- Granularity: one row per trade date, expiration, strike, and put/call.
- Required logical fields:
  - trade date;
  - expiration;
  - strike;
  - option type (put/call);
  - settlement price;
  - volume;
  - open interest;
  - implied volatility.
- Required metadata: product/contract identifier, currency/price scaling,
  publication/finalization rule, missing-value semantics, and data dictionary.
- Preferred format: CSV or ZIP containing CSV plus the data dictionary.

CVOL alone is insufficient for `CONTRACT_READY`; the full chain is required so
the future hypothesis can distinguish level, skew/term structure, and actual
position/liquidity state without synthesizing open interest.

## Causal availability rule

- Use only final daily values.
- Record the official publication/finalization convention from the licensed
  data dictionary.
- A value may affect the EA only on the first EURUSD decision bar whose open
  occurs after that value was officially available.
- CME web pages state that displayed open interest can refer to the previous
  trading day; the future normalization must preserve this lag rather than
  relabel it as same-day information.

## Workspace storage

Raw and generated datasets stay under the ignored, machine-local directory:

```text
02. AlphaFactory/external/cme_fx_options_euro/
  raw/
    cvol/
    option_chain/
    documentation/
  acquisition_manifest.json
  normalized/              # created only after raw validation
```

No corpus, extraction scratch, training cache, or backtest log is to be retained
on `C:`. Raw files are immutable after delivery. Every file is hashed before
normalization.

## Fail-closed inventory

Run:

```powershell
python "02. AlphaFactory/tools/cme_fx_options_inventory.py" `
  --root "02. AlphaFactory/external/cme_fx_options_euro"
```

The tool returns `CONTRACT_READY` only when both CVOL components and full option
chain schema cover the frozen period. Any other state blocks outcome inspection,
hypothesis registration, feature engineering, ONNX training, and EA build.

## Access result this session

- Direct scripted retrieval was rejected by CME with an explicit automated-
  access/Data-Terms message; no scraping workaround is permitted.
- QuikStrike Option Settlements requires CME Group login.
- DataMine historical access requires account/login, license agreement, and an
  order.
- No controllable browser backend was available in this session, so the order
  could not be completed on the Owner's behalf.

Official sources:

- https://www.cmegroup.com/datamine.html
- https://www.cmegroup.com/market-data/cme-group-benchmark-administration/cme-group-volatility-indexes.html
- https://www.cmegroup.com/market-data/cme-group-benchmark-administration/files/cvol-methodology.pdf
- https://www.cmegroup.com/tools-information/quikstrike/option-settlement.html
- https://www.cmegroup.com/trading/about-settlements.html

Next external action: Owner signs in to CME DataMine and places/downloads the
two-part one-time order, or enables a controllable signed-in browser session.
Files must be saved directly into the workspace `raw/` subdirectories above.
