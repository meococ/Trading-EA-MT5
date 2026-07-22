# EA_VRAS_RegimeAdaptiveScalperV2

Terminal HYP-VRAS-EURUSD-M5-002 engineering record. It preserves the complete
seven-gap VRAS signal/risk surface and corrected `OrderCheck()` contract, but
its bound attempt stopped at OnInit because the identity guard still required
HYP-001/magic 5600741. No market bars, trades or economics were produced.

Research defaults are safe: automatic trading is disabled outside Strategy
Tester, all decisions are closed-bar, and all produced evidence is explicitly
diagnostic-only because cost/news provenance is not promotion-grade. Source is
retained byte-identical for audit and must not be rerun.
