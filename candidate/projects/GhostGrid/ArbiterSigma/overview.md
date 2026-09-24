# Arbiter-Sigma — Overview

**Source doc:** ARBITER_SIGMA_Unified_Architecture.md — "The Unified
Macro-Microstructure Liquidity-Displacement Governance Architecture"

**Core function:** four independent frameworks (AMIE, USLM, RFDA,
UMLDE) each solved the same problem — raw SMC/ICT price-action concepts
(liquidity sweeps, Fair Value Gaps, Market Structure Shifts, AMD
cycles) are too noisy and discretionary to trade systematically — the
same way, with a hierarchical macro-governs-micro gating pipeline, but
each solved it *differently* and each is incomplete somewhere else. Run
together naively they collide on 5 axes: which FVG gets traded, which
of 4 regime classifiers is authoritative, 3 conflicting entry-sizing
splits, 4 conflicting stop-loss formulas, and 4 conflicting take-profit
architectures.

**Arbiter-Sigma is the resolution** — not a fifth competing framework,
but a re-sequencing of all four into one 10-layer pipeline where every
cross-framework conflict becomes a precedence rule instead of a
contradiction. Nothing from the four source documents is discarded;
everything is re-deployed into the layer where it actually belongs.

**Role in the unified system (per direction):** support tier — an
independently-designed system built to feed additional direction and
intelligence into the core (Ghost Grid + Phantom Strike), not a peer
with equal standing. It was designed separately from the core, so its
own risk/capital model (AuM-based sizing, its own stop and TP cascades)
was never reconciled against Ghost Grid's or Phantom Strike's guard
stack — that reconciliation is deferred to actual implementation. This
document itself contains zero mentions of "Ghost Grid" — see
`../architecture-unified-system.md` for the full picture.
