# HYP-STBS-XAUUSD-M15-004 — Comparator failure

Status: `KILL_EXACT_ORDERS_HEADING_ENCODING_PREDICATE`

Attempt: `STBS004-COMPARATOR-001` (consumed; no retry)

## Evidence

- Screened authority raw SHA256: `CE2558662D065F01C6CD926EBE380252D023096020E431E7D42A0E650DA7F85B`.
- Attempt start SHA256: `50D5C69C6DB4A5D60180C7ACB56A6901AC679B12FDE5A924164561553148534F`.
- Failed terminal SHA256: `905A1C5C899F52B3EF879A95563C462A250E6D73CC810F39CEB40536B93CA16D`.
- Attempt chronology: `2026-08-09T06:14:19.601684Z` to `2026-08-09T06:14:19.624735Z`.
- The attempt root contains exactly the start and failed terminal. No comparator report or success receipt exists.

## Exact failure

The claimed comparator captured and hash-validated its frozen inputs, then stopped at `orders_section_is_empty()` with `ValueError: report Orders section is not exactly empty`.

The exact UTF-16 report contains the Vietnamese section heading `Các lệnh đặt`, followed by the already frozen zero-order structure: one 11-cell bold header with colspan vector `[1,1,1,1,2,1,1,1,2,1,1]` and logical sum 13, then exactly one empty spacer cell before `Deals`. The HYP004 source literal for the Vietnamese heading was mojibaked, so the heading search failed before the structural checks could run.

## Verdict boundary

This kills only the HYP004 locale-heading predicate. It does not reject the HYP003 MT5 audit, signal identity, ATR/geometry logic, data quality, zero-order fact or any market/economic property. HYP004 opened no AlphaFactory run, compile, MT5 process, source acquisition, order, outcome, performance metric or economics. Same-ID retry is forbidden.

HYP004 did not reach the Orders structural checks or journal/oracle/geometry comparison; those contracts remain unadjudicated by HYP004.

A fresh comparator-only revision may change only the exact Orders-heading recognition, keep the English `Orders` alternative, retain the exact structural empty-section checks, and preserve all prior BOM, provenance, dual-clock, journal, geometry, zero-authority and one-shot contracts.
