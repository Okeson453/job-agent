# POLM — Key Features

- Multi-Factor Regime Classification Engine (MF-RCE) — five weighted
  dimensions, must exceed a score of 60 before any protocol activates
- SPRT-based session halt (Sequential Probability Ratio Test, 20:1
  odds-against-edge threshold) replacing arbitrary loss-count shutdowns
- Kelly-fraction-governed position sizing: 25% of optimal Kelly per
  protocol, capped 1.5% (Alpha) / 1.0% (Beta), recomputed quarterly
- Instrument-adaptive volume validation (replaces a universal 2x rule
  with real volume for futures / tick velocity for forex / z-scored
  exchange volume for crypto)
- Fractal Multi-Scale Pipeline for high-beta instruments (5-minute
  early entry, addressing a 15-minute latency bottleneck in v1.0)
