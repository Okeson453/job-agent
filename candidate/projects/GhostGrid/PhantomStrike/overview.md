# Phantom Strike — Overview

**Source doc:** Phantom_Strike_Technical_Design_V1.md — "the single,
authoritative technical specification," consolidating four prior
incremental design iterations into one coherent architecture. No prior
version numbers (v1.0/v1.1) are referenced in this doc; this supersedes
the earlier module list recorded from memory in this scaffold (VAVE,
SSM, VIW, AFP, SIM, FRG, CLP, SIGMA FILTER, PULSE PROBE, VAULT SHIELD,
APEX LENS) — treat this document as current and authoritative going
forward.

An automated capital-deployment engine that consumes a signal feed from
Ghost Grid (external signal authority: H_c confluence score, regime
classification, exit logic) and converts it into position-sized,
risk-governed trade execution on a cent-denominated MT5 account.
Five-day campaign structure, $10 -> $500.

**Scope boundary (structural, repeated throughout the doc):**
1. Signal authority is external — Phantom Strike may weight/filter/gate
   on Ghost Grid's signals but never alters Ghost Grid's own logic
2. The guard stack is the unconditional final arbiter — no adaptive or
   conviction-weighted component anywhere may touch the kill floor,
   reserve-trigger, guard-stack thresholds, or per-trade risk constant
