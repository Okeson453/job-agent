# Full Candidate Answer Bank

Canonical answer/evidence layer for the autonomous job-application agent.

## Evidence states
- VERIFIED_FACT — fixed candidate fact.
- VERIFIED_TEMPLATE — approved reusable wording grounded in facts.
- GENERATED_FROM_EVIDENCE — LLM may draft, but claim validation is mandatory.
- MANUAL_REVIEW — candidate approval is required.
- NEEDS_VERIFICATION — blocked from automatic submission.

## Hard rule
The agent must never upgrade a project from concept/design/research to implemented/deployed without source evidence.

Sensitive fields such as authorization, visa, citizenship, criminal/background questions, compensation, employment dates, certifications and references are fail-closed.
