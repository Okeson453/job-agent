# Phantom Strike — Architecture

## Structural model: one graph, one state object, one arbiter
Replaces an earlier long sequential call-chain design with a DAG of
evaluation branches converging on one shared tick-context object,
resolved by exactly one arbitration stage:

```
ACTIVE SUPERVISORY ENGINE (ASE): Health Vector -> Mode Classifier ->
  Bounded Parameter Broadcast (continuous, read by every branch)
        |
   MARKET branch        SIGNAL branch           CONFLUENCE branch
   (ODE, elastic VIW,   (Ghost Grid H_c/        (volume weight, CVD
    micro-regime)        C-Score, Echo Lock,      divergence, MTF
                          Pulse Probe)             alignment, adaptive
                                                    friction)
   [all three run concurrently; arbiter waits only for the slowest]
        |
   CAPITAL branch (Risk-Budget State Machine) -- sequential, after merge
        |
   GOVERNANCE branch (8-Layer Guard + risk constant) -- sole arbiter,
        ALWAYS LAST, ALWAYS FINAL
        |
   Execution Abstraction Layer (broker-agnostic)
```

Any branch may propose a lot adjustment; **only GOVERNANCE resolves
competing proposals into the final order size** — a structural fix for
a defect tolerated in earlier module-chain designs (undefined override
order between conviction sizing, partition constraints, and mode caps).

## Unified Signal Intelligence (USIL)
Ghost Grid H_c (external authority) + C-Score (deterministic mechanical
signal quality) -> Composite Conviction Score (CCS) -> regime
micro-state refinement -> **Echo Lock** entry confirmation -> signal
confluence stack -> Opportunity Density Engine (ODE) with elastic
execution windows -> standalone-signal fallback path.

## Unified Capital Dynamics Engine (UCDE)
Risk-budget state -> volatility-adjusted position sizing core -> streak
elasticity -> anchor float -> streak insurance -> friction rate
gateway -> compound lock -> Capital Continuity Reserve (CCR) ->
dynamic capital partitioning -> adaptive profit lock -> precision
sizing (verified high-conviction setups only).

## Active Supervisory Engine (ASE)
Health vector + composite score -> mode ladder (Full Velocity 90-100 /
Standard 70-89 / Defensive 50-69 / Preservation 30-49 / Suspension
0-29, plus event-triggered Reserve-Active/Recovery states) -> bounded
parameter adaptation.

## Resilience
Audit trail, shadow ledger for degraded-connectivity mode, execution
abstraction across 4 gateway implementations, an explicit engineering
risk register.
