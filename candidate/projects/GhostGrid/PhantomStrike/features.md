# Phantom Strike — Key Features

- DAG-based single-arbiter architecture (replaces earlier sequential
  module-chain design)
- Echo Lock entry confirmation (distinct from the standalone Echo
  Pulse framework — see `../EchoPulse/overview.md` for the disambiguation)
- Portfolio exposure guard for multi-instrument deployments (25% of
  equity aggregate cap, independent of any single symbol's ceiling)
- Nuclear-halt synchronization between this engine's capital branch and
  any external portfolio-level circuit breaker
- Cent-account mandate with a formal execution-environment section
- Full mathematical validation section: per-trade expectancy, Kelly
  boundary, campaign-level success/ruin probabilities, signal-quality
  dependency — with a "corrected and removed claims" summary
