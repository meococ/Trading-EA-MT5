# Remaining GAP — cost/tick acquire V2

Grade: `SINGLE_DAY_OR_SHALLOW_HISTORY_DIAGNOSTIC_ONLY`
Freeze eligible: **False**

## Gaps

- `quote_days=2/90`
- `EURUSD_comm=2/30`
- `USDJPY_comm=0/30`
- `slip≈0/100+_MISSING_NE_0`

## Unlock checklist

- [ ] >=90 distinct UTC quote days (Real QFSI accumulate multi-week OR broker/vendor multi-month tick tape)
- [ ] >=30 unique commission observations per primary (EURUSD, USDJPY) from Real deal history
- [ ] >=100 side-referenced fill/slip samples per primary symbol (order→fill, not deal.profit alone)
- [ ] Do not use Strategy Tester 'current' spread as research cost surface
- [ ] Bulk copy_ticks_range multi-month hangs this terminal — need chunked offline dump or vendor tape

## Not blockers (do not stall)

- Real login already connected → used opportunistically for deals+ticks.
- QFSI accumulate continues in parallel; do not kill Real to chase ceremony.
- Monetization rebuild Track B is authorized offline without this freeze.

Receipt: `80EF7C186468219D4DDB93BCB7956BD0E1F75B00877B6BE59C9E2493C91B4E70`

