# PLAUSIBILITY — blind audit (mandate W1, seed 20260921)

## judge calibration

Golden-control 'yes' rate: **27/30 = 0.90** — judge reliable (>= 0.8)

## plausible-FP rate (share of engine FPs a PA trader would plausibly draw)

| engine | n | plausible | rate |
|---|---|---|---|
| v0 | 30 | 22 | 0.73 |
| v1@ef06f265 | 30 | 21 | 0.70 |
| linelab | 30 | 24 | 0.80 |

| fp type | n | plausible | rate |
|---|---|---|---|
| BAR_MARKER | 9 | 6 | 0.67 |
| BOX | 11 | 6 | 0.55 |
| BRACKET | 7 | 6 | 0.86 |
| CONTEXT_LINE | 2 | 2 | 1.00 |
| CONTEXT_RANGE | 2 | 0 | 0.00 |
| LABEL_TF | 5 | 5 | 1.00 |
| LEVEL_CARRIED | 7 | 4 | 0.57 |
| PATTERN_LINE | 44 | 38 | 0.86 |
| RANGE_OPEN | 1 | 0 | 0.00 |
| SQUEEZE | 2 | 0 | 0.00 |

## golden misses (golden objects no engine matched)

knowable share: **27/30 = 0.90** ; plausible share: **27/30 = 0.90**

engine-FP knowable share (structure existed at decision time): **66/90 = 0.73**

## judge specificity (W1b negative controls, R17 §17.4)

sensitivity (golden controls yes-rate): **27/30 = 0.90**

specificity (negatives judged not-plausible, cant_tell excluded): **20/30 = 0.67** (n_decided 30/30)  — **UNRELIABLE (< 0.70)**

| engine | n | obs. plausible | Rogan–Gladen corrected | CI95 |
|---|---|---|---|---|
| v0 | 30 | 0.73 | 0.71 | 0.33..1.00 |
| v1@ef06f265 | 30 | 0.70 | 0.65 | 0.29..1.00 |
| linelab | 30 | 0.80 | 0.82 | 0.50..1.00 |


## negatives audit + W1b recompute (R28 §28.3.2, 23:09Z)

Method: `neg_audit.py` converts each synthetic negative into an engine
record and runs the official ruler (`eval_v2.match`) against every
scorable golden on the same panel.  A negative that matches is invalid
— the judge saying "plausible" is then *correct*, not a false accept.

### result

| class | n | invalid |
|---|---|---|
| all W1b negatives | 30 | 2 |
| owner-pack negatives (subset) | 6 | 0 |

Invalid: `neg_002`, `neg_011` — both **BRACKET price-shifted** copies.
The ruler's bracket rule (coverage >= 0.3 + same letter) does not test
price, so a 3-5 ABR price shift leaves the match intact.  Construction
defect: for BRACKET, only a *time* shift or a letter change produces a
true negative.

`neg_025` (pack p05, visually a well-fitted box): ruler **no-match**
against its nearest golden (BOX, 35 min overlap) — valid negative; the
judge correctly said "no".

### W1b recomputed

sensitivity (golden controls): **27/30 = 0.90** [0.77-1.00]

| denominator | rejected | specificity | CI95 |
|---|---|---|---|
| all 30 negatives | 20/30 | 0.67 | 0.50-0.83 |
| 28 valid negatives | 19/28 | **0.68** | 0.50-0.86 |

Rogan-Gladen corrected plausible-FP share:

| engine | RG (all-30) | RG (valid-28) |
|---|---|---|
| v0 | 0.71 [0.41-1.00] | 0.71 [0.42-1.00] |
| v1@ef06f265 | 0.65 [0.35-0.94] | 0.65 [0.37-0.94] |
| linelab | 0.82 [0.59-1.00] | 0.83 [0.54-1.00] |

### verdict on R22 §22.3 "judge unreliable"

**Stands, and was only marginally an artefact.**  Removing the two
invalid negatives lifts specificity 0.67 -> 0.68 — still below the 0.70
bar, and the RG-corrected plausible-FP shares move <= 0.01.  The wide
CIs ([0.50-0.86]) include 0.70, so "unreliable" is a precision
statement, not a proven bias.  Note the artefact ran the other way for
`neg_011`: the judge's "yes" on an item that actually matches a golden
was arguably *correct* — counting it as a false accept understated
specificity.
