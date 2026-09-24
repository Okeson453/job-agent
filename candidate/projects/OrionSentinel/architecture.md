# OrionSentinel — Architecture

## v1 "The Fortress" — capital/execution engine
```
KERNEL: TickRouter, StateMachine, NexusLedger, Logger, TimerDispatcher
  -> SIGNAL GATE (reads Global Variable every tick: stale check, score
       >=75 check, checksum, duplicate check; basket size from score:
       75-79->2, 80-84->3, 85-89->4, 90-100->5)
  -> 8-LAYER GUARD STACK (basket-aware, not per-leg):
       L0 Equity Guard, L1 Exposure Limits, L2 Anchor Float,
       L3 Position Lot Table, L4 Parameter Gate, L5 Drawdown Throttle,
       L6 Friction Resistance Gateway, L7 Instrument Precision Guard
  -> EXECUTION SPINE (simultaneous multi-order dispatch, staggered
       entry, retry FSM, unit-closure monitor)
  -> CONSTELLATION ENGINE (ACTIVE/LOCKED/FLATTENING states — basket
       lives or dies as a unit; any SL close closes every leg)
  -> POST-TRADE & PERSISTENCE (Anchor ratchet-only update, pipe-
       delimited Nexus Ledger write)
```
Design principles: fail-closed, deterministic state, strict custody
boundary (this engine is sole capital authority — upstream V2 only
ever proposes), Anchor Float never decreases, tables over formulas
wherever money is involved, a basket (not a position) is the unit of
risk, and structural exclusions (no recovery, no hedging, no scale-in,
no streak-based size escalation — not disabled features, absent code
paths).

## V2 "Signal Generation & Transport" — CCS pillar-fusion engine
```
OnInit/OnTick -> Pillars (weighted): Structure (30%) + Momentum +
  Liquidity + RegimeSession -> DXY Alignment -> Fusion (ComputeCCS(),
  graduated compression ladder, graduated move curve, trigger-depth
  coding) -> ConfirmationGate -> TargetPath -> CostFilter ->
  RateDiscipline -> SignalCommit (writes CCS + basket-size hint to the
  Global Variable v1 reads)
```
CCS bands (per the deployment checklist): ELITE >=88, Standard below
that, plus compression-flagged and dead-zone-flagged candidates tracked
separately in the weekly review cadence.
