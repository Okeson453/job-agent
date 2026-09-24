# TestingEngine — Key Features

## ACIE — Adaptive Crash Intelligence Engine
The authoritative live scorer once history is warm (>=5 observed
rounds):
- Multi-model PSI ensemble with online weight updates
- Optional Platt calibration when it improves rolling Brier score
- Strategy layer: ENTRY / REDUCED_ENTRY / SKIP
- Live selectivity via `MIN_SIGNAL_EDGE` plus an **adaptive edge**
  learned from realized signal outcomes
- Ensemble disagreement gate (`ACIE_MAX_DISAGREEMENT`) — skips when the
  models disagree beyond a configured threshold

Fallback: a separate `PredictionEngine` + feature-engine stack runs
when ACIE itself is unavailable, with explicit `FALLBACK_BASELINE`
provenance tagging so degraded predictions are traceable.

Default strategy mode is `quality` (threshold >= fair + edge); a
high-frequency mode is available via `ACIE_STRATEGY_MODE=hf`.

## Correctness contracts (the README's own list)
1. Correlation — exactly one unmatched pending prediction per target round
2. Temporal — `generated_at` before target start; dispatcher refuses
   late sends; BG kills stale outbox rows
3. History — N+1 history includes completed source N, never the
   target round's own crash
4. Idempotency — ED dedup by game id; feedback claimed once per prediction
5. Authority — non-authoritative workers drop mutation roles after
   losing the fence
