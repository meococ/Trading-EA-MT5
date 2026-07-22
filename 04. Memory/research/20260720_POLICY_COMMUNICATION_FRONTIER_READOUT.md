# Policy-communication differential frontier readout

Date: 2026-07-20

Verdict: `NO_LEGAL_HISTORICAL_CANDIDATE`

This is a source-feasibility and de-duplication readout only. It does not open
a hypothesis, define a trading rule, authorize a price join, create an EA, or
permit a backtest.

## Candidate examined

The only materially independent free-data mechanism that survived the initial
idea screen was a Fed-versus-ECB monetary-policy communication differential for
EURUSD:

`policy-language innovation -> relative expected policy path -> EURUSD repricing`

It is independent of the terminal ICT/FVG/SMC family, OHLC trend/mean-reversion,
session drift, CFTC positioning, daily futures OI/volume, public SDR, prediction
markets, ETF/real-yield and cross-asset lead-lag objects.

## Gate result

### Source/PIT gate: FAIL

- The Federal Reserve speech archive is public, and many individual PDFs state
  `For release on delivery` with an exact time and timezone.
- The official ECB speech dataset is public and supplies the original
  publication **date**, title, speaker and text, but it is updated monthly and
  does not supply a historical `published_at` timestamp, timezone, immutable
  version identifier or correction lineage.
- The current ECB weekly schedule has event times, but a rolling current page is
  not a reproducible 2018--2025 first-publication/vintage archive.

Official sources:

- <https://www.ecb.europa.eu/press/key/html/downloads.en.html>
- <https://www.federalreserve.gov/newsevents/speech.htm>
- Fed exact-clock example:
  <https://www.federalreserve.gov/newsevents/speech/files/powell20180508a.pdf>

### Cadence gate: UNPROVEN

The raw volume of inter-meeting communication appears high enough, but valid
cadence cannot be measured until policy-only inclusion, same-day deduplication
and causal availability are bound to a valid PIT archive. Date-level rows may
not be relabelled with an invented intraday clock.

### Transmission/direction gate: FAIL

The economic mechanism is plausible and official ECB research finds that
relative Fed/ECB policy tone helps explain EURUSD. However, the published
high-frequency evidence treats market reactions as **communication surprises**
and/or combines tone with market-rate information. The ECB's illustrative
inter-meeting differential is smoothed over six months. This does not establish
that raw speech tone level alone has a stable event-trading sign.

Official evidence:

- <https://www.ecb.europa.eu/press/blog/date/2023/html/ecb.blog230809~f101598a82.en.html>
- <https://www.ecb.europa.eu/pub/research/authors/profiles/thilo-kind.en.html>

## Hard stop

Do not create a historical 2018--2025 backtest, infer event timestamps, use a
current monthly CSV as a historical vintage, tune NLP thresholds, or add price,
OIS/rate, session or OHLC filters to rescue this object. No registry row or
preregistration is opened.

## One new direction worth retaining

`FORWARD_ONLY_FED_ECB_POLICY_COMMUNICATION_CORPUS`

The only honest free-data path is to create the missing PIT evidence prospectively:

1. capture official Fed/ECB HTML/PDF/RSS at first-seen UTC;
2. preserve raw bytes, headers, URL, fetch time and SHA-256 on `D:`;
3. append every revision as a new immutable version;
4. freeze policy-only inclusion and deterministic tone scoring before outcomes;
5. measure causal cadence for at least 12 elapsed weeks before considering a
   new hypothesis;
6. stop if fewer than 80% of complete weeks contain 2--5 eligible decisions,
   capture completeness is below 95%, or deterministic replay differs.

This direction needs an explicit Owner decision before any scheduled collector.
Even a successful collection would establish data capability only, not edge.

