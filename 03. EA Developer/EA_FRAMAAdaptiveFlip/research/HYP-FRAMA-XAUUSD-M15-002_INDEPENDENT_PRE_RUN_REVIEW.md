# HYP-FRAMA-XAUUSD-M15-002 — independent pre-run review

Verdict: `PASS_BASELINE`.

Reviewed source SHA256: `6D2F21FCD53097DE82CA584A53CC507EBAC03A0056A4DA9137B46A12CFE2855F`.

The native-handle readiness transition re-anchors `g_last_bar_open` and returns before scheduling, preventing a mid-bar false exact-next execution. A never-ready run remains runtime-fatal. Signal, risk, stopout sizing and lifecycle are unchanged from the prior reviewed source. Compile is `0 errors, 0 warnings`; refreshed non-repaint audit passes and binds the reviewed source.

Authorization is limited to one untuned XAUUSD M15 Model-0 TRAIN baseline; no economic/promotion claim is made here.
