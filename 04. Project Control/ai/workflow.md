# EA Development Workflow — Sonic R

Updated: 2026-07-13

## Development Lifecycle

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ 1.IDEATE │──▶│2.RESEARCH│──▶│ 3.PREREG │──▶│4.DEVELOP │
│          │   │          │   │          │   │          │
│ Thesis   │   │ Source   │   │ Hypothesis│  │ Code     │
│ Source   │   │ Audit    │   │ Pass/fail │  │ Compile  │
│ Family   │   │ De-dup   │   │ Budget   │  │ Non-      │
│ Check    │   │ No-outcome│  │ Holdout  │  │ repaint  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                   │
    ┌──────────────────────────────────────────────┘
    ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│5.BACKTEST│──▶│6.VALIDATE│──▶│7.FORWARD │──▶│ 8.DEPLOY │
│          │   │          │   │   TEST   │   │          │
│ Model 1  │   │ WFA      │   │ Demo 2-4w│   │ Micro-   │
│ screen   │   │ Monte    │   │ ≥50 trade│   │ live     │
│ Model 0  │   │ Carlo    │   │ Match BT │   │ Scale up │
│ confirm  │   │ Robust   │   │ No param │   │ Monitor  │
│ Cost     │   │ Cost     │   │ change   │   │ Kill     │
│ stress   │   │ stress   │   │          │   │ switch   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
```

## Candidate State Machine

```
idea → probe → screened → challenger → confirmed → forward-test → portfolio-sleeve → live
                  ↓           ↓            ↓             ↓
               parked      parked       parked         parked
                  ↓           ↓            ↓             ↓
               killed      killed       killed         killed
```

- **idea**: Thesis documented, source identified
- **probe**: No-outcome audit / offline analysis running
- **screened**: Model 1 fast screen completed
- **challenger**: Model 0 backtest run, under review
- **confirmed**: Passed 5/5 validation gates
- **forward-test**: Running on Demo account
- **portfolio-sleeve**: Passed forward test, approved for portfolio
- **live**: Running real money (micro → full scale)
- **parked**: Promising but failed a gate — can be revisited
- **killed**: Fundamental flaw found — no revival without new evidence

## Failure-to-Research Feedback Loop

```text
VALID RUN FAILS A STRATEGY GATE
  -> RECORD + KILL/PARK CURRENT VERSION
  -> FREEZE FAILURE PACKET AND ARTIFACTS
  -> GPT-5.6 SOL + PRO + DEEP RESEARCH
  -> SOURCE AUDIT + FAMILY DE-DUP
  -> NEW INDEPENDENT/CHILD HYPOTHESIS OR NO LEGAL CANDIDATE
  -> CHEAP OFFLINE PROBE
  -> NEW PREREG ONLY IF THE PROBE SURVIVES
```

- An invalid run routes to correctness/infrastructure repair and an exact-packet
  rerun; it is not strategy evidence and must not seed a new trading rule.
- A valid poor-performance result closes the current hypothesis version before
  research continues. Deep Research diagnoses the failure and searches for a
  genuinely new mechanism; it cannot tune the failed version.
- Any post-result hour/day/session/symbol/threshold/SL/TP/BE/filter observation
  is a new idea with a new trial budget, holdout, ID, probe, and preregistration.
- Repeated duplicate proposals or an unchanged data/execution blocker stop the
  loop until external evidence changes. `NO LEGAL CANDIDATE` is valid output.
- No Deep Research answer authorizes code, compile, backtest, or promotion.

## Phase Details

### Backtest batch storage closeout

Every batch of at least five runs or at least 1 GiB ends with this storage lane:

1. Build/refresh the runs catalog and record active `runs/` bytes.
2. Analyze first; generate compact validation/datalog/cost artifacts before any cleanup.
3. For logs over 50 MB or likely over 100,000 lines, create a streaming index and use capped search/window reads. Never load the whole file into agent context.
4. Dry-run byte-identical mirror dedupe; keep `logs/` and `analysis/logs/` compatibility paths as hardlinks.
5. Dry-run archive retention. Canonical/doc-referenced run IDs are protected automatically; recent runs are protected by the age gate.
6. Owner reviews candidate list, bytes reclaimed, destination volume and plan SHA256. No approval means no deletion.
7. Execute as copy -> full SHA256 verification -> source removal, then rebuild `runs.db` and record the archive manifest.

This lane manages storage only. It cannot change a run verdict, rescue a strategy,
or turn an archived run into weaker evidence.

### Phase 1: Ideate

- Document the trading thesis in plain language
- Identify source/provenance (ForexFactory, research paper, observation)
- Check against existing feature families — is this genuinely new?
- If it maps to a killed/parked family → stop unless new evidence exists

### Phase 2: Research

- Source audit: read and record exact pages/posts
- De-duplicate against `SONIC_SOURCE_INVENTORY.md`
- Run no-outcome analysis if applicable (scanner, census, label sheet)
- **No code changes allowed in this phase**

### Phase 3: Pre-Register

- Use `research/registry/PREREG_TEMPLATE.md`
- Define: hypothesis, changed feature, symbol/timeframe, date window
- Define: model, overrides, pass/fail gates, feature budget
- Define: holdout rules, banned post-result edits
- Register in `CANDIDATE_REGISTRY.jsonl`

### Phase 4: Develop

- Implement **one small reversible patch**
- New behavior must be **default-off** unless gate explicitly authorizes
- Compile immediately: `alpha.ps1 compile EA_SonicR`
- Run non-repaint audit: grep for `CopyRates(...,0,...)`, `CopyBuffer(...,0,...)`
- Review diff before proceeding

### Phase 5: Backtest

**Model 1 Screen (fast, ~2 min):**
```powershell
alpha.ps1 backtest EA_SonicR -Symbol EURUSD -Period M5 -Model 1 `
  -DateFrom 2021.01.01 -DateTo 2025.12.31 -Overrides "key=value"
```

**Survivor gates (Model 1):**
- Net Profit > $300
- PF ≥ 1.15
- Max DD ≤ 5.0%
- Trade Count ≥ 100

**Model 0 Confirmation (slow, ~15-30 min):**
```powershell
alpha.ps1 backtest EA_SonicR -Symbol EURUSD -Period M5 -Model 0 `
  -DateFrom 2021.01.01 -DateTo 2025.12.31 -Overrides "key=value"
```

- Model 0 must match Model 1 within lot-rounding tolerance
- If PF drops > 0.15 from Model 1 → investigate tick-data artifacts

### Phase 6: Validate

**Run full validation stack:**
```powershell
alpha.ps1 validate-full EA_SonicR -RunId <run_id>
```

**5 gates, ALL must pass:**

| # | Gate | Tool | Pass Criteria |
|---|------|------|---------------|
| 1 | Walk-Forward Analysis | `alpha.ps1 wfa` | ≥3/5 OOS windows profitable |
| 2 | Monte Carlo Simulation | `alpha.ps1 monte` | P95 DD < initial DD × 1.5 |
| 3 | Robustness Suite | `alpha.ps1 robust` | ≥4/7 tests pass |
| 4 | Cost Stress | `sonic_cost_stress.py` | PF > 1.0 at x2 cost, PF ≥ 1.25 at x1.5 |
| 5 | Equity Curve Audit | `validate-full` | No >500 day flat, R² > 0.85 |

**Additional checks:**
- Non-repaint audit (source scan)
- Market phase attribution (no single-regime dependency)
- Portfolio correlation (if adding to existing portfolio)

### Phase 7: Forward Test

| Parameter | Requirement |
|-----------|-------------|
| Duration | 2-4 weeks minimum |
| Trade Count | ≥50 trades (more important than calendar time) |
| Environment | Demo account, same broker as planned live |
| VPS | 24/7 connectivity required |
| Monitoring | Daily P&L log, execution quality check |
| Pass Criteria | PF within backtest 95% CI, no execution errors |
| **Critical Rule** | If ANY parameter changes → restart evaluation period |

**Metrics to track daily:**
- Trade count, win rate, PF
- Slippage per trade (actual vs. expected)
- News filter behavior (fail-closed working?)
- SL/TP fill quality
- Spread at execution time vs. backtest assumption

### Phase 8: Deploy

**Transition path:**
1. **Micro-live**: 0.01 lot, minimum capital, 4-8 weeks
2. **Scaled live**: Gradual increase to target risk%
3. **Full deployment**: Target allocation, ongoing monitoring

**Kill switches (mandatory):**
- Max daily loss: 3% equity → disable EA
- Max weekly loss: 5% equity → disable EA
- Max drawdown: 10% equity → disable all EAs
- Spread filter: skip trade if spread > 2× normal
- VPS disconnect alert: email/telegram notification

**Monthly review checklist:**
- [ ] Compare live PF vs. backtest PF
- [ ] Check rolling 30-day drawdown
- [ ] Review execution quality (slippage stats)
- [ ] Verify no parameter drift
- [ ] Check correlation between sleeves hasn't increased

## Quick Reference: AlphaFactory Commands

```powershell
# Compile
alpha.ps1 compile EA_SonicR

# Backtest (Model 1 screen)
alpha.ps1 backtest EA_SonicR -Symbol EURUSD -Period M5 -Model 1 -DateFrom 2021.01.01 -DateTo 2025.12.31

# Backtest (Model 0 confirm)
alpha.ps1 backtest EA_SonicR -Symbol EURUSD -Period M5 -Model 0 -DateFrom 2021.01.01 -DateTo 2025.12.31

# Full validation
alpha.ps1 validate-full EA_SonicR -RunId <id>

# Individual gates
alpha.ps1 wfa EA_SonicR -RunId <id>
alpha.ps1 monte EA_SonicR -RunId <id>
alpha.ps1 robust EA_SonicR -RunId <id>

# Full research loop
sonic_research_loop.ps1 -EA EA_SonicR -Symbol EURUSD -Period M5
```

## File Organization

```
Advisors/
├── AGENTS.md                           ← Agent doctrine (lean rules + pointers)
├── CLAUDE.md                           ← Claude pointer-only entry
├── INDEX.md                            ← Workspace map
├── 01. GOAL/
│   └── GOAL.md                         ← Owner-frozen target
├── README-SONIC R.md                   ← Strategy knowledge base
├── 02. AlphaFactory/                   ← Build & test pipeline
│   ├── alpha.ps1                       ← Main CLI
│   ├── runs.db                         ← Run catalog
│   ├── runs/                           ← Run evidence
│   └── tools/                          ← Analysis tools
├── 03. EA Developer/EA_SonicR/         ← Source code
│   ├── EA_SonicR.mq5                  ← Main EA
│   ├── Include/                        ← Module headers
│   ├── presets/                        ← Parameter presets
│   └── research/                       ← Research & evidence
│       ├── preregs/                    ← Pre-registrations
│       ├── readouts/                   ← Experiment results
│       ├── analyzers/                  ← Analysis scripts
│       ├── data/                       ← JSON data
│       ├── specs/                      ← Strategy specs
│       └── registry/                   ← Candidate registry
├── 04. Project Control/ai/            ← Control docs
│   ├── hot.md                          ← Current hot cache
│   ├── current_state.md                ← Current state
│   ├── workflow.md                     ← THIS FILE
│   ├── forward_test_protocol.md        ← Forward test procedure
│   └── validation_gates.md             ← Gate definitions
└── deploy/                             ← Deployment configs
    ├── demo/                           ← Demo .set files
    ├── prop/                           ← Prop .set files
    └── live/                           ← Live .set files
```
