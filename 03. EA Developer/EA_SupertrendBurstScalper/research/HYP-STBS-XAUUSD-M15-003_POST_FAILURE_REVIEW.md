# HYP-STBS-XAUUSD-M15-003 — Independent post-failure review

Status: `PASS_KILL_HYP003_VALIDATOR_CONTRACT_FAILURE_RUN_REUSABLE_NO_ECONOMICS`

Independent review reconciled the screened authority, sole attempt artifacts, Alpha run manifest, HQ/data proof, report, journal, zero-trade summary, source, EX5 and config. Alpha compile/MT5/data collection completed. The attempt failed only after the run because the inherited validator rejected a single leading UTF-8 BOM. A latent comparator defect also used the oracle server-axis epoch where MQL emits the UTC numeric epoch.

Read-only forensic reconciliation established two identical journal copies and 690 unique events with exact counts `683/7/339/344`, ATR/geometry readiness `683`, zero direction/exact-next mismatches, zero fatal/trade records, and zero mismatch under both correct time identities: numeric runtime epochs against oracle UTC and printed timestamps against oracle server time. Therefore HYP003 demonstrates neither a signal/causal/runtime failure nor any economic result.

The HYP003 attempt is consumed and must not be retried. A fresh comparator-only child is legal after terminal closure if it:

- uses a fresh ID/root/one-shot claim and authorizes no compile, MT5, outcome or economics;
- hash-locks the HYP003 authority/start/terminal/stdout/stderr and every canonical run artifact before reading them;
- captures every input once after claim and hashes/parses the same bytes;
- accepts at most one leading UTF-8 BOM for known JSON, rejecting double/interior BOM and invalid UTF-8;
- requires exact duplicate multiplicity two, all frozen counts and zero order/trade/fatal records;
- maps numeric source/decision epochs through oracle UTC rows while independently matching printed source/decision strings to oracle server-axis epochs;
- binds both canonical and duplicate run-local paths where present, and makes no zero-warning claim without a compile log.

No market-edge, performance, PF or deployment conclusion is authorized by this review.
