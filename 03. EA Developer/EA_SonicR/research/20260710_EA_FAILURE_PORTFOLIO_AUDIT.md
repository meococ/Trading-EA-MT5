# EA Failure Portfolio Audit

Date: 2026-07-10

Verdict: `FRONTIER_REACHED` for the current Sonic field/symbol space.

## Scope And Authority

This audit reviewed the local AlphaFactory catalog, per-run artifacts, current
Sonic control docs, the restored doctrine-canonical 51-row registry, and the
preserved 2026-07-04 verdict ledger snapshot. The SQLite catalog is an index;
all decisive claims below were checked against run-local artifacts or the
preserved verdict snapshot.

Physical/run-identity coverage:

- `218` non-empty physical run directories exist across `34` EAs;
- one directory is excluded from performance counts as identity-corrupt:
  `EA_ITSM/20260621_170259` declares `ea_name=EA_ITSM`, but its `config.ini`
  executes `EA_LondonNY.ex5` and its report/config hashes are byte-identical to
  `EA_LondonNY/20260621_170259`. The shared timestamp `run_id` also collides in
  the SQLite catalog, whose old key is not EA-qualified;
- the analytic population is therefore `217` identity-valid non-empty runs.

Analytic-population coverage:

- `217` non-empty runs across `34` EAs;
- `64` runs with PF above `1.30`, all below `2` trades/week;
- `15` runs inside `2-5` trades/week, all with PF at or below `1.30`;
- `0` runs satisfying both target conditions.

The denominator is elapsed calendar time, including inactive weeks:

```text
elapsed_weeks = (ToDate - FromDate).days / 7
trades_per_week = unique_completed_positions / elapsed_weeks
```

Active-week/month denominators and rounded trades/year are invalid for the
current target. For example, SilverBullet run `20260628_131343` has `520`
completed positions over about `260.86` weeks, or `1.993` trades/week, not a
clean pass at `2.0`.

## Failure Taxonomy

| Failure class | Evidence-backed finding |
|---|---|
| Sparsity | Every run with PF above target misses the lower cadence bound. LondonNY, Cobra, and ITSM are roughly `0.27`, `0.50`, and `0.87` trades/week. |
| Data/cost illusion | `176/217` runs have no cost-stress artifact. Existing fixed `$0.50/trade` proxies do not prove symbol/lot spread, commission, swap, or slippage. |
| Slippage illusion | Of 69 slippage summaries, 28 are unavailable and 32 report zero absolute mean. Zero tester slippage is not live execution evidence. |
| Regime concentration | Sonic XAU 2024-2025 reaches PF `1.3976`, but the nominal 2021-2025 route falls to PF `1.1535`; the short seed is dominated by a small winning pocket. |
| Matched-control identity | None of the cataloged manifests contains the required hypothesis, source hash, input hash, Git status, and verifiable control/challenger linkage. |
| Multiple testing | Only one PBO artifact was found and no complete White Reality Check/SPA family artifact exists. The full tried family is therefore untaxed. |
| False validation | `42/69` stored validation summaries say `PASS`, but 14 of those runs have PF at or below `1` and non-positive net. Older PASS states mostly prove child tools executed. |
| Equity quality | Of 49 equity audits, only two pass; the rest are `WARN`, `FAIL`, or `REJECT`. |
| Duplicate evidence | Identity-valid rerun directories remain visible in the population but do not count as independent confirmation, including SilverBullet `20260628_131532`/`20260628_131720` and SonicR `20260701_163205`/`20260705_022757`. The cross-EA `20260621_170259` identity collision is excluded entirely. |
| Execution-policy mismatch | `18/69` audited runs fail the no-overnight policy. SilverBullet `20260628_131343` holds `22.69%` overnight and crosses three weekends. |

## Project Findings

### EA_SonicR

The best short-window Model 0 seed, `20260701_134204`, has `127` trades,
PF `1.3976`, net `$773.33`, and about `1.23` trades/week. It is not a survivor:

- stored validation is `REVIEW 3/6`;
- robustness pass rate is `57.1%`, below `60%`;
- PBO and White Reality Check are missing;
- equity audit is `REJECT`;
- top 5% of trades contribute about `199.9%` of total profit;
- the largest trade contributes `42%` of total profit;
- slippage reconciliation has `open_ack_minus_fill_gap=-127`.

The longer nominally same route, `20260701_163205` / duplicate
`20260705_022757`, has `335` trades and PF `1.1535`. The current XAU route is a
favorable-regime pocket, not a robust backbone.

Trader-thesis failures are also closed:

- generic sideway/range, compression breakout, retest, and context-rescue
  families failed;
- EUR Asian manipulation reached `2.21` trades/week but cost PF was `1.078`
  and year concentration failed;
- GBP value drift to EMA89 had insufficient runway and holdout cost PF about
  `0.817`;
- XAU ATR filtering improved PF by deleting roughly 90% of cadence;
- Dragon/Trend distance preserved cadence but removed the decisive impulse
  winners.

No new rescue filter is authorized from the same fields or holdout periods.

### EA_SilverBullet

This is the closest historical cadence seed, not a current candidate.

- 2021-2025: PF `1.3255`, `1.993` trades/week;
- 2019-2025: PF `1.2594`, `1.936` trades/week;
- equity audit `WARN`, top 5% trades contribute `89.2%` of profit;
- no broker-calibrated cost proof for the near-boundary run;
- overnight exposure violates the scalp contract;
- the preserved The5ers transfer verdict is `KILL`: PF `1.018939`, cost x1.5
  PF `0.998852` over `785` trades.

It must not be tuned or promoted from the current evidence.

### EA_LondonNY

The preserved production verdict has strong quality: PF `1.960412`, holdout PF
`1.396754`, cost x1.5 PF `1.948376`, and Monte Carlo P95 DD about `3.20%`.
However, standalone cadence is about `0.3` trades/week. Cross-pair transfer
killed EURUSD, GBPUSD, and EURJPY; the surviving USDJPY+XAUUSD book remained
about `0.42` trades/week. It is a sparse sleeve, not the requested EA/book.

### Other Shelf Families

- ITSM: headline PF survived, but holdout PF `1.05484` and 2024-2025 decay
  triggered `KILL`.
- ChopRegime: the fresh untouched 2018-2020 OOS PF was `1.025976`; family
  verdict `KILL_FAMILY`.
- Gotobi: timezone correction did not rescue transfer; treatment PF `0.910317`.
- Spark: both configurations failed, PF about `1.00` and `0.93`.
- H4Ribbon: pooled PF about `0.357`.
- TrendBook: corrected implementation remained dead, portfolio PF about
  `0.496`.
- Gap-fill discovery: historical spread and rollover erased the apparent Stage
  1 edge; the compiled probe later produced PF `0.477`.

## Root Causes In The Development Process

The failures are not explained only by bad indicators. The process allowed:

- attractive PF to hide insufficient calendar cadence;
- short favorable windows to outrank longer falsification;
- zero/fixed costs to stand in for broker execution;
- exit-code success to masquerade as numeric validation;
- rerun duplicates to look like independent confirmation;
- missing source/input hashes and stale report fallback;
- a globally keyed timestamp `run_id` that can collapse or cross-wire two EAs;
- post-hoc rescue filters to consume holdouts.

The new process must therefore repair the evidence path before trying another
entry rule.

## Only De-Duplicated Research Opening

The existing Sonic feature frontier remains closed. One external research pivot,
`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`, survived intake de-duplication only
as an `idea`; it is not an EA candidate and is currently
`COST-DATA BLOCKED`.

It uses synchronized closed-M15 EURUSD, GBPUSD, and USDJPY returns to detect a
common USD impulse, ranks all three pairs, and permits one fixed Sonic
Classic pullback-break candidate. It is a cross-sectional router, not another
Asian-range, `CONTEXT_FAIL`, Dragon/Trend threshold, PVSRA standalone,
session/hour veto, or management-replay patch.

The distinction is deliberately narrow. S555 tried other-pair lead-lag, S618
tried same-bar consensus into fixed USDJPY, and S670 tried laggard catch-up.
The new idea selects the pair already expressing the factor most strongly and
waits for that pair's own pullback-break. Those three failed families are now
locked falsification controls. The idea is killed unless it materially beats
all three in train and one-time holdout.

Required sequence:

1. Restore and validate the control plane.
2. Use the frozen formula, zero-tuning budget, train/holdout, controls, and kill
   rules in the schema-valid preregistration.
3. Prove synchronized tick-derived bid/ask paths and broker-cost provenance.
4. Run an offline population probe only.
5. Patch no EA unless the frozen train and untouched holdout gates pass.

The preregistration exists at
`D:\Trading EA MT5\03. EA Developer\EA_SonicR\research\preregs\20260711_H_FX_CROSS_SECTIONAL_USD_FACTOR_001_PREREG.md`.
Historical bid/ask quote ticks, account commission, and same-broker P90
slippage provenance are still absent. The read-only broker audit found only
about `4%` non-zero M15 spread-field coverage in 2024-2025, two EURUSD
commission lifecycles, no GBPUSD or USDJPY commission samples, and zero usable
side-referenced slippage samples. Step 4 is therefore not authorized. See
`D:\Trading EA MT5\03. EA Developer\EA_SonicR\research\20260711_BROKER_COST_PROVENANCE_AUDIT.md`.

## External Mechanism And Liquidity Basis

The universe is commercially defensible, but the hypothesis is not externally
proven. The final 2025 BIS survey reports USD/EUR, USD/JPY, and USD/GBP as the
three largest currency pairs by global OTC turnover, with respective shares of
about `21.2%`, `14.3%`, and `7.6%` in April 2025:

- [BIS 2025 Triennial Survey, FX results](https://www.bis.org/statistics/rpfx25_fx.pdf)
- [BIS 2025 survey data portal](https://www.bis.org/statistics/rpfx25.htm)

Research on common currency factors supports testing a common-dollar state,
while macro-news and order-flow research supports treating information flow as
economically meaningful:

- [NBER: Identifying Exchange Rate Common Factors](https://www.nber.org/papers/w23726)
- [NBER: Micro Effects of Macro Announcements: Real-Time Price Discovery in Foreign Exchange](https://www.nber.org/papers/w8959)
- [NBER: How is Macro News Transmitted to Exchange Rates?](https://www.nber.org/papers/w9433)
- [NBER: Order Flow and Exchange Rate Dynamics](https://www.nber.org/papers/w7317)

These sources justify a falsifiable probe only. They do not establish that a
closed-M15 factor, strongest-pair router, or retail-CFD implementation has a
profitable edge after costs.

## Primary Local Evidence

- `D:\Trading EA MT5\02. AlphaFactory\runs\_progress_report_20260704\progress_report.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_ITSM\20260621_170259\run_manifest.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_ITSM\20260621_170259\config.ini`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_LondonNY\20260621_170259\run_manifest.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_LondonNY\20260621_170259\config.ini`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SonicR\20260701_134204\analysis\enhanced_summary.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SonicR\20260701_134204\analysis\validation_summary.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SonicR\20260701_134204\analysis\equity_audit.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SonicR\20260701_134204\analysis\slippage_summary.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SonicR\20260701_163205\analysis\enhanced_summary.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SilverBullet\20260628_131343\analysis\enhanced_summary.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SilverBullet\20260628_131343\analysis\equity_audit.json`
- `D:\Trading EA MT5\02. AlphaFactory\runs\EA_SilverBullet\20260628_131343\analysis\overnight_exposure.json`
- `D:\Trading EA MT5\03. EA Developer\EA_SonicR\research\CANDIDATE_REGISTRY.jsonl`
