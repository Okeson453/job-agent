# Echo Pulse — Overview

**Source doc:** ECHO_PULSE_Framework.md — "Master Engineering
Blueprint v1.0"

A 12-tier, 19-core probabilistic decision engine (22 modules counting
governance/capital extensions) that converts raw tick/candle data into
a calibrated probability distribution over pip-displacement outcomes,
gates it through hard microstructure and macro-risk vetoes, fuses the
survivors into one confidence score via a hysteresis-governed state
machine, and routes execution to one of five specialized strategy
agents — under a continuous feedback loop and a hard risk shield with
final veto over every other component.

**Core rule, inherited from all 7 synthesis sources:** no single
indicator, oscillator, or heuristic may independently trigger a trade —
every signal must survive contextualization, confirmation, and
validation before reaching fusion.

**Synthesizes 7 prior architectures** into one non-redundant,
implementation-grade design: PHANTOM PMDE-X, the Hybrid Pip-Movement
Concept, OKP-TEA, AVPTF, the PMDE Scoring Engine, the PMDE Layer 0-4
Blueprint, and **VECTOR PULSE ENGINE (VPE)**.

**Disambiguation — this is NOT the same thing as Phantom Strike's
"Echo Lock":** `../PhantomStrike/` has its own, smaller "Echo Lock"
entry-confirmation submodule (candle-boundary + CVD slope + spread-
spike checks via Schmitt hysteresis) — similar name, different scope.
Echo Pulse is the full standalone pip-movement framework.

**Role in the unified system (per direction):** support tier —
independently designed to feed additional direction/intelligence into
the core (Ghost Grid + Phantom Strike), not a core peer. It explicitly
absorbs "VECTOR PULSE ENGINE," which earlier Phantom Strike notes named
as a SIGMA FILTER feeder — the most plausible concrete path once this
gets reconciled with the core at implementation time, but not yet
built or wired up.
