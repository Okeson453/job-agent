# Kairos Sovereign — Overview

**Source doc:** KAIROS_v2.md — "Kinetic Adaptive Intelligence for
Regime-Oriented Systematic Trading," Hardened Edition.

*Update: this doc's actual architecture is a finer-grained 11-layer
(0-10) system plus four inserted half-layers (5.5 / 6.5 / 8.5 / 9.5) —
more granular than the "4-stratum, 30-step" summary previously on file
here. Treat this as the current, authoritative breakdown.*

**Role in the unified system (per direction):** support tier — an
independently-designed system feeding direction/intelligence into the
core (Ghost Grid + Phantom Strike), not the top-level orchestrator.
Worth flagging honestly: Kairos's *own* text below describes itself as
the master doctrine unifying Ghost Grid, Phantom Strike, Void Engine,
POLM, and Arbiter-Sigma — a broader role than "support system." That's
what the document says about itself; the actual intended architecture
now treats it as support tier instead. Keep that in mind if you revisit
the source doc directly.

v2 is a direct response to 22 flaws found across 4 independent peer
reviews of v1 — both fatal contradictions (regime-detection latency
paradox, a Risk Guardian race condition, a fractional-differentiation
discontinuity) and structural omissions (no adversarial red team, no
compounding-velocity governor, no margin-aware sizing, no exchange-
downtime handling, no broker-manipulation model). Axiom count expands
7 -> 10; implementation sequence restructured to build resilience
before complexity.

**Governing principle:** know the regime before you trust the signal;
know the uncertainty before you act; know the cost before you size;
know the system's own failure modes before you deploy it, with a
recovery protocol ready before the failure happens.
