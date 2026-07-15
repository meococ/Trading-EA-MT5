# ATR-trail tick-proxy — offline probes

Receipt: `1626718918088C2ED1EB1F24DD879BDB0ADA48338DADDACBB80E042923855B3B`
Baseline: N=524 PF=1.3794 tpw=2.0099 x1.5=1.0134

Method: tick unavailable → MFE-envelope (authority) + M1 path proxy (labeled).

| ID | N | PF | tpw | x1.5 | lift | Verdict | notes |
|---|---:|---:|---:|---:|---:|---|---|
| `HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001` | 524 | 2.5323 | 2.0099 | 1.8099 | 0.7965 | `PROBE_SURVIVOR` |  |
| `HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001` | 524 | 2.2173 | 2.0099 | 1.5918 | 0.5784 | `PROBE_SURVIVOR` |  |
| `HYP-RR2-EXIT-ATRTRAIL-M1PATH-ARM075-K15-001` | 524 | 1.55 | 2.0099 | 1.1151 | 0.1017 | `KILLED_AT_OFFLINE_PROBE` | stress_fail |

Model 0: **AUTHORIZED**

