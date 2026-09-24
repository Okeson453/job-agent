# candidate/ — Personal Career Data Repository

## What this is
A single source of truth for every fact about you that a job application,
a CV, a cover letter, or an AI agent filling out a form might need.
Nothing here is "the CV" itself — CVs/cover letters are *generated from*
this data (see cv_profiles/ and cover_letters/). This repo is the raw
material: atomic, sourced, and verifiable.

## Design concept
- **YAML = structured fact.** Anything with a type (date, number, enum,
  list, boolean) goes in .yaml. Keys are stable identifiers a script or
  agent can query directly (`skills/programming_languages.yaml` ->
  `languages: [...]`). Never bury structured facts inside prose.
- **Markdown = narrative.** Anything that needs sentences — a project
  story, a bio, a challenge you solved — goes in .md. H1 = title,
  H2 = fixed section headers (don't rename them; scripts may key off them).
- **One concern per file.** Don't merge `frameworks.yaml` and
  `programming_languages.yaml` even though they overlap conceptually —
  each file should answer exactly one question.
- **snake_case** for filenames. **PascalCase** for project directory
  names (must match the project's real/product name, e.g. `OrionSentinel`).
- **Every claim is traceable.** Anything that could be challenged in an
  interview (a metric, a claim of scale, a "led a team of X") should have
  a matching entry in `metadata/source_registry.yaml` pointing at
  `evidence/`. Unverifiable claims get flagged in
  `metadata/verification_status.yaml`, not deleted — you decide whether
  to use them.

## Fill order (recommended)
1. `identity/` + `profile/` — who you are, 15 min.
2. `skills/` — pull straight from your actual stack; don't pad.
3. `experience/` + `projects/` — the bulk of the work. One project dir
   per real venture (you already have material for OrionSentinel,
   SentraAura, and your Crash-automation work — port summaries in,
   don't re-derive from scratch).
4. `achievements/` — only claims with a number or a verifiable outcome.
5. `preferences/`, `compensation/`, `availability/`, `work_authorization/`
   — the fields every application form asks for; fill once, reuse forever.
6. `answer_bank/` — canned, honest answers to recurring interview/
   application questions, so you're not re-writing "why do you want this
   role" every time.
7. `cv_profiles/` + `cover_letters/` — generated *last*, from everything
   above, one variant per role family (backend/security/trading/etc.).
8. `metadata/` — do this continuously, not at the end: every time you add
   a claim, log its source.

## Placeholder convention
Every generated file below contains inline `<!-- -->` (md) or `#` (yaml)
comments telling you exactly what to put there. Comments are safe to
delete once you've filled the field. `TODO` marks anything genuinely
required before the file is "done"; comments without `TODO` are optional
enrichment.

## What's pre-filled
A handful of `identity/` and `skills/` fields are pre-filled from what
you've already told me — check them, don't assume they're complete.
Everything else is a schema, not data.
