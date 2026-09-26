# pat_Q10auto.json

Q: Object: PATTERN MARKS. Q10+AUTOMATION: Where do the experts in this corpus DISAGREE about pattern definitions, and which pattern rules are mechanical enough to automate causally (Lo-Mamaysky-Wang kernel method, Bulkowski identification guidelines)? Cite sources.

### Key Disagreements Among Experts on Pattern Definitions

Experts in this corpus disagree sharply on the validity, geometry, drawing techniques, and confirmation rules of technical chart patterns.

#### 1. Diagonal Trendlines vs. Horizontal Boundaries
* **Peter Brandt** strongly warns against diagonal chart constructions (trendlines, symmetrical triangles, wedges), labeling trendlines "the most unreliable diagonal chart construction" [1]. He notes that violating a trendline carries no price target or guaranteed direction shift [2], restricts his analysis primarily to horizontal boundaries [3, 4], and jokes that "an ape with a ruler" can draw trendlines [5].
* **Support And Resistance Trading** agrees, declaring trendlines to be "the weakest form of S/R" due to subjective anchor selection, and notes having eliminated them for trade entries in favor of horizontal zones [6].
* **Adam Grimes** defends standard trendlines but acknowledges they are "the most used and abused tool" [7]. He provides strict parameters: an uptrend line must connect successive higher lows without cutting through prices, and must connect a pivot low to a pivot low preceding a new trend high [8-10].
* **Al Brooks** relies heavily on trendlines, trend channels, and "micro trend lines" (2 to 10 bars) across all timeframes to gauge market strength and identify flag setups [11, 12].
* **Tom DeMark** rejects subjective drawing entirely, substituting manual line fitting with mathematical, automated **TD Lines** [13].

#### 2. Geometry: Candle Wicks vs. Body Closes & Lines vs. Zones
* **Adam Grimes** explicitly calls drawing trendlines through candle shadows/wicks or bodies a "sloppy practice" that invalidates the support/resistance reference [9].
* **Al Brooks** explicitly permits and recommends drawing trendlines using candle bodies rather than wicks in strong trend environments [11].
* **Support And Resistance Trading** uses candle body closes as the primary reference level for horizontal levels, utilizing wicks strictly to define the outer boundary [14].
* **Rayner Teo & ChartMini Blog** view support/resistance as flexible **zones** rather than single lines [15-17]. Teo adjusts lines to capture the maximum number of touches across bodies or wicks [18], while ChartMini formalizes a two-layer definition separating a "core" (closes/bodies) from an outer "envelope" (wicks) [19, 20].

#### 3. Pattern Confirmation vs. Dynamic Structure
* **Thomas Bulkowski** defines chart patterns through rigid quantitative filters and insists that a pattern is **not valid** until confirmed by a price close above the intervening peak [21, 22]. Without this breakout confirmation, unconfirmed formations are merely "squiggles on a chart" with a high failure rate [21, 22].
* **Lo, Mamaysky, and Wang (LMW)** define pattern occurrence algorithmically at the instant the final local extremum completes based on price proximity and temporal separation [23, 24], evaluating conditional returns immediately following pattern completion rather than waiting for a breakout.
* **Wyckoff Method (StoicFX)** rejects fixed static geometric definitions altogether. Wyckoff's Rule 1 states that *"The Market and Individual Securities Never Behave in the Same Way Twice"* [25]; accumulation and distribution patterns are dynamic, shapeshifting structures with infinite variations that cannot be trapped in rigid geometric rules [25, 26].

---

### Mechanical Pattern Rules for Causal Automation

Several frameworks in the corpus provide objective mathematical rules that can be coded into automated algorithms without human subjectivity:

```
                  ┌─────────────────────────────────────────┐
                  │      RAW PRICE TIME SERIES (P_t)        │
                  └────────────────────┬────────────────────┘
                                       │
                         [Rolling Window Filtering]
                                       │
                  ┌────────────────────▼────────────────────┐
                  │    KERNEL REGRESSION SMOOTHING m̂_h(t)   │
                  └────────────────────┬────────────────────┘
                                       │
                        [Derivative Sign Changes]
                                       │
                  ┌────────────────────▼────────────────────┐
                  │       LOCAL EXTREMA (E_1...E_n)         │
                  └────────────────────┬────────────────────┘
                                       │
                        [Deterministic Inequality Check]
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼────────┐             ┌───────▼────────┐             ┌───────▼────────┐
│ Double Bottom  │             │   Rectangle    │             │   Broadening   │
│  |E1-Eb| ≤1.5% │             │ Tops/Bottoms   │             │  Tops/Bottoms  │
│ Δt ≥ 22 Days   │             │ Tops/Bots ≤.75%│             │ E1 < E3 < E5   │
└────────────────┘             └────────────────┘             └────────────────┘
```

#### 1. Lo-Mamaysky-Wang (LMW) Kernel Smoothing Method
Lo, Mamaysky, and Wang automate classical pattern recognition using nonparametric kernel regression [27, 28]:
* **Smoothing Estimator**: Fits a kernel regression \\(\hat{m}_h(t)\\) over rolling time windows (e.g., \\(l + d = 38\\) trading days) to filter out high-frequency white noise \\(\epsilon_t\\) [24, 28, 29].
* **Derivative Zero-Crossings**: Evaluates the continuous first derivative \\(\hat{m}_h'(t)\\) and identifies local extrema at points where the derivative changes sign (\\(Sgn(\hat{m}_h'(t)) = -Sgn(\hat{m}_h'(t+1))\\)) [29]. These smoothed extrema are then mapped to local extrema in raw prices [30].
* **Deterministic Inequality Rules**:
  * **Double Tops / Bottoms (DTOP / DBOT)**: Identifies an initial extremum \\(E_1\\) and a subsequent extremum \\(E_a\\) or \\(E_b\\) such that the two tops/bottoms are within **1.5% of their average price** and separated by at least **22 trading days** (\\(\Delta t \ge 22\\)) [23, 24].
  * **Rectangle Tops / Bottoms (RTOP / RBOT)**: Identifies 5 consecutive extrema (\\(E_1, \dots, E_5\\)) where all local tops and all local bottoms fall within **0.75% of their respective averages** [23].
  * **Broadening Tops / Bottoms (BTOP / BBOT)**: Identifies 5 consecutive extrema with expanding highs and lows (\\(E_1 < E_3 < E_5\\) and \\(E_2 > E_4\\) for tops) [31].

#### 2. Bulkowski Identification & Confirmation Guidelines
Bulkowski’s guidelines convert chart patterns into programmatic parameters [21]:
* **Metric Filters**: Valleys must bottom near the same price level; the intervening peak must represent at least a **10% price rise** from the lowest valley [21].
* **Shape Classification**: Programmatically distinguishes narrow, sharp V-shaped spikes (Adam) from wide, rounded multi-bar troughs (Eve) [21].
* **Causal Trigger**: Automation rules trigger a valid breakout signal **only when price completes a daily close above the highest peak** between the two valleys [21, 22].

#### 3. Tom DeMark (TD Lines)
DeMark replaces manual trendlines with fully algorithmic **TD Points** [13]:
* **Level-\\(N\\) TD Points**: A Level 1 TD Point High requires a bar high flanked by 1 preceding bar and 1 succeeding bar with lower highs (3 bars total) [13]. A Level-\\(N\\) TD Point requires \\(N\\) preceding and \\(N\\) succeeding bars with lower highs (or higher lows for TD Point Lows) [13].
* **Automated Line & Breakout Qualification**: Trendlines connect active TD Points, and breakouts are automatically classified as qualified (solid line) or disqualified (dashed line) via mathematical criteria [13].

#### 4. Algorithmic Market Structure (SMC / LuxAlgo)
* **Lookback Extremal Windows**: Scans for swing highs and lows using fixed lookback periods (e.g., 5–49 bars for internal structure, 50–100 bars for swing structure) [32].
* **Causal Event Rules**:
  * **Change of Character (CHoCH)**: Programmatically triggers when price breaks a prior swing low during an uptrend or prior swing high during a downtrend [32].
  * **Break of Structure (BOS)**: Programmatically triggers when price breaks a prior swing high during an uptrend or prior swing low during a downtrend [32].

---

Would you like to explore building an automated Python backtest for one of these mechanical frameworks (such as LMW kernel regression or DeMark TD Lines)?

## CITED SOURCES
- [1] src=216c23c3: The most unreliable diagonal chart construction is the trendline, followed closely by the symmetrical triangle. Do NOT read this to mean that diagonal patterns do not produce profitable trades. I have experienced some wonderful trades involving diagonal chart construction. In fact, over the years ma
- [2] src=216c23c3: · Horns (or sloping patterns) · Compound fulcrums (borrowed from point and figure charting) · Rounding patterns Diagonal chart construction · Head and shoulders – when the neckline slants into the right shoulder · Symmetrical triangles · Right-angled triangles – when the breakout is through the diag
- [3] src=cc06b1a5: a futures stock or forex cross chances are I've drawn too many lines i get comments all the time about my markings and charts being oversimplified i take that as a as as a great compliment the most reliable chart patterns tend to be those that require more than 12 weeks to form i want to see a marke
- [4] src=cc06b1a5: u and make money as patterns as a day trader all the more power to you uh patterns on weekly charts I find are the most reliable and horizontal patterns are far more reliable than diagonal patterns now there's some reason for that i'm not going to go into that in this webinar but there are some spec
- [5] src=cc06b1a5: ude trend lines i don't use trend lines uh you know G here now I know some traders who make money trading trend lines and so you know I want to give them uh I I I want to give them the nod and say "Congratulations you can do it." But in my own way of thinking you give a chart book a ruler and a penc
- [6] src=2ae36cf5: Trendlines are the weakest form of S/R in my experience. Drawing a trendline requires at least two swing points, and different traders will connect different points. That subjectivity means less order concentration at the level. I stopped using trendlines for entries about two years ago. I still dra
- [7] src=65c415d9: Trendlines are perhaps the most used and abused tool in modern technical analysis. It is difficult to even come up with a precise definition of a trendline, or with firm rules for where and how to draw them. One good working definition is that a trendline is a line drawn between two points on a char
- [8] src=65c415d9: Standard trendlines Standard uptrend lines are drawn between higher lows in an uptrend; the standard downtrend line is a line drawn between lower highs in a downtrend. The uptrend line shows where buyers have stepped in on the declines with additional demand and have bid the market higher, which is 
- [9] src=65c415d9: "Nonstandard" trendlines in the XLF. Don't "cut" prices There is a debate among traders and analysts about whether trendlines should cut through prices, as shown in the next chart and example B of the chart above . Of course, you can draw any line you want to and there are good arguments to be made 
- [10] src=cb3c4375: Why does this trendline end? Because price action at the end of 2016 invalidated the line. The line was broken decisively, and once a line is cut or broken we don't have any good reason to expect it to be meaningful in the future. (In other words, it's a mistake to carry this line forward.) Now look
- [11] src=e544c5e4: flat the trend line is when the trend line breaks we can use this to gauge the strength of the other side counter Trend Traders sometimes it's better to use the bodies of the candles to draw trend lines here's an example of multiple trend lines we have broad bull trend lines here and here and then w
- [12] src=e544c5e4: multiple trend lines that also contain bearish price action micro trend lines small steep trend lines and strong Trends a micro trend line can be drawn on any time frame it's a smaller trend line drawn between two and 10 bars within a bigger Trend when a micro trend line has a false breakout this ca
- [13] src=283dd470: TD Lines™ TD Lines™ TD Lines are mechanically and objectively constructed. The trendlines drawn are TD Supply Lines and TD Demand Lines. Once the TD Lines are broken and qualified, the study automatically calculates a price projection. A qualified breakout appears as a solid line; whereas, a disqual
- [14] src=2ae36cf5: My rules for drawing S/R: Use the body close of candles as the primary reference, not wicks. Wicks show the extreme, but closes show where price actually settled. I mark the zone using the cluster of closes, then extend the zone to capture the worst wick. Draw zones, not lines. I use a rectangle too
- [15] src=35993b7d: My approach to drawing Support and Resistance uses either 1 line or 2 lines. It is much cleaner and immediately tells you which area of the chart to pay attention to. I use a single line when price respect a level almost to the pip and i use 2 lines when price bounces off an area. I highlight only t
- [16] src=35993b7d: Reply nmesoma says: December 21, 2015 at 12:39 am For the example of the second last picture, why do you choose to have 2 SR lines for some areas but only 1 SR line for other areas? Do you Draw the SR line at the Top of the wick? at the close of the candle? How do you decide which is more accurate? 
- [17] src=7e0b3a3d: A zone can be based on: several swing highs or swing lows; a cluster of closes; overlapping candle bodies; a wick envelope around a narrower body or close cluster; the edge of a range or consolidation; a gap, session, auction, settlement, or other clearly identified price boundary; a calculated refe
- [18] src=a45cd69d: Zoom out your charts (at least 200 bars for me) Draw the most obvious levels (if you need to second guess, then it's not an important level) Adjust your levels to get the most number of “touches” (it can be body or wick) Now, if you want a full training on how to draw Support and Resistance, then ch
- [19] src=7e0b3a3d: <cited_table>
- [20] src=7e0b3a3d: Before using this method, define whether all wicks qualify or whether an anomaly rule excludes specific observations. Method 4: Core plus wick envelope Create two related bands: Core: close cluster or body range. Envelope: qualifying wick extremes. This method preserves more information than forcing
- [21] src=7360ee4d: Adam & Eve Double Bottoms: Bull Market Results Overall performance rank (1 is best): 17 out of 39   Break even failure rate: 12%   Average rise: 43%   Throwback rate: 67%   Percentage meeting price target: 69% The above numbers are based on 1,020 perfect trades. See the glossary for definitions. Sco
- [22] src=7360ee4d: More Adam & Eve Double Bottoms: Trading Tips A trading setup related to double bottoms and throwbacks is located here . Trading Tactic Explanation   Measure Rule for Adam & Eve Double Bottoms Measure rule The link to the left gives more information about the measure rule. Compute the height from the
- [23] src=1a586e7f: lowest top . highest bottom, 7 After all, for two consecutive maxima to be local maxima, there must be a local minimum in between and vice versa for two consecutive minima. Foundations of Technical Analysis 1717 RBOT [ 5 E1 is a minimum tops are within 0.75 percent of their average bottoms are withi
- [24] src=1a586e7f: Definition 5 (Double Top and Bottom) Double tops ~DTOP! and bottoms ~DBOT! are characterized by an initial local extremum E1 and subsequent local extrema Ea and Eb such that Ea [ sup $Ptk * : tk * . t1 * , k 5 2, . . . , n% Eb [ inf $Ptk * : tk * . t1 * , k 5 2, . . . , n% and DTOP [ 5 E1 is a maxim
- [25] src=b0799ea5: Understanding Wyckoff’s Market Rules These rules are derived from Wyckoff’s studies and experience charting the stock market. Rule 1: The Market and Individual Securities Never Behave in the Same Way Twice Rather, trends unfold through a broad array of similar price patterns that show infinite varia
- [26] src=5c67f357: Selling Climax Spring Sign of Strength Last Point of Support Reaccumulation Continuation Accumulation Schematics Not every accumulation range follows the textbook. Wyckoff documented multiple variations to account for ranges that skip events, repeat phases, or resolve differently. Schematic 1: Class
- [27] src=1a586e7f: Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation ANDREW W. LO, HARRY MAMAYSKY, AND JIANG WANG* ABSTRACT Technical analysis, also known as “charting,” has been a part of financial practice for many decades, but this discipline has not re
- [28] src=1a586e7f: I. Smoothing Estimators and Kernel Regression The starting point for any study of technical analysis is the recognition that prices evolve in a nonlinear fashion over time and that the nonlinearities contain certain regularities or patterns. To capture such regularities quantitatively, we begin by a
- [29] src=1a586e7f: Within each window, we estimate a kernel regression using the prices in that window, hence: [mh~t! 5 ( s5t t1l1d21 Kh~t 2 s!Ps ( s5t t1l1d21 Kh~t 2 s! , t 5 1, . . . ,T 2 l 2 d 1 1, ~14! where Kh~z! is given in equation ~10! and h is the bandwidth parameter ~see Sec. II.C!. It is clear that [mh~t! i
- [30] src=1a586e7f: function. If the signs of [mh ' ~t! and [mh ' ~t 1 1! are 11 and 21, respectively, then 8 If we are willing to place additional restrictions on m~{!, for example, linearity, we can obtain considerably more accurate inferences even for partially completed patterns in any fixed window. Foundations of 
- [31] src=1a586e7f: Because broadening, rectangle, and triangle patterns can begin on either a local maximum or minimum, we allow for both of these possibilities in our definitions by distinguishing between broadening tops and bottoms. Definition 2 (Broadening) Broadening tops ~BTOP! and bottoms ~BBOT! are characterize
- [32] src=3726d651: 