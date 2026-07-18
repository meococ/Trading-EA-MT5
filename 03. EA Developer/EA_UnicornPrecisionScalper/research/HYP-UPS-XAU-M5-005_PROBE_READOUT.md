# Probe readout — HYP-UPS-XAU-M5-005

## Decision

`PASS_BUILD_AUTHORIZED`. This decision authorizes only implementation, compile
and non-repaint audit of the single frozen event-anchored sweep-state change.
It is not profitability evidence and does not authorize Model 0 until the
canonical source, registry and task packet are hash-bound.

## Frozen identity

- Prereg SHA256:
  `4EAC24C05589B94AF0E6A5B208949AB6A9A98B93F9E8D0AE4C58234DB0F45315`.
- Probe script SHA256:
  `FA335842F4AC3EFE3A1C3C98A4CB7450BD1BCB943AB3681812EEE53C55D0F573`.
- Probe artifact SHA256:
  `35CE76496A67D8698091518D935BB3BAFBC856AA97D569ED9FD4582A9BCB5494`.
- Casebook SHA256:
  `0AA3D254148DC6445CB4730AFBBF6AF7CA3F893A05DA437FC3350869298FED60`.
- Window: `2024.01.01`–`2025.12.25`; 2026 remains untouched.
- Terminal data path:
  `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent`.
- Raw bars persisted: `false`; forward outcomes evaluated: `false`.

## Result

- Event-anchored challenger: `251` candidates, `2.42345` per elapsed week.
- Matched fixed-four-bar control: `159`; additional candidates: `92`.
- Direction: `205` long / `46` short; active months: `24`.
- Structurally valid late states: `120` (`47.81%`); maximum observed state age:
  `90` M5 bars within the frozen UTC session.
- Candidates emitted after invalidation: `0`.
- Deterministic no-outcome casebook: `200` rows.
- All nine preregistered probe criteria passed.

## Interpretation and limit

The fixed four-bar expiry was materially suppressing otherwise valid closed-
bar structures. The probe demonstrates opportunity density and state-machine
separation only. It says nothing about fill quality, expectancy, PF or
drawdown. Those remain falsification questions for a one-shot Model-0 matched
comparison after build gates pass. No threshold or session change is allowed.

