# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-004-C01 — capture lifecycle failure

Status: `KILLED_ASYNC_SCREENSHOT_VERIFIED_TOO_EARLY`

Run `20260807_055425` reached the exact post-exit event and MT5 accepted the
native `ChartScreenShot` request. The VisualShots row proves:

- case: `RSF-C16-BREAKOUT-LONG-L`;
- event: `2019.06.04 09:59:59` server time;
- filename was unique;
- `request_ok=1`, `request_error=0`;
- `file_verified=0`, `file_size_bytes=0`, `verify_timeout=1`.

The code used `CaptureQueuedVisualShots(true)` in the same tick. Because
`ChartScreenShot` is asynchronous, force mode immediately treated the not-yet
materialized file as a terminal timeout and discarded the pending event. No PNG
was imported. This is an engineering failure, not a chart or trading result.

The remaining OUTCOME-004 cases were not launched because they share the same
capture lifecycle. The successor must issue on a later tick, retain reference
objects, and verify over subsequent ticks before cleanup.
