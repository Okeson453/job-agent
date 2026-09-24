# AegisTriage — Key Features

- Six-agent pipeline: Supervisor, Triage, Enrichment, Investigation,
  Response, Report — each with an explicit tool-access policy
- SOC Dashboard, Auth Screen, Design Tokens (Figma, pending approval)
- Visual design system built for cognitive load under pressure: dark
  theme default, severity color tokens carry semantic meaning only,
  WCAG 2.2 AA, fully keyboard-navigable incident queue
- AI-specific zero-trust controls: prompt-injection detection on every
  input, sandboxed tool calls, schema-validated agent output, full
  input/output logging on every LLM call
- Graceful degradation to a deterministic rule engine if the LLM API is
  unavailable
