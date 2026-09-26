# WEB_RESEARCH_C1 — public evidence for the perception engine (Lead, 22/09 04:33Z)

The Owner asked for this at 04:17Z: "read more material online". A research agent ran about 15 searches and read about 10 pages. Every source below was opened, except the one marked "abstract only". Lanes take items from here only through the same-hash A/B and the keep-rule (R34 §34.5, R37 §37.6).

## Bottom line
- **There is no new Volman answer key.** He published only the two books; there is no website, forum or video material with dated charts from him. The 198 TUNE panels remain our only expert answer key.
- **Experts agree poorly even on horizontal levels.** In Osler (2000), six firms published daily FX support/resistance levels. Only about 30% of possible matches between firms occurred, even with a ±5-point tolerance (pairs ranged from 13% to 38%). So the ceiling for matching ONE expert's single level at a tight tolerance may be far below .5. End thresholds must come from our own human-ceiling check (R34 §34.6), not from intuition.
- **Round numbers are the best-documented trait of human-drawn FX levels.** In Osler (2000), over 70% of published levels end in 0 and 96% end in 0 or 5. The levels bounced more often than arbitrary levels (60.8% vs 56.2%), and the firms' own "strength" ratings had no predictive value.

## Findings by question
**Extra answer keys**
- ForexFactory thread "Understanding Price Action by Bob Volman (notes and examples)", started 2018. Amateurs post marked-up 5-minute charts in his style; Volman does not take part. At best it is a weak outside check inside DESIGN years, and it is not an answer key. It is not used without the Owner's OK. https://www.forexfactory.com/thread/733640-understanding-price-action-by-bob-volman-notes-and
- No public dataset of human-drawn S/R levels, ranges or trendlines exists. Osler's firm data (1996–98) is not public. https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf

**Box and range proposals**
- **TradingView "Support & Resistance KDE":** a density over pivots, where each pivot's kernel is as wide as that bar's high–low range. It ranks density peaks and merges peaks closer than a multiple of ATR. Fed with every wick tip instead of pivots, it can reach lone spikes and mid-band "eye-level" prices, which are exactly our missing box edges. https://it.tradingview.com/script/4XYcYFbA-Support-Resistance-KDE
- **etnfrank/support_resistance:** agglomerative clustering on raw highs and lows, not only on pivots. https://github.com/etnfrank/support_resistance (WTFPL)
- **py-market-profile:** point of control and value-area edges as mid-band candidates; FX has only tick volume, so check how it bins first. https://github.com/bfolkens/py-market-profile (BSD)
- **ruptures** (change points) proposes where a box starts and ends, not where its edges go. https://github.com/deepcharles/ruptures (BSD-2)

**Level ranking**
- **Garzarelli et al. 2014:** the chance of a bounce rises with the number of earlier bounces, and the tolerance scales with the typical move at that time scale. https://www.nature.com/articles/srep04487
- **Chung & Bellotti 2021** (intraday): levels with more earlier bounces bounce more, and the effect fades with the level's age. https://arxiv.org/abs/2101.07410
- **Osler 2003, JF** (abstract only): take-profits cluster at round numbers and stop-losses just beyond them. So price tends to reverse at round numbers and accelerate after crossing them, which explains true and false breaks there. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=447361
- No paper covers choosing ONE level at a time. Tools show the top N after a spacing filter.

**Trendlines**
- **neurotrader888:** one tight line per side per window, anchored on the most extreme pivot and fitted so it never crosses price. https://github.com/neurotrader888/TechnicalAnalysisAutomation (MIT)
- **pytrendline:** lines through pairs of pivots; drops lines that cut candle bodies, merges near-duplicates and keeps the best of each group. https://github.com/ednunezg/pytrendline (MIT)
- **trendln:** a test bench of generators (3-point, 2-point, Hough). https://github.com/GregoryMorse/trendln (MIT)
- A Hough transform on its own gives 22–31 lines per chart and has never been compared with human drawings (Jitpakdee & Pravithana 2017).

## Lead routing (formal in the next ruling)
1. **Build — levels (coverage is the blocker, R37 §37.4).**
   - First measure, 10 minutes, on TUNE: what share of the author's LEVEL_CARRIED, MINI_LEVEL and box edges lie within 1–2 pips of a 00 or 50 price?
   - If the share is high, add round-number LC candidates behind a flag, with a rank bonus, and A/B.
   - Then score levels by touches (tolerance scaled with ABR) × recency decay, with the defended-origin route ON.
2. **BOX-LAB — the 4th edge source it listed as remaining:** a wick-tip density (KDE) edge generator, kernel width = bar range, peaks merged within an ABR-scaled spacing. Report the engine box oracle and box@1 as usual.
3. **Build — lines (after levels):** a pytrendline-style duplicate merge before the 2-line budget; the neurotrader888 one-line-per-side fit as an arm.
4. **EVAL-AUDIT — human ceiling (R34 §34.6):**
   - put Osler's 30% (13–38%) inter-firm agreement in the protocol as prior evidence;
   - propose the smallest panel set that gives a usable ceiling.
5. **SCALE:** report what share of the engine's levels sit on 00/50 at scale, next to the author's share on TUNE.

Not taken: a learned ranker trained on 198 panels (too few answer keys; the agent rated the evidence weak), and forum screenshots (not without the Owner's OK).
