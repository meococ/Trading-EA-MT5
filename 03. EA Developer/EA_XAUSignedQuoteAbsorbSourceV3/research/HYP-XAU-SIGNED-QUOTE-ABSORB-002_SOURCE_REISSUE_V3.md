# HYP-XAU-SIGNED-QUOTE-ABSORB-002 — Source runtime reissue V3

V2 run `20260812_041825` completed the frozen MT5 Model 4 source gate, but AlphaFactory rejected the artifact because the EA did not emit the mandatory D0 series witness after MT5 synchronization. The raw bounded journal showed 32,636 source signals and a passing aggregate source gate; those values remain engineering diagnostics only until this reissue is accepted.

V3 is a fresh package identity with identical quote classification, signal state machine, thresholds, window, session, symbol and dates. It adds only the outcome-blind `DATA_EPOCH_D0_SERIES_PROOF` witness already required by AlphaFactory. No signal, threshold, trade or cost logic changed. Frozen preregistration remains the V1 package file; V1/V2 artifacts and source snapshots remain immutable.

This is an engineering evidence reissue, not a parameter or trading-logic revision.

