# AegisOS — Combined-Platform Architecture

## Eight unified bounded contexts (DDD)
Identity & Access, Threat Detection, Investigation, Vault & Documents,
Policy Engine, Response, Audit & Compliance, Key Management.

## Five emergent capabilities
1. **Cryptographically Sealed Incident Evidence Packages** — every
   investigation artifact auto-sealed (SHA-256 hash, AES-256-GCM,
   per-recipient ECIES-wrapped DEK, S3 Object Lock WORM) the moment
   it's created; one HSM-signed Merkle root covers both platforms' logs.
2. **Threat-Aware Vault** — AegisShare file-access anomalies flow into
   AegisTriage's ingestion pipeline (OCSF-normalized), enabling
   full-kill-chain correlation (e.g. beacon + mass file access =
   exfiltration, not just C2 callback).
3. **Zero-Knowledge Agentic Evidence Processing** — investigation agents
   never receive vault plaintext. Analyst authorizes a scoped,
   time-limited unlock; decryption happens client-side; agent gets only
   analyst-prepared metadata extracts; every access is logged and
   cryptographically expires.
4. **Unified ABAC/RBAC Governance** — one OPA policy context spans both
   platforms (e.g. investigation-scoped, auto-expiring vault access tied
   to AegisTriage incident status).
5. **Automated Regulatory Evidence Package** — GDPR breach notification
   package (detection timeline, exposure assessment, containment
   evidence, cryptographic integrity proof) auto-generated within
   minutes of incident classification, sealed WORM.

## New attack surface (combination-specific risks)
- Agent access to vault metadata → mitigated by out-of-band analyst
  approval + 4hr-max scoped grants, agent never sees plaintext
- Cross-platform privilege escalation → unified policy grants the
  **intersection**, never the union, of the two platforms' role contexts
- Evidence package poisoning → package generation is read-only from an
  immutable, hash-chained investigation log
- Zero-knowledge boundary erosion → CI fitness function asserts
  `src/domain/vault` has zero imports from any inference/analysis module

## Hardest engineering problems (per the source analysis)
- Maintaining the zero-knowledge invariant as agent capabilities grow —
  every new agent feature must be evaluated against "does this need
  server-side plaintext access?"
- Merging two very different visual languages (AegisShare's Bloomberg-
  Terminal/Palantir data-density vs. AegisTriage's SOC-cockpit aesthetic)
  into one coherent identity without feeling welded together.

## 16-week build path (if built from scratch)
Weeks 1-3 unified foundation → 4-6 vault-as-SIEM-source → 7-9 evidence
grant system → 10-12 unified policy engine → 13-15 automated compliance
packages → 16 hardening/red-team.
