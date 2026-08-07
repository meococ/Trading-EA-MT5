# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-005-C01 — native file absence

Status: `KILLED_CHARTSCREENSHOT_FILE_NOT_MATERIALIZED`

Run `20260807_060039` reached the exact frozen event and preserved the pending
request for the full 200-tick budget. The terminal sidecar recorded
`request_ok=1`, `request_error=0`, but `file_verified=0`, `file_size_bytes=0`,
`verify_ticks=200`, `verify_timeout=1`. No `RSFV_*.png` appeared anywhere under
the portable terminal or tester-agent file roots, so AlphaFactory correctly
rejected the visual run.

This establishes that `ChartScreenShot` acknowledgement is not file-delivery
proof in this portable tester environment. The remaining OUTCOME-005 cases were
not launched. A successor may use complete-window Windows Graphics Capture only
on short normal visual replays; `Skip to` mode remains forbidden because it can
expose stale frames.
