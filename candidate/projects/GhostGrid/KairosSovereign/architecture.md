# Kairos Sovereign — Architecture (Layers 0-10 + half-layers)

| Layer | Name | Core content |
|---|---|---|
| 0 | Temporal Integrity Foundation | Four-timestamp schema, provenance hashing, exchange-gap handler |
| 1 | Chrono-Causal Ingestion Fabric | Immutable event log, PIT bi-temporal indexing, consensus scoring, broker reliability fingerprinting |
| 2 | Multi-Resolution Event Bus | Kafka spine, bounded-staleness watermarking, synthetic no-trade bar emission |
| 3 | Stationary Feature Manifold | Feature DAG (bounded-staleness), regime-anchored frac. differentiation, entropy gate, Bayesian deprecation, 5 feature families (A-E) |
| 4 | Label Architecture | Fill-distribution-sampled labels, L2-informed + margin-aware costs, probabilistic tier promotion |
| 5 | Regime Intelligence Engine | HMM+GMM+PELT+CUSUM hierarchy, regime transition forecast, regime amnesia buffer |
| 5.5 | Adversarial Red Team (NEW) | 24/7 automated adversary, manipulation simulator, data-poisoning attacker, counter-strategy generator |
| 6 | Adaptive Model Parliament | Six ministers, inference timeout gate, uniform information sets, EWC online learning, decision attribution matrix |
| 6.5 | Epistemic Uncertainty Quantifier (NEW) | MC Dropout ensembles, VAE-based OOD detection, SHAP divergence index |
| 7 | Evidence Accumulation Engine | Bayesian log-Bayes factors, online regime-conditioned base rates, latency-aware confidence decay |
| 8 | Execution & Slippage Bridge | Digital twin, L2 replay, RL execution agent |
| 8.5 | Ghost Grid Execution Mesh (NEW) | Broker latency fingerprinting, anti-stop-hunt positioning, stealth order construction, funding-rate arbitrage. *(Kairos's own internal execution-layer concept — distinct from the parent `../` (Ghost Grid) MT5 scalping project this now sits under; same name, different system.)* |
| 9 | Nuclear Risk Guardian | State-versioned signal evaluation, margin-aware Kelly sizing, 5 constraints + correlation kill-switch + liquidity gate, synchronous inline (race-condition fix) |
| 9.5 | Compounding Velocity Governor + Phoenix Protocol (NEW) | Tier friction coefficients, profit lockbox, variance budget, automated post-mortem, confidence-rebuild sequence |
| 10 | Continuous Learning & Observability | Drift-triggered retraining, priority compute queue, incident log as training data, Omega Loop |

**Feedback loops:** synchronous inline feedback to the Risk Guardian
(<10ms, state-versioned); async feedback to Regime + Feature layers
(<50ms); Omega Loop runs a daily pre-computation feeding Layer 9's
survival config.

## Ten design axioms (v1's 7, expanded)
Regime Supremacy; Temporal Sanctity; Adversarial Humility; Ensemble
Democracy; Signal Purity Over Model Complexity; Capital Preservation as
Primary Objective; Explainable Death; the Adaptivity-Rigor Trade-off Is
Measurable (NEW); the System Must Survive Itself (NEW); Complexity Is
Managed, Not Celebrated (NEW — every component has a Minimum Viable
fallback).
