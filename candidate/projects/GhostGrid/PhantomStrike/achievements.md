# Phantom Strike — Achievements

<!-- No live-campaign results yet. The Monte Carlo validation below is
a SIMULATED validation of the risk-cap design, not a live/paper trading
result — label it accurately if this goes on a CV. -->

- Resolved a fatal, previously-unresolved contradiction in the per-trade
  risk cap (1% hard ceiling vs. 1.5-3.0% escalation table couldn't both
  be true) via 10,000-run-per-scenario Monte Carlo validation rather
  than arguing from the formula alone — adopted a flat 2.0% cap
  (Scenario C: 96.4% campaign completion, 3.6% ruin, 0.0% timeout,
  50,722 USC median final equity vs. 32,067 at 1% and a 51.6% ruin rate
  at the unclipped 1.5-3.0% table).
