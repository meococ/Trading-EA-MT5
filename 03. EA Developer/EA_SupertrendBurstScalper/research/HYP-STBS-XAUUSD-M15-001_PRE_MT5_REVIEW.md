# HYP-STBS-XAUUSD-M15-001 — Independent pre-MT5 review

- Status: `PASS_PRE_MT5_PACKET_BUILD_AUTHORITY`
- Review time: `2026-08-09T04:44:00Z`
- Scope: static engineering and evidence-chain review only. No AlphaFactory run, MT5 launch, source-data scan, order, deal, outcome, return, or economic metric was opened by this review.

## Frozen identities

- Prereg: `483132EE010DEB3EDC3DD1C1E93B419DC63CC7A61B324F76C40AE00650520F35`
- MQL5 source: `B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D`
- Packet builder: `93ACA56CB81D1AAF87899364672A681120AAE355C5A61869DFDD884D17655DDD`
- MT5 audit runner/comparator: `C4F2976F919EF9345CFC15891A9A8066F1FB5D474635C88BB29D047456645C14`
- Harness tests: `94242FECB06A17C869BA2FAE10965373FB34CA2CD27B9E92E54D0C73D4AD14DB`
- Engineering tests: `E657D43E27558B4B35A0D585323E314161CAF2FCC7A01F59FF8744702A7F258A`
- Non-repaint audit: `FBFB994CA6238CE323EA890A8A3C7F909D219466FE65F1416B3527C474F17503`
- Static compile receipt: `5D7975407041AAFFFA26307A4386806C7D6258221483B0502642A7165484BAE1`
- `.gitignore`: `5BED98CF0FF2526A725B0E64B69A76EEA74430A13206E0F1EBE2AEE75441FED6`

## Review verdict

The causal package and the two-stage harness are fit for the initial packet-build authority. The review verified:

1. Closed H1 Supertrend events remain exact to the HYP012/HYP003 parent mapping; M15 exact-open, prior-M15 ATR and no-send geometry checks are causal and fail closed.
2. The packet builder claims `STBS001-PACKET-BUILD-001` exclusively with flush/fsync before reading bound inputs, writes success or failure terminal evidence, and binds its marker, attempt identity and authority row in the receipt.
3. The MT5 runner requires packet attempt limit one and consumed one, then claims `STBS001-MT5-AUDIT-001` before hashing receipt, parent oracle or other bound evidence.
4. Duplicate Terminal/Core journal records are accepted only when payloads are identical with uniform multiplicity; 690 unique source epochs remain mandatory.
5. Source, EX5 and config must be the exact run-local snapshot paths and match manifest hashes.
6. The packet and MT5 attempt roots have exact ignore rules; `.gitignore` is itself hash-bound, so evidence-terminal creation cannot invalidate the sealed Git-status contract.
7. All order, deal, performance, outcome, economic, optimization, validation, holdout, paper, live, retry and registry-mutation permissions remain false.

Focused evidence: 18/18 source-contract tests and 18/18 harness tests pass; both Python harness modules compile; candidate-registry and source-of-truth validators pass. This PASS authorizes only the initial probe row and the single packet-build attempt. It does not authorize AlphaFactory/MT5 or make an economic claim.
