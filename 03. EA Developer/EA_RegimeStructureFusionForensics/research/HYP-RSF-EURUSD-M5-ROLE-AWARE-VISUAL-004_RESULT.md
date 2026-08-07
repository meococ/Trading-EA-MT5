# HYP-RSF-EURUSD-M5-ROLE-AWARE-VISUAL-004 — native paired-chart result

Status: `COMPLETED_DIAGNOSTIC_ONLY`

## Evidence contract

- Source economic run: `EA_RegimeStructureFusion/20260807_064845`.
- Replay EA: `EA_RegimeStructureFusionForensics`.
- EURUSD M5, MT5 Model 1, Visual Mode.
- Eight cases were frozen before replay: the best and worst result from each
  executed route. Replay P/L has no economic authority.
- Every chart is a full-window capture of the real portable MT5 Strategy Tester
  Visualization window. No chart was reconstructed or rendered from CSV data.
- All eight PNGs are `1906 x 1025`, have a valid PNG signature, and were copied
  by AlphaFactory into the matching run artifact with the same SHA-256.

## Paired visual diagnosis

| Pair | Losing chart | Winning chart | Mechanism difference visible on native MT5 |
|---|---|---|---|
| Breakout long | C01 buys a minor positive phase inside a larger bearish path; price is below the dominant structure and immediately resumes lower. | C02 enters during a persistent higher-high/higher-low path, rising basis and expanding bands, with room to the next external high. | Indicator agreement is insufficient. Directional structure and runway distinguish the pair. |
| Breakout short | C03 sells a small local break inside a larger rising path and is followed by bullish displacement. | C04 has a protected high and a fresh bearish BOS at the entry location, then clean downside continuation. | A closed structural event, not a band/QQE color, must arm the trade. |
| Trend long | C05 buys near a soft high after an extended recovery; basis is flat and the target sits beyond nearby liquidity. | C06 enters after a protected low, bullish BOS and continuation base; the next soft high supplies a visible objective. | Pullback/reclaim plus available room is materially different from late trend chasing. |
| Trend short | C07 sells after a prolonged decline into a protected low while an MSS/reversal is forming. | C08 sells below a protected high after bearish BOS, with clear room to the next soft low. | Exhaustion at opposing liquidity must veto continuation even when the prior trend is bearish. |

QQE is useful as a phase check but changes too frequently to be a causal trigger.
MBB is useful for slope, compression/expansion and entry-to-objective location.
AIRD/VRC are useful as hostile-state vetoes. TB structure supplies the only
event order that consistently separates the paired examples: protected level,
closed BOS/MSS or sweep/reclaim, then entry before the next liquidity objective.

The post-exit `Soft H/Soft L` labels are diagnostic hindsight and are not known
at entry. The successor may use only a live opposing swing already published on
the decision bar; otherwise its target remains the preregistered fixed-R target.

## Failure radius carried forward

The killed `ROLE-AWARE-003` mechanism must not be rescued by tuning QQE,
session, direction, year, band width or confidence thresholds. Its failure is
semantic: lagged indicator consensus is being treated as a forecast. The next
economic trial must use a fresh hypothesis and a new causal event:

1. A closed-bar TB structural event arms one direction.
2. A retest/reclaim must occur before expiry; no same-bar breakout entry.
3. The entry must not be at opposing protected/soft liquidity.
4. The available structural objective must cover the frozen minimum reward.
5. AIRD/VRC can veto ambiguity or hostile volatility; QQE cannot delay the
   entry into a late zero-cross consensus.

## Native chart manifest

| Case | Source result | Alpha run | SHA-256 |
|---|---:|---|---|
| C01 Breakout Long loss | -1.1159R | `20260807_072716` | `B8D6FEE3AF77B6862ABED4197C446AD66867410A5CC60EB192165F4F4E16D0AD` |
| C02 Breakout Long win | +1.4559R | `20260807_072915` | `E0FF826F5A150D7F62012EBB482831D2E28C71D53159410F71AAFFF723974C79` |
| C03 Breakout Short loss | -1.0862R | `20260807_073102` | `34F15A4187C0CE04C48529D5EFE4ACBBD3914B54C9ECC95F2B8590BCE21C387E` |
| C04 Breakout Short win | +1.4394R | `20260807_073256` | `130321DC27B0024ADFD83A89F02967D9B1DDA121B4A053D81692C4F54CB80296` |
| C05 Trend Long loss | -1.1343R | `20260807_073447` | `29E27B53E279DF5647D7C1949D24584FB52610771B05DDEC2A712C81B9541A21` |
| C06 Trend Long win | +1.4894R | `20260807_073630` | `67513378C31B0EF39069F295930047C26DEF9AF3BF918068D4F7573F82D770A4` |
| C07 Trend Short loss | -1.0588R | `20260807_073820` | `3517FD6B2DF73639B6E594140C2A42AA478351ABAE30C6AA45988C21863B746D` |
| C08 Trend Short win | +1.4905R | `20260807_074013` | `313E84110B2930C9EE0689442AF80BE9FCBFD86B7E35B35FFB05334062F8B3EC` |

Engineering-valid: yes. Economic-valid: not applicable. Promotion-ready: no.
