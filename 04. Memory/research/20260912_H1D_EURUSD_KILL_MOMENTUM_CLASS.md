# 2026-09-12 — CELL 8: EA_HtfDisplacement EURUSD M5 kill + CRLF registry hazard

## Result

| Field | Value |
|---|---|
| Hypothesis | HYP-H1D-EUR-M5-001 (H1 displacement continuation, M5 exec) |
| Runs | `20260912_084836` (pass A) + `20260912_085029` (governed, complete loop end-to-end) |
| Window | 1999.01.01 → 2026.09.11 (`verified_m1_asof`) |
| History quality | **99%** |
| Trades | 6,907 — cadence **4.78/wk FAIL** (< 10 floor) |
| Report PF / Net / DD | 0.869 / -2,604 USD / 27.0% |
| Cost PF x1.0 / x1.5 / x2.0 | **0.763** / 0.711 / 0.664 |
| MC p95 DD / Robustness | 28.1% / 14.3% |
| Overnight / weekend | 0 / 0 — PASS (first clean exposure gate) |
| Verdict | REVIEW → **KILLED_AT_MODEL_0** |

## Reading

First momentum-class test on the cheap venue (EURUSD spread p90 0.1
pips). Two independent disqualifiers:

1. **Cadence** — 4.78 trades/week vs the 10/week floor. H1-level signals
   (one decision per closed H1, Mon–Thu 08–16, body ≥ 0.5×ATR(H1)) are
   intrinsically sparse; reaching 10/wk would require leaving the frozen
   spec, which is not permitted.
2. **Economics** — PF 0.869 gross, 0.763 at measured cost. Europe 0.89 /
   NY 0.82 both negative; losses spread across 13 flagged years — no
   regime concentration to even hypothesize about.

Momentum continuation is not better than the fade/MR family on this
venue: three EURUSD mechanisms (IBS continuation, Camarilla fade, H1
displacement) all land at cost-PF ≈ 0.68–0.76.

## Pipeline finding: CRLF registry line endings

Pass-A was blocked by `registry_row_sha256` mismatch. Root cause: a
Python text-mode append wrote `\r\n`, so `build_control_packet.py`'s
raw-bytes row hash included the trailing `\r` while the engine's
`Get-TextSha256` hashes the `Get-Content`-stripped line. Fix:

- Registry normalized to LF (validated `CANDIDATE_REGISTRY_OK`).
- Builder now strips trailing `\r` before hashing the raw line —
  robust to either convention.

Append note for future rows: write the registry in binary or with
`newline=''` to preserve LF.

## Cell tally (8 kills, 0 passes)

CRSI-R2 GBPUSD (data) · AMA XAU · VwapFade XAU · HourDrift XAU ·
GBBSqueeze XAU · IBSC EURUSD · CamarillaFade EURUSD · **H1D EURUSD**.
