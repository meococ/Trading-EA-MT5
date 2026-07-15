# Offline SB + Spark Deposit=100000 Book Join V1

Generated: 2026-07-14 19:39:07 ICT
Result SHA256: `10FA68A325F27B18CE875526699DD7786E694136C297070200A450E4C8DF8E44`

## Spark capital twin

- 10k run `20260714_002614`: N=325 PF=1.3053 net=1099.38
- 100k run `20260714_193358`: N=325 PF=1.3804 net=9350.59
- Report SHA256: `8E655DB0E5537F99CEB9ED7560D472FC8F45E6D862F5495A0B965D82BBDE9357`

Deposit=100000 twin landed run 20260714_193358; N identical 325; PF rose 1.31->~1.38; net ~8.5x not 10x so CAPNORM×10 was imperfect.

Alpha closeout threw includes_sha256 mismatch after report ready; artifacts kept; analyze completed.

## Honest books (no CAPNORM)

| book | N | PF | tpw | net | PF@$2 | PF x1.5 | PF x2 | old CAPNORM PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `BOOK-A1-SPARK100K` | 845 | 1.363 | 3.2411 | 17226.52 | 1.3217 | 0.9086 | 0.6815 | 1.3204 |
| `BOOK-MAXKZ2-SPARK100K` | 871 | 1.3572 | 3.3408 | 17473.68 | 1.316 | 0.9048 | 0.6786 | 1.3168 |

Still UNVERIFIED_TESTER_DEFAULT. GOAL unmet. Do not mine hour-11 weakness.

