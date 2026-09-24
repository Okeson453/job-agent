# AegisTriage — Challenges & Failure-Mode Design

Good source material for "how would this system handle X failing"
interview answers:

| Failure mode | Response | Fallback |
|---|---|---|
| LLM API down / quota exceeded | Circuit breaker opens after 5 failures in 30s | Deterministic rule engine handles triage until reset |
| Kafka partition leader failure | Auto-rebalance, offsets preserved | Zero alert loss — offsets commit only after processing |
| Investigation agent timeout | Temporal retries w/ backoff (3x) | Escalate to human queue with partial investigation attached |
| EDR API unavailable | Circuit breaker + dead letter queue | Response action queued for retry, analyst notified |
| Database overload | PgBouncer pooling + read-replica routing | Reads fail gracefully; writes continue on primary |

**Self-monitoring (AegisTriage watches itself):** agent action-rate
anomalies trigger automated self-audit; prompt-injection attempts route
to a security review queue; triage severity-distribution drift is
tracked and alerts the platform team if it shifts unexpectedly.
