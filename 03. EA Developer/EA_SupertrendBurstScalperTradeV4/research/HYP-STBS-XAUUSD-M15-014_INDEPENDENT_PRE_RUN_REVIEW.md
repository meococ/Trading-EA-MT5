# HYP-STBS-XAUUSD-M15-014 independent pre-run review

Verdict: `PASS_PRE_AUTHORITY`

Reviewed exact source SHA256 `028D0AADB49856F58B167390E93300CD12AD90993F13FE7D5012DE6FFB8FC726`.

The review initially found and rejected three lifecycle defects: close-before-open transaction ordering, comparing deal-row count with position count under partial fills, and replay classifying every partial close as final. The final source resolves them by:

- registering `DEAL_REASON_SO` idempotently before lifecycle-row context is required;
- deferring a close callback until the owned position OPEN has been logged;
- using one stable hypothesis/magic sidecar across reinitialization and reloading logged deal/distinct-position/stop-out identities;
- replaying historical owned deals deterministically in two passes, OPEN then CLOSE;
- balancing distinct opened and final-closed position IDs instead of row counts;
- computing cumulative volume only through the current `(DEAL_TIME_MSC, deal ticket)`, so two partial openings plus two partial closes yield exactly `CLOSE_PARTIAL(0), CLOSE(1)`.

Margin evaluation uses the correct `MqlTradeCheckResult` projected fields and the frozen percent/money stop-out contract. Signal, Supertrend, ATR, time window, stop, target, hold and maximum risk remain unchanged. All three `OrderSend` gateways are directly guarded by `InpAuditOnly`.

The first launcher review rejected a blank receipt authority because it would have entered AlphaFactory performance analysis. The final package instead uses the existing exact `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE` path: HYP014 is hard audit-only, `telemetry_profile=none`, telemetry off, no sidecars, and no performance/outcome analysis. Lifecycle-v3 code is statically reviewed here but must be restored and separately reviewed in a fresh trade-enabled child.

The final evidence-integrity pass also rejected live parser imports, repeated report/journal reads and mutable canonical compile evidence. The patched runner authority-binds and attempt-archives `quant_analyzer.py` plus the reviewed static EX5/log after the durable claim. Immediately after Alpha returns it captures any post-Alpha canonical EX5/log and the exact created/deleted run-set before checking the return code. A nonzero or later validation failure additionally archives an immutable inventory of every discovered new run. Success parses only captured report/journal bytes, requires one fresh 0E/0W result and reconciles the captured run EX5 with both manifest EX5 identities.

Bound static evidence:

- EX5 SHA256 `5F8F3B26BCDC5D9DA5F960E60F2BC12356BB881A95793A92FC0D26859D1FF803`
- compile log SHA256 `6F907E906C98BB7CBECBA5053DAF38757336B123F3DFB4771D0557CDF2042979`, result 0 errors / 0 warnings
- prereg SHA256 `033A6247186BF3C2459F6A8420B22C4E3FD350574B0F42FDFC10F7BB2E51076D`
- source/lifecycle test SHA256 `1B049E8DBA530EAD87CF7559A00DC6B99246B33CF0D0CCE357073306BB03067D`
- non-repaint manifest SHA256 `3AD97CE789EF3D4C37080D80E0A27576B3C2AEBDAA826D2D47632DF037A84BDD`
- non-repaint audit SHA256 `24A7D7DE42256BD263E0BBA157E64260DDAFFD32224F4D853457333CED6049B4`, PASS
- one-shot audit launcher SHA256 `105E4701D696AD911209EF7DD614C7B387D1430B4796DF08AE589AD697EF4034`
- audit-launcher mutation test SHA256 `4CE2C344DBF48918C0C2BCE0E79F12B09C3A49CD0FFEBD9F9A85B6B7C1E2B8F5`
- bound quant analyzer SHA256 `A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B`
- combined focused suite: 19 passed

Authority boundary: exactly one `STBS014-MODEL0-AUDIT-001`, `InpAuditOnly=true`, zero orders/outcomes/economics. The launch must fail if the stable HYP014 lifecycle or RunMeta sidecar exists before the first attempt. This audit proves signal scheduling and broker-margin-candidate feasibility only; post-fill margin and lifecycle economics remain unproven and cannot be claimed from a zero-trade run.
