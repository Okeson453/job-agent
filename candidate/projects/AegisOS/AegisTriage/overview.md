# AegisTriage — Overview

**Source doc:** aegistriage-enterprise-design.md (v2026 Standard —
Design Steps 1-5)

Enterprise-grade agentic AI-powered SIEM triage & autonomous
investigation platform. Philosophy: *"bounded autonomy with human
oversight"* — agents reason and act at machine speed, but every
decision stays explainable, auditable, and policy-governed. Doesn't
replace analysts; eliminates the ~80% of alert noise so analysts work
the 20% that matters.

**Stack (as specified):** TypeScript, Next.js 15, React 19, Tailwind v4,
Prisma, PostgreSQL, Kafka, Redis, Kubernetes.

**Three non-negotiable design laws:**
1. Security is structural, never additive (zero-trust from line one)
2. Autonomy is bounded — every agent action sits behind a policy,
   approval gate, or confidence threshold
3. Every decision is explainable and reversible (compensating undo for
   any automated response)
