# Acquisition readout — Iron ore + CNY strength

Manifest: `v8_exogenous/manifests/20260715_IRONORE_CNY_ACQUISITION_V1.json`  
Contract: `v8_exogenous/contracts/20260715_IRONORE_CNY_AVAILABLE_AT_UTC_CONTRACT_V1.json`

## OK

- Yahoo TIO=F iron ore daily → panel lag +1d  
  SHA `85DE1CAC628A0476570CE490B33A8C80911EBEB66A79E1C89DC781A35F9A9A0E`
- Yahoo USDCNY=X → CNY strength (1/USDCNY) panel lag +1d  
  SHA `9C173814E2453948D31EEA1F915CAA2B2F9AFBDCFD81781BA7214F1948E2FA48`

## Unavailable this pass

- CNH=X / USDCNH=X offshore (Yahoo n≈1) — documented in contract
  `unavailable_this_pass`; pick-next = USDCNY strength.

## Explicit non-use

- Not XLK/XLF sector twin.
- Not HG/GC CuGold twin.
- Not VIXCLS / MOVE / HY / DTWEX siblings.
- Not WTI/Brent oil ToT densify.
- Not WALCL/ECB/MMF/G10 overnight FRED densify.
