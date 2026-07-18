# Gold Macro Pulse external data

Research-only, public primary-source panel for a causal cheap probe.

- `DFII10.csv`: Federal Reserve Board H.15 10-year inflation-indexed Treasury
  constant-maturity yield, retrieved through FRED series `DFII10`.
- Official series page: `https://fred.stlouisfed.org/series/DFII10`.
- Raw CSV endpoint:
  `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10`.
- The H.15 release is posted at 16:15 U.S. Eastern on business days. The probe
  therefore uses an observation only on the following business day; it never
  trades from a same-day H.15 value.

The downloaded file is immutable input. Its SHA256 and retrieval timestamp are
bound in the hypothesis prereg and result packet. No FRED value is treated as
known before its declared availability date.

