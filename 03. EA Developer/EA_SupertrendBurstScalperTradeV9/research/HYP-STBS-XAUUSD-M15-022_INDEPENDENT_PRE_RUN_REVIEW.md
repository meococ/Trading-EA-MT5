# HYP-STBS-XAUUSD-M15-022 — Independent pre-run review

## Verdict

`PASS_PRE_AUTHORITY`

Static independent review found no fatal blocker before the initial HYP022 authority. No source data, MT5 baseline, outcome, return or economic artifact was opened by this review.

## Reviewed identities

- Source: `9B82946CF17A876B547E7227F7FA131183C2383D38BF639574001CAB03DF8D82`
- EX5: `5FDB825F8D83EF52F639547CE444C936FD1ED9EE581AD5220EBA0774128A8954`
- Compile log: `E605E1BD6095F7E79D44F8397F54A2D02D89F2E191D17DDC6CD7762A92A5DEF9`, exactly one `0 errors, 0 warnings` result
- Preregistration: `7AACB5A598957CF29D661833E5756B0981090741C86047B0B1CE8187319FD8BF`
- Bounded diff proof: `1CC4B30A4F524A95837DD53AFC76CB2CDDF59619A41A58AB8578FF339FD35B44`
- Risk/source test: `E6F337726E1CC627732C05D194C2C39D43D9ABA5C91401BAAE1BA7074A2AC1A1`
- Runner/adapter test: `3A519EE55818800B4DCF2965DCC0B9B42292DE7B3381B3432E84B57B7B039391`
- HYP022 runner: `A01B6D5F3E76C5B6E3B60D82690F6D894E1A9B559A19E107BA475D2ECDAB0F5E`
- Non-repaint auditor: `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`
- Static non-repaint manifest: `899E2C031DBC93FD99450990347C3FB1FB412E848964820AD4A0887FAAE3F6F1`
- Static non-repaint audit: `359E11DC5979E5D0B915A510F0148D3451D11994EDF46ADA1D18F3CF0C238509`

## Findings

The source stresses every candidate from the worst fill permitted by the frozen 20-point deviation to the frozen SL, subtracts the full frozen 4.4/lot round-turn charge, and uses the greatest requested-entry, worst-fill or SL margin for both the 5%-equity ceiling and stressed total margin. The unchanged actual-margin check remains a fatal runtime backstop for gaps beyond that frozen envelope.

The run-local non-repaint adapter preserves the original AlphaFactory manifest, rejects pre-existing provenance fields, freezes the exact auditor/static authority, and accepts only `collection_authority_verified=false`, one exact V9 source, zero findings and one exact line-678 `collection_first_date_copytime` allowance. Auditor, derivative manifest and audit bytes are rehashed before acceptance and recorded in the run evidence.

Focused tests report `15 passed`; the candidate registry reports `860` valid rows before HYP022 authority. This verdict authorizes only preparation of the frozen one-shot baseline authority. It is not evidence of market edge, PF, economic validity or promotion readiness.
