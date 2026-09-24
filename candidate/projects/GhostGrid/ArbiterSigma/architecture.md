# Arbiter-Sigma — The 10-Layer Master Pipeline

Strictly sequential state machine — a signal must pass every layer in
order; failure at any layer routes to a *named* terminal state (never a
silent drop):

| Layer | Name | Core function | On fail |
|---|---|---|---|
| L0 | Temporal Governor | AMD Killzone phase & session window & news blackout | SYSTEM DORMANT |
| L1 | Macro Regime Classifier | 4D Composite Regime Vector (HTF bias, continuous regime-state Θt, Fib premium/discount zone, volatility state) | HIBERNATING |
| L2 | Liquidity Anchor Mapping Engine | Unified pool registry (ILP, PDH/PDL, ORB, session extremes, Fib pools) | MONITOR MODE |
| L3 | Sweep Validation Engine | Penetration-depth band + close-back-inside + declining delta | MONITOR MODE |
| L4 | Order-Flow Absorption Gate | CVD divergence / L2 absorption-node / delta-reversal | ABORT (Momentum-Breakout Lockout) |
| L5 | Displacement & Structure-Shift Validator | MSS close + displacement velocity filter + volume spike -> FVG genesis | MONITOR MODE |
| L6 | Inducement & iFVG Confirmation | Mandatory inducement bait (Tranches A/B) + optional iFVG conversion (Tranche C) | ORDER CANCELED |
| L7 | Tiered Execution Matrix | 30/40/30 tranche allocation | GAP DISCARDED (staleness >30 bars) |
| L8 | Dynamic Risk & Capital Governance | Stop cascade, TP1->TP2->TP3, AuM sizing, Regime Deflector, Circuit Breaker | KILL SWITCH (engine lockout) |
| L9 | Adaptive Enhancement (Phase 2, optional) | ML confidence weighting, Iceberg/TWAP routing, spread-elasticity cancellation | non-blocking, modulates L7/L8 only |

## The 8 cross-framework conflicts it resolves (and how)
1. Fresh-FVG vs. iFVG-conversion entry -> **tranche separation** (fresh
   FVG = Tranches A/B, iFVG conversion = optional Tranche C)
2. Four competing "Layer 1" regime classifiers -> **vector
   composition**: all four become orthogonal dimensions of one
   Composite Regime Vector, none discarded
3. 50/50 vs 40/60 vs single-clip entry sizing -> **30/40/30
   three-tranche superset** absorbing all three source philosophies
4. Four incompatible stop-loss formulas -> **max-of-buffers rule**
   (larger of an ATR-based and a spread/sigma-based component)
5. Four incompatible take-profit architectures -> **sequential
   cascade** (TP1 fixed R:R de-risk -> TP2 Volume POC -> TP3 Anchored
   VWAP trail)
6. AMD Killzone phases vs. fixed session windows -> **nested gating**
   (AMD = outer/macro gate, session windows = inner/micro gate)
7. No AuM risk model vs. partial vs. full -> **layered capital
   governance** (UMLDE's fractional model as base, others as
   multiplicative modifiers on top)
8. ML classifier as hard pre-filter vs. deterministic explainability ->
   **confidence-weighting, not gating** — L9's ML layer never blocks a
   signal the deterministic L0-L8 core approves; it only modulates
   position size within already-permitted bounds
