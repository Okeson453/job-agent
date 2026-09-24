# OrionSentinel — Challenges & Design Constraints

## v1's 14 non-negotiables (design constraints, not yet-solved problems
— useful as "what would you never compromise on" interview material)
Sole capital authority; Anchor Float never decreases; the 8-layer
sequence is fixed (never skipped/reordered); lot per position capped at
2.00, basket size bounded 2-5; SL/TP fixed at 10/15 pips with no
override from any source; all legs in a basket share direction/stop/
target/lot; a basket lives or dies as a unit; friction ceiling is
instrument-specific (40% XAUUSD, 15% majors, 25% indices); no recovery/
hedging/scale-in anywhere in the codebase; no streak-based size
escalation; exposure/correlation checks always evaluate the full
basket, never a single leg; signal interface is Global-Variable-only
(no sockets/DLLs/file I/O/WebRequest); every state transition writes to
the Nexus Ledger; a Kill Floor breach triggers immediate flatten, never
a throttle.

## Genuine open items (both engines, unchecked in source)
- v1 production-readiness checklist: broker `SYMBOL_VOLUME_STEP`
  verification, 4-week demo run, Layer 3/4/5/6 boundary tests, 100+
  forward-tested baskets with <10% max drawdown — **none confirmed done**
- V2 deployment checklist: `tod_matrix.csv` starts empty on first
  deploy — the Time-of-Day gate provides **no protection** until enough
  candidate-log volume exists to run `TODMatrixBuilder.mq5`; this
  window must be treated as calibration, not a protected live run
- Commission/slippage points must be set from actual broker
  statements — never left at the 0.0 default in production
