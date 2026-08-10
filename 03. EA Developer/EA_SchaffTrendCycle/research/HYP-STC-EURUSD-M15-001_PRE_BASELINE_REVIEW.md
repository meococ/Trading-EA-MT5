# HYP-STC-EURUSD-M15-001 pre-baseline review

Verdict: `PASS_ONE_UNTUNED_MODEL0_BASELINE`.

Scope is engineering correctness only. No market outcomes, PF, validation,
holdout or promotion evidence were opened during this review.

- Source SHA256: `3FA2B8765E2ABD6F04BAE3F442E4696CDD2916BCFE9D9444F9232FAB17A5AF64`.
- EX5 SHA256: `11C8FC944D4AE530AAB20435608D9D57110B01CC5C6D66023ED095080322F8EE`.
- Compile log SHA256: `0412578B980D6A2B1A3A24D43AF061067475EA6598288062CAF578DF5A683F86`; exactly one `Result: 0 errors, 0 warnings`.
- Frozen prereg SHA256: `EBB58B99D5B89222BD3E51E3AC84AED65EAAF2B7E4B40E30DE64B8C5D0397310`.
- Focused test SHA256: `9E124A5FB9C7FE78F7744C1DD0689A1EAD268EB4635B3DD49ED6B5208427D49D`; `11/11` PASS after the final compile.
- Preload-origin proof SHA256: `2F8CFEA7F6370857BFB54DDF1D6422ED7E10EB072767052BBB3EC582C649F16C`.
- Non-repaint manifest SHA256: `8ACD71AFFC454A89968522D253BDD135F354AF29EEED38E586A0FA3E7175F6F3`.
- Non-repaint audit SHA256: `045D3D976E1F953DF33CC28E4CAAC5C38CE6D9E4EB42C2EB6C795CB4EC795866`; status `PASS`, zero findings.
- Cost source manifest SHA256: `7502CE78093562690B2E5D75D3FE58FD890314A7BF4459C9BB7304FEF20F9260`; research-proxy only.

The independent reviewer first rejected a rolling-window STC recurrence and
then a preload check that allowed late history. Both were fixed before any
baseline: the current source requires synchronized history, exact first/last
server timestamps, exact `24,776`-bar population, strictly increasing bars and
one recurrent update per completed M15 bar. The final independent verdict is
`PASS_PRE_BASELINE`, with no remaining fatal formula, signal, risk, lifecycle
or lookahead blocker in this bounded review.

Authorized next action is exactly one EURUSD M15 Model-0 DESIGN baseline over
`2016.01.04-2021.01.01`, with no optimization or same-ID economic retry. A run
failure is engineering evidence; a completed admissible report must receive an
immediate economic verdict before any further work.
