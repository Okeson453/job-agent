# OrionSentinel — Overview

**Source docs:** OrionSentinel_Technical_Design_v1.md,
OrionSentinel-V2-Ready.zip (52 files: MQL5 EA + Includes + config +
validation-protocol test scripts + install docs)

A two-engine MT5 system, team **Okeson Systems** (per source code
copyright header):

- **OrionSentinel v1 — "The Fortress"** — deterministic, fixed-rule
  capital-management and execution engine (native MQL5). Receives trade
  proposals over a RAM-resident Global Variable interface, runs each
  through an 8-layer guard stack, and opens 2-5 identically-parameterized
  positions as a single basket. $15 cent-account, 10-pip stop/15-pip
  target, 0.03 lot per position, 1:1.5 R:R.
- **OrionSentinel V2 — "Signal Generation & Transport"** — the signal
  side. No scoring/gating logic of its own; loads config and
  orchestrates a fixed pillar-fusion gate sequence, then commits a
  Composite Conviction Score (CCS) to the V1 Fortress via the same
  Global Variable interface.

V2 is explicitly the *companion* to v1, not a replacement — confirmed
in the EA source header: `Companion: OrionSentinel v1 (The Fortress)`.
