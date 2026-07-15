# Merge memo — Structural rebuild panel (post-Wave5)

Date: 2026-07-14 ~23:05 ICT  
Status: `OFFLINE_FIRST_COMPLETE / NO_MODEL0_SURVIVOR / PHASE0_COMPOSE_STILL_BLOCKED`  
Authority: Owner R&D continue; `DEMO_DISCOVERY_DIMINISHING_RETURNS=true`; GPT waived  
Panel: Sonic trader / quant validation / MQL5 systems (`cursor-grok-4.5-high-fast`)  
Coordinator: this memo (panel memos are inputs, not authority)

## Why thick vs cadence splits (merged)

| Lens | Mechanism |
|---|---|
| Trader | Cadence sleeves fire on **routine session/vol states** with noise-anchored stops; thick sleeves need rare **liquidity acceptance** after a real stop-run. Raising TF alone ≠ architecture. |
| Quant | Friction identity: thin $/trade books die under +$12; thick books keep PF but starve calendar cadence. Densify raises fill count and **worsens** friction budget. RR2 N=524 stress FAIL is mean-edge, not small-N noise. |
| Systems | Tester `current` understates Real haircut; portfolio co-execution ≠ equal-join; min-lot / stops-level geometry can inflate R$ vs risk% — but RR2 P10 risk_usd≈$38 already clears a $24 floor, so **tiny-stop geometry is not the RR2 failure mode**. |

**Split law (reconfirmed):** cadence sleeves ≠ thick sleeves. Mid-vol / IB / session-box without a structural invalidation object ≠ joint GOAL book.

## Shortlist ≤4 rebuild theses (a priori) + offline results

| ID | Architecture | De-dup vs killed books | Offline result | Model 0 |
|---|---|---|---|---|
| T1 `HYP-COST-ARM-RMIN-RR2-001` | Risk model: arm only if structure risk_$ ≥ k×$12 | Not MaxKZ/RR densify | **KILL** — RR2 already wide (P10≈$38); k=2/3 does not lift x1.5 PF (~1.01) | Withheld |
| T2 `HYP-AUDJPY-LEAD-USDJPY-H1-001` | Cross-asset quality impulse lag | Not GBPJPY-lead / GOLDJPY | **KILL** PF 1.06 / tpw 6.85 / stress FAIL | Withheld |
| T3 `HYP-D1-TREND-H1-PB-001` | Multi-TF: D1 slope lock + H1 PB | Not ATR%ile; not ungated EMA-stack densify | **KILL** PF ≈1.00 / stress FAIL | Withheld |
| T4 Phase-0 RR2+Spark | Portfolio sleeve equal-join | Frozen IDs only; not SBSparkBook rescue | Diagnostic PF **1.38** / tpw **3.26**; x1.5 **1.07 FAIL**; ceremony **BLOCKED** | Illegal |

Artifacts: `preflight/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V1.json`, `readouts/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V1.md`.

## Phase-0 compose ceremony

**Still blocked.** Exact text:

> `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW` — contamination not cleared. No Phase 1 outcome compose.

Universe freeze already exists (`194548` + `193358`) — metadata only. Prior Real-P50 joins remain diagnostic. Owner (or designated clean freeze review) required to clear attestation; agents must not rewrite contamination JSON.

## What NOT to test

- Another Demo session-break / IB / ATR%ile / Asia-box Model 0 batch
- MaxKZ / RR / SB / Spark densify; Wave1–5 killed/parked family retunes
- GBPJPY-lead / AUDJPY-lead densify after T2 kill; EMA-stack / D1-H1-PB retune after T3 kill
- Cost-arming threshold mining on RR2 from this readout
- Outcome-selected sleeve re-pick; PF-weighted portfolio blend; SBSparkBook scaffold reopen
- “Wait for Real login” as discovery headline

## Next structural objects (probe-first; no Model 0 yet)

1. **Stop-run → multi-bar acceptance** with a **new edge object** (not AsianSweep N=0, not EQHL intake-kill, not LondonORB-accept PARK, not PDH-break PARK) — e.g. prior-day liquidity grab + 2-bar closed acceptance beyond sweep extreme + stop behind wick; a priori RR and session contract frozen before probe.
2. **LondonNY-class thick cadence expansion** — change **event definition** only (quality events), not Mon/day mine from S529/S544.
3. **Owner Phase-0 contamination clear** — unlock compose ceremony on frozen universe (still expect +$12 stress fail unless cost provenance improves).
4. QFSI / Real cost = **parallel hygiene only**.

## Coordinator decision

- `DEMO_DISCOVERY_DIMINISHING_RETURNS=true` **acknowledged** — lane shifts to structural rebuild + offline-first.
- **No Model 0 this session** (zero offline survivors).
- Best shelf unchanged: RR2 `20260714_194548` PF **1.378** / ~**2.01**/wk (research HIT; GOAL +$12 x1.5 FAIL).
