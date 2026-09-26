# RW_EST — "write the right band" (Ruling 87, arm RW)

Estimate, read-only. Parent = C-3 (`uip2_pbbirth@8361fe85`,
canonical-identical `@e7d13384`), tau-keyed runs, 623 TUNE windows,
`eval_v2.V2.match` imported. Simulation = verbatim replay of
`pipes.py:50-179` over the confirmed-pivot stream.

## STEP 0 — mechanics (confirmed with file:line)

Lead's read confirmed exactly:

- range-double band: DEFENDED edge = the pair price
  (`top=max(prev.price,price)` `pipes.py:83` for double_top;
  `bot=min(...)` `pipes.py:86` for double_bottom); OPPOSITE edge =
  raw segment extreme (`bot=min seg lows :84`, `top=max seg highs :87`)
  over `seg = bars[max(0,lo_i-2):idx+1]` (:80-81).
- `dtol = max(1.0, 0.25*abr)` computed `pipes.py:70`, **unused**; the
  pair test at `pipes.py:79` uses the fixed `DTOL = 2.0` (:66).
- `trade_tags.cluster_edge(sorted_wicks, tol, top)` never returns
  None — it falls back to `sorted_wicks[0]` = the raw extreme
  (`trade_tags.py:161`). Ruling's "if None keep raw" ≡ built-in.
- Carried levels keep `src=None` in geometry (checked on live pickles);
  the carry link is the `why` route (`broken_box_edge_*`,
  `congestion_edge`, `boxes.py:1211-1223`).

Expressibility:

- **RW-E** is exactly replayable: same trigger, same cands, same seg;
  only the opposite-edge value changes
  (`min/max seg` → `cluster_edge(seg wicks, tol_e)`). Envelope is
  evaluated on the *new* height, so a birth can move to a later cand.
- **RW-G** is exactly replayable: same edge math, pair test tolerance
  `dtol` instead of `2.0` — changes which `prev` qualifies (first
  qualifying in the backward scan), hence band and t_left.
- A build would touch `pipes.py:84/:87` (flag e.g. `ev_uip_rw_edge`)
  and `pipes.py:79` (flag e.g. `ev_uip_rw_gate`); nothing else.
- **No birth-cap or budget channel**: both variants only change the
  UIP object's band / write decisions; the object still occupies
  `famlive_box=1` and stays lvfree-excluded from signal/hard caps.
  The only cross-family channel is (a) carried levels spawned from a
  band edge that now differs, and (b) a shifted/failed UIP birth
  (envelope on the changed height, or no qualifying pair under RW-G).

Approximations: object death pinned to the real `t_right` (v1
lifecycle not re-derived on changed bands); birth score floor assumed
to pass (no `below_min_score` replay); pivots visible at bar `i` =
`t_conf <= i`. Fidelity validates the approximation set:

**Fidelity: parent replay (mode=base) reproduces the real C-3 write
chain exactly on 119/119 decisions** (bar + both edges).

## PART 0 — diagnostics

### 0a. Edge-error split DEFENDED vs OPPOSITE (ABR20)

24 rewrite-in-window rows → 54 writes, vs the edge-matched candidate
and vs golden; 16 hits → last write vs golden.

| group | edge | n | med | p75 |
|---|---|---|---|---|
| writes vs cand | defended | 54 | 0.56 | 1.11 |
| writes vs cand | opposite | 54 | **0.62** | **1.54** |
| writes vs golden | defended | 54 | 0.91 | 1.68 |
| writes vs golden | opposite | 54 | **0.85** | **1.84** |
| 16 hits vs golden | defended | 16 | 0.23 | 0.39 |
| 16 hits vs golden | opposite | 16 | 0.19 | 0.44 |

Lead's prediction (opposite error larger): **weakly confirmed on the
miss rows** (opposite p75 larger both vs cand and vs golden) but
**not on hits** (defended med slightly larger, 0.23 vs 0.19). The
raw-extreme edge is not the dominant error term on the hit set — both
edges are within ~0.4 ABR there.

### 0b. Clause binding on the 12 no_cand rows (per confirmed pivot)

| clause | pivots |
|---|---|
| SEP (no same-side prev with `idx-t_ext >= 8`) | 0 |
| DTOL (prev eligible, all `|dprice| > 2.0`) | 13 |
| would pass if `|dprice| <= dtol` | **0** |
| pb clause: `idx - t0a < PBSEP` | 13 |

`dtol` would not have admitted any candidate on these rows — on these
panels `dtol = max(1.0, 0.25*ABR)` is **below** 2.0, i.e. RW-G
*tightens* the gate here.

## PART 1 — simulation results

### Item 1: box hits (V2.match on simulated box@1 at each golden tau)

| variant | lost (of 16) | gained (of 103) | net |
|---|---|---|---|
| RW-E | 4 — 9.6a@600, 9.15b@900, 9.32a@510, 9.44b@730 | 1 — 9.15b@895 | **-3** |
| RW-G | 3 — 9.17a@475, 9.34a@495, 9.44b@730 | 1 — 9.25b@775 | **-2** |

Mechanism check (RW-E): `cluster_edge` returns a less-extreme
(= defended-cluster) opposite edge only when the raw extreme is an
isolated wick; on the lost hits the band narrowed and the golden
edges fell outside ruler tolerance.

### Item 2: rewrites per panel

| variant | sim med | p90 | max | parent med | added | removed |
|---|---|---|---|---|---|---|
| RW-E | 29 | 43 | 56 | 29 | +0 | -0 |
| RW-G | 23 | 37 | 49 | 29 | **+0** | **-707** (115 panels) |

RW-E writes on the same triggers (count identical; only edge values
differ, and only where a 2-wick cluster exists — 3/12 review panels'
final band changed). RW-G removes writes everywhere: `dtol` < 2.0 on
all measured panels, so the gate only ever tightens.

### Item 3: cross-family at-risk (C-3 hits: level 7, line 20, bracket 29)

| variant | level | line | bracket | reason |
|---|---|---|---|---|
| RW-E | 1 | 0 | **2** | `birth-bar-differs` (envelope on changed height moves UIP birth → slot held by a different early object); no `carry-edge-differs` hit |
| RW-G | 1 | 1 | **2** | same channel |

At-risk rows: level 9.61c@745 LEV0010; line 9.4a@530 PAT0011 (G only);
bracket 9.26c@925 BRA0015, 9.61c@935 BRA0005 (both).
Arm-Y gross-loss leg: the implicated UIP band differs from parent on
all 7 arm-Y rows under both variants — informational; those losses
were caused by Y's kill, which RW does not perform.

### Item 4: 12 fixed review panels

| panel | RW-E Δband | RW-G Δband (vers) | author match (any) |
|---|---|---|---|
| 9.2b | no | no (22→14) | no |
| 9.10c | no | yes, [13030.6,13090.1] (41→37) | no |
| 9.11b | no | no (35→30) | no |
| 9.17b | no | yes-ish, [13202.7,13208.4] (35→26) | no |
| 9.25a | no | yes, [13216.0,13232.4] (12→6) | no |
| 9.33c | yes, [12998.0,13075.1] | no (57→50) | no |
| 9.36c | no | no (49→40) | no |
| 9.40a | no | no (35→29) | no |
| 9.42b | no | no (29→21) | no |
| 9.48b | no | no (31→27) | no |
| 9.52a | yes, [12920.9,12927.7] | no (5→5) | no |
| 9.57b | yes, [12672.7,12698.8] | no (28→21) | no |

## Gate table (Lead's fixed rule: net>=+3, lost<=2, at-risk<=1/family,
med rewrites <= parent+1)

| gate | RW-E | RW-G |
|---|---|---|
| net box >= +3 | FAIL (-3) | FAIL (-2) |
| lost <= 2 | FAIL (4) | FAIL (3) |
| at-risk <= 1 per family | FAIL (bracket 2) | FAIL (bracket 2) |
| med rewrites <= parent+1 | pass (29 <= 30) | pass (23) |
| **verdict** | **FAIL** | **FAIL** |

## Tóm tắt (VI)

- Replay parent khớp 119/119 — mô phỏng trung thực; cả hai variant FAIL gate.
- RW-E (cluster edge): `cluster_edge` chỉ đổi opposite edge khi có wick lẻ; hiếm khi đổi — net -3 vì làm mất 4 hit sẵn có, chỉ cứu 1.
- RW-G (dtol thay DTOL=2.0): trên TUNE `dtol` luôn <2.0 → gate chỉ SIẾT (707 writes bị xoá, 0 thêm), vẫn net -2.
- 0a: sai số opposite edge không trội hơn defended trên hit set — raw-extreme không phải nút thắt chính; 0b: cả 13 pivot bị DTOL chặn và `dtol` cũng không cứu được.
- Kết luận theo §87.4: E3 dừng sinh arms; anatomy đầy đủ đã có (edge split + clause binding + 119/119 fidelity).
