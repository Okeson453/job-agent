# Knowledge base gaps

Everything the CV and email generator reads comes from `candidate/`. Empty or
`TODO` fields are omitted from generated documents — nothing is invented. Fix
these in priority order; each item says where it goes and what shape it takes.

## P1 — affects every generated CV

- [ ] **Employment dates** — `candidate/experience/employment.yaml`
      `start_date: {value: "2021-03", precision: "month"}`, plus `end_date` and
      any earlier employers as their own entries. Dates are what most ATS parsers
      key on; without them the current role reads as undated.
- [ ] **Years of experience + career level** — `candidate/profile/candidate_overview.yaml`
      and `career_level.yaml`: `years_experience: 5`, `career_level: "mid"`,
      `current_title`, `primary_domain`, `open_to`. One-line `justification`
      (scope, not tenure).
- [ ] **Professional summary** — `candidate/profile/professional_summary.md`
      2–3 sentences, first person, no claims not already in the KB.
- [ ] **Measurable results** — `candidate/achievements/measurable_results.yaml`
      3–5 entries:
      ```yaml
      - result: "Reduced prediction pipeline latency"
        metric: "p95 420ms → 90ms"
        context: "TestingEngine"
        source: "commit 092f66ce"
      ```
      Numbers are the single biggest CV quality lever, and the grounding check
      rejects any number that isn't here.

## P2 — sections that are currently dropped

- [ ] **Certifications** — `candidate/certifications/certifications.yaml`.
      `name`, `issuer`, `date_earned`, `credential_id`, `credential_url`.
      If you have none, say so and I'll mark the section intentionally empty.
- [ ] **Employment responsibilities** — `candidate/experience/responsibilities/README.md`
      is a placeholder. Bullets live inline in `employment.yaml` today; move or
      add 3–6 outcome-shaped bullets per role if there are older roles.
- [ ] **Project responsibilities** — files still `TODO` for: Crash, GhostGrid,
      OrionSentinel, SentraAura, TestingEngine, AegisShare, AegisTriage,
      EchoPulse, KairosSovereign, PhantomStrike. Two or three bullets each on what
      *you* built.
- [ ] **Project dates and links** — `start` is `null` in every `project.yaml`;
      `repo_url` is empty for most. Add `start: "2025-06"` where accurate.

## P3 — targeting and eligibility

- [ ] **Role targets** — `candidate/profile/role_targets.yaml`
      `primary_targets`, `secondary_targets`, `excluded_titles`.
- [ ] **Work authorization** — `candidate/work_authorization/*.yaml`
      `authorized_countries: ["Nigeria"]` plus any others. Keep the standard
      answer text as is unless you want different wording.
- [ ] **Compensation floor** — `candidate/compensation/*.yaml` already has
      hourly/day rates. Confirm a minimum annual figure if you want salary
      filtering to bite, then set `MIN_SALARY` or the profile's `min_salary`.

## P4 — education detail

- [ ] **Degree dates** — `candidate/education/degrees.yaml` `start_year`,
      `end_year`, and whether "in-progress" is still correct.
- [ ] **Academic honors** — `candidate/education/achievements.yaml` if any.

## Not needed

- Portfolio and architecture notes are already populated.
- `cv/*.pdf` stubs are ignored; CVs are generated from the KB.

## Fastest path

Reply with the P1 items as free text (dates, years, level, three achievements
with numbers) and I'll write them into the YAML, then regenerate a sample CV so
you can see the difference.
