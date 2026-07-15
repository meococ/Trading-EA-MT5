# EA SilverBullet Build Status

- Authority: operational recovery ledger only; `04. Project Control/hot.md`
  remains the sole canonical live-scope owner.
- Goal: Focus directly on buildable `EA_SilverBullet_v2.mq5`; no Git workflow.
- Acceptance criteria: opt-in weekend-flat and max-hold controls are fail-safe,
  preserve default behavior, compile with zero errors/warnings, and have focused
  ordering/default tests plus a non-repaint audit.
- Current state: DONE for the compile-only build slice. Root Git is absent. The
  previous long-running research goal is paused; no performance verdict was
  produced.
- Latest evidence: exposure tests `3/3` pass; non-repaint static audit PASS;
  MetaEditor compile `0 errors, 0 warnings`; EX5 is `88,860` bytes with SHA256
  `CB8219D20C1E87D7D0FF004E8FAF5B7DD3C0FD9F7047CCC3C423E63C44CCCF48`.
- Current diagnosis: the EA can now enforce a broker-server-time Friday cutoff
  and a position-age cap, both default-off. The Friday `21:45` default remains
  provisional and must be bound to the intended broker session before enabling.
- Next experiment: after broker session/timezone and side-aware cost data are
  supplied, run one fixed matched Model 0 control/challenger; no parameter scan.
- Budget: no live execution, no AutoTrading enablement, no real-order mutation.
