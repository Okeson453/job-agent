# AegisOS — Overview

**Source doc:** aegisos-synthesis-analysis.md

AegisOS is what emerges when two independently-specified enterprise
security systems — **AegisTriage** (agentic SIEM triage) and
**AegisShare** (zero-knowledge secure file sharing) — are combined. The
two solve opposite ends of the same problem: AegisTriage asks "what's
happening right now and what do we do about it," AegisShare asks "how
do we handle sensitive artifacts without ever exposing them." Security
incidents always produce sensitive artifacts, so the combination closes
a real gap: every AegisTriage investigation output gets cryptographically
sealed into AegisShare's zero-knowledge vault, and AegisShare's file
access anomalies become threat signals AegisTriage can reason about.

**Category positioning:** "Zero-Knowledge Agentic Security Intelligence
Platform" — not a SIEM, not a file-sharing tool. Tagline: *"From first
signal to signed evidence — unbroken."* Visual identity: "Cryptographic
Noir" — Sovereign Gold (#F5C842), Operational Cyan (#00D4FF).

See `AegisTriage/` and `AegisShare/` for the two component specs.
