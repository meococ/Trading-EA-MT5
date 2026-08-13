# Frozen preregistration - HYP-ORLS-EURUSD-H1-002

Runtime-only successor to `HYP-ORLS-EURUSD-H1-001`, whose sole run stopped before economics on an array bound error. HYP002 changes only the feature buffer allocation from 25 to 26 H1 rates and refreshes package/hypothesis/magic/log identity. All equations, six features, past-only EW standardizer, delayed four-open label, RLS constants, cost hurdle, fixed four-H1-bar lifecycle, catastrophe stop, sizing, risk locks, test splits and gates remain exactly those frozen in the HYP001 preregistration.

EURUSD H1, Model 0, DESIGN `[2018-01-01, 2022-01-01)`, FivePercent current broker spread, USD100,000, leverage 1:100. Warm-up 120 valid observations; `lambda=beta=0.9975`; `alpha=1`; label horizon 4 contiguous H1 opens. Entry requires score beyond `1.5 * (spread/mid + 0.00008 + 0.00005)`. Catastrophe SL is `3*ATR14` clamped 25..80 pips, 0.25% equity risk, 3x notional cap, 9% free-margin cap, fixed four-bar exit, 21:50 daily and 18:50 Friday flat.

No validation, holdout, matched-control, tuning, feature edit, direction/session/day/year filtering or alternate model is authorized before the DESIGN engineering/coverage/label gates are reconciled.
