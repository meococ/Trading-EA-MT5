# HYP-STBS-XAUUSD-M15-015 independent pre-run review

Verdict: `PASS_PRE_AUTHORITY`

HYP015 is a fresh outer-only harness revision after terminal HYP014. It reuses the exact V4 MQL source, magic, EX5, compile log, non-repaint evidence, cost/data identity and signal/margin mapping. Outer authority/task/receipt/run-manifest identity is HYP015; the immutable inner MQL override and journal summary identity remains HYP014.

The only invocation change is removal of the Alpha CLI `-Spread` pair. Receipt and expected manifest still bind semantic spread `current`, which is the AlphaFactory representation produced by an omitted/empty current-spread request. The runner separately verifies the terminal HYP014 row/hash/verdict and hashes its failure, post-review and failed-attempt terminal artifacts.

Bound current evidence:

- source SHA256 `028D0AADB49856F58B167390E93300CD12AD90993F13FE7D5012DE6FFB8FC726`
- prereg SHA256 `46F44F893909E70E0859FEC0A9CB10B1592B6BD757F9532B1E8D6A3AAFB296E0`
- runner SHA256 `49908B8F1D82C1F6CB652B16CB52B25B99046ABE35D01FE4287F5E5776309746`
- HYP015 revision test SHA256 `01E6BB4E1321B32519DB6CBEDC12D103D31C6A9AD0D4F4C9D822F1A4FE6FCE14`
- inherited source/lifecycle test SHA256 `1B049E8DBA530EAD87CF7559A00DC6B99246B33CF0D0CCE357073306BB03067D`
- inherited non-repaint audit SHA256 `24A7D7DE42256BD263E0BBA157E64260DDAFFD32224F4D853457333CED6049B4`, PASS
- inherited static EX5 SHA256 `5F8F3B26BCDC5D9DA5F960E60F2BC12356BB881A95793A92FC0D26859D1FF803`
- inherited compile log SHA256 `6F907E906C98BB7CBECBA5053DAF38757336B123F3DFB4771D0557CDF2042979`, 0 errors / 0 warnings
- combined focused suite: 23 passed

Authority boundary: one `STBS015-MODEL0-AUDIT-001`, data acquisition/correctness only, zero orders/outcomes/economics, no retry. The inherited claim-first static/captured-byte/run-delta/failure-inventory contract remains unchanged.
