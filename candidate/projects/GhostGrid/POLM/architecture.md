# POLM — Architecture: Six Sequential Layers

| Layer | Name | Function | Output |
|---|---|---|---|
| L0 | Parameter Adaptation Layer (v1.1 new) | Weekly adaptive-bounds update via 500-trade rolling grid search | Updated alpha/beta/gamma/delta constants |
| L1 | Macro Bias Engine | Prior-day structure + Range Compression Ratio + dynamic zone mapping | PDH, PDL, dynamic zone map |
| L2 | Session Intelligence Engine | Session identity detection, session-specific ORBs | London ORB, NY ORB, session score |
| L3 | MF-RCE (regime classifier) | Five-factor weighted regime classification | Protocol state: Alpha / Beta / Gamma / Null |
| L4 | Signal Validation Engine | Instrument-adaptive volumetric + morphological filters | Valid-signal bool + EV score |
| L5 | Execution & Management Layer | Kelly-sized entry/SL/TP, fractal pipeline for high-beta instruments | Sized order + exit logic |
| L6 | Correlation Risk Layer (v1.1 new) | Portfolio-level correlated risk aggregation | Portfolio risk bool |

## Three protocols
- **Protocol Alpha (Mean Reversion)** — session opens inside prior
  range, attempts mean reversion at structural extremes
- **Protocol Beta (Bracket Expansion)** — failure to hold at extremes
  converts to expansion; ORB is the intraday timing catalyst
- **Protocol Gamma (Liquidity Sweep, v1.1 new)** — price appears to
  break out but returns inside the box; replaces v1.0's Anti-Chop
  immediate flip with a two-bar buffer + TRANSITION state, producing
  the system's highest-quality reversal entries

## v1.1's key hardening moves over v1.0
Fixed constants -> adaptive weekly-grid-search bounds; single-metric
regime path integral -> five-factor weighted MF-RCE; "2 consecutive
losses" halt -> SPRT statistical test + 3% drawdown circuit breaker;
theoretical EV point estimates -> rolling 100-trade realized metrics
with bootstrap confidence intervals; per-instrument-only risk ->
portfolio Correlation Risk Layer with a 3% portfolio cap.
