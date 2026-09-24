# AegisTriage — Architecture

## Multi-agent system (the agentic core)
Not a monolithic LLM call — a supervised pipeline:

```
ALERT QUEUE (Kafka) -> SUPERVISOR AGENT (routes, enforces autonomy
policy, human-escalation threshold)
  -> TRIAGE AGENT (severity classification, FP filtering, confidence)
  -> ENRICHMENT AGENT (MISP/OTX, VirusTotal, MITRE ATT&CK mapping, CVE)
  -> INVESTIGATION AGENT (log queries, ATT&CK timeline, attack graph,
     IOC clustering)
  -> RESPONSE AGENT (playbook generation, human gate on HIGH/CRITICAL)
  -> REPORT AGENT (executive PDF, technical MD, SIEM ticket, confidence
     citations)
```

Each agent has an explicit, minimum-necessary tool-access policy (e.g.
the Triage Agent can read alert data and run the classifier but cannot
write state or call external APIs; the Response Agent can execute
pre-approved actions with a human gate but cannot modify the playbook
library or take bulk actions).

## System-level patterns
Hexagonal architecture (non-negotiable baseline) + Domain-Driven Design
bounded contexts + event-driven backbone + CQRS (separate alert
write/query paths) + event sourcing (the audit log as first-class
architecture) + saga pattern for distributed investigation workflows +
API gateway/service mesh.

## Core aggregates
- **Alert** (Ingestion context root) — source, severity, ATT&CK tactics,
  indicators, OCSF-normalized
- **Investigation** (event-sourced) — immutable append-only event log,
  attack timeline, confidence, full agent decision chain
- **Playbook** (Response context root) — trigger conditions, ordered
  steps each with a compensating action, required approval level
  (AUTO/ANALYST/MANAGER/CISO); agent-generated playbooks must be
  human-reviewed before `canAutoExecute()` returns true

## Resilience hierarchy
Prevent (circuit breakers on every external call) -> Detect (health
probes, queue-depth alerting at 70%/90%) -> Recover (graceful
degradation to rule-based triage if the AI engine is down; retry with
backoff+jitter; bulkhead isolation per integration) -> Learn (monthly
chaos engineering, every production failure gets a runbook + synthetic
test).
