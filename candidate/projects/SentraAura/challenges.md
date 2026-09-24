# SentraAura — Challenges & Design Decisions

**The doc explicitly replaced an earlier "recommended + open-ended
alternatives" tech-stack format with single, committed choices plus a
named migration trigger** for each — e.g. NATS JetStream now, "migrate
to Kafka when sustained throughput or exactly-once/long-retention
requirements exceed it, keep the bus-agnostic Event Schema Registry
unchanged." This is a good example of turning an exploratory spec into
something an implementation team can actually build against — worth
citing as a documentation/architecture-process decision on its own.

**Explicit non-goals / deferred infra:** Neo4j, Qdrant, and Kafka are
all named as the *next* step, not the starting one — each deferred
until a specific, measurable threshold is hit, avoiding speculative
infrastructure.
