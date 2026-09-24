# SentraAura — Architecture

## Core operating loop
`Discover -> Create -> Produce -> Clip -> Publish -> Measure -> Learn ->
Optimize -> Repeat`, with a tighter, canonical self-improvement loop
inside "Measure -> Learn -> Optimize":
`Observe -> Measure -> Diagnose -> Hypothesize -> Experiment -> Measure
-> Learn -> Adapt`

## Multi-agent architecture (30 agents, 6 domain groups)
Intelligence, Creative, Production, Clipping, Distribution, Operations
— each agent communicates via a defined Agent Communication Contract
(§4.1); a consolidated agent catalog with per-agent escalation/failure-
recovery rules (§4.2-4.3).

## Content Asset Graph
A lineage/provenance graph (node types, edge types, Cypher-style
provenance queries) tracking every asset from research input through
every derivative clip/thumbnail/title back to its source — this is
what makes the "many derivative assets from one long-form video" model
auditable rather than just a batch pipeline.

## AI Clipping Engine (§6) — a named subsystem in its own right
Semantic segmentation -> feature/composite clip scoring -> candidate
generation -> context reconstruction/completeness check -> ranking,
selection, duplicate control -> automatic hook reconstruction ->
vertical reframing -> captioning. Scores clips on semantic importance,
narrative completeness, retention potential, emotional intensity,
novelty, hook strength, quotability, and contextual boundaries.

## 6-batch dependency-ordered development plan (chosen approach)
1. Foundation / contracts / shared packages
2. Control & state layer services
3. Agent-runtime: intelligence + creative + production agents
4. Agent-runtime: clipping + distribution + operations agents + media pipeline
5. Support services + evals
6. Infra / CI-CD / ops

## Provider-agnostic AI architecture
Capability interfaces (§11.1) abstract every AI capability (LLM, TTS,
image, video, transcription) behind a common interface; a Provider
Gateway (§11.2, LiteLLM) handles routing; cost/quality tiering by task
type (§11.3) picks cheaper/faster models where task quality tolerance
allows it.

## Orchestration
Temporal as the durable workflow engine (replay-from-checkpoint, saga/
compensation semantics) — explicitly called "load-bearing, not
nice-to-have" given the multi-hour, multi-stage nature of a single
video's production pipeline.
