import {
  Claim,
  ClaimVerdict,
  CandidateFact,
  EvidenceLevel,
  ValidationOutcome,
  ValidationResult,
} from '../types';

export const EVIDENCE_ORDER: EvidenceLevel[] = [
  'verified',
  'implemented',
  'partially_implemented',
  'designed',
  'research',
  'concept',
];

export function getEvidenceRank(level: EvidenceLevel): number {
  const idx = EVIDENCE_ORDER.indexOf(level);
  return idx >= 0 ? idx : 999;
}

/**
 * Governing Principle (§6 / README):
 * VERIFIED → IMPLEMENTED → PARTIALLY_IMPLEMENTED → DESIGNED → RESEARCH → CONCEPT
 * can_support(claimed, actual): true only if actual is as strong or stronger than claimed.
 * E.g., DESIGNED cannot support IMPLEMENTED.
 */
export function canSupport(claimed: EvidenceLevel, actual: EvidenceLevel): boolean {
  return getEvidenceRank(actual) <= getEvidenceRank(claimed);
}

const IMPLEMENTED_REGEX = /\b(built|deployed|shipped|operated|ran in production|production system|launched|released|maintained in prod|on-call|scaled to)\b/i;
const DESIGNED_REGEX = /\b(designed|architected|specified|drafted|proposed|modelled|modeled)\b/i;
const RESEARCH_REGEX = /\b(researched|studied|investigated|explored|analysed|analyzed)\b/i;

export const KNOWN_PROJECTS = [
  'TestingEngine',
  'CrashWave',
  'OrionSentinel',
  'AegisShare',
  'AegisOS',
  'AegisTriage',
  'GhostGrid',
  'SentraAura',
  'ArbiterSigma',
  'EchoPulse',
  'KairosSovereign',
  'VoidEngine',
  'Crash',
];

const TECH_REGEX = /\b(TypeScript|JavaScript|Python|PostgreSQL|Postgres|Redis|Node\.?js|WebSockets?|FastAPI|SQLAlchemy|Playwright|AWS|Docker|Kubernetes|GraphQL|gRPC|MQL5|Tailwind)\b/gi;

export function extractClaims(text: string): Claim[] {
  if (!text || !text.trim()) return [];

  const sentences = text
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 8);

  const claims: Claim[] = [];

  for (const sentence of sentences) {
    const lower = sentence.toLowerCase();
    if (lower.startsWith('the company') || lower.startsWith('your team') || lower.startsWith('this role')) {
      continue;
    }

    let claimedLevel: EvidenceLevel | null = null;
    if (IMPLEMENTED_REGEX.test(sentence)) {
      claimedLevel = 'implemented';
    } else if (DESIGNED_REGEX.test(sentence)) {
      claimedLevel = 'designed';
    } else if (RESEARCH_REGEX.test(sentence)) {
      claimedLevel = 'research';
    }

    let projectRef: string | null = null;
    for (const proj of KNOWN_PROJECTS) {
      const pRegex = new RegExp(`\\b${proj}\\b`, 'i');
      if (pRegex.test(sentence)) {
        projectRef = proj;
        break;
      }
    }

    const techMatches = sentence.match(TECH_REGEX) || [];
    const technologies = Array.from(new Set(techMatches.map((t) => t.trim())));

    const isExperienceAssertion =
      lower.includes('i designed') ||
      lower.includes('i built') ||
      lower.includes('i implemented') ||
      lower.includes('i developed') ||
      lower.includes('i architected') ||
      lower.includes('my experience') ||
      lower.includes('experience with') ||
      lower.includes('years of experience') ||
      lower.includes('responsible for') ||
      lower.includes('led ') ||
      lower.includes('owned ') ||
      lower.includes('deployed') ||
      lower.includes('contributed') ||
      lower.includes('based in') ||
      lower.includes('work authorization');

    if (claimedLevel === null && !isExperienceAssertion && !projectRef) {
      continue;
    }

    const words = (sentence.toLowerCase().match(/[a-z]{4,}/g) || []).filter(
      (w) => !['that', 'this', 'with', 'from', 'have', 'been', 'were', 'which', 'their', 'about', 'would', 'could', 'should'].includes(w)
    );

    claims.push({
      text: sentence,
      claimed_level: claimedLevel,
      project_ref: projectRef,
      technologies,
      keywords: words.slice(0, 10),
    });
  }

  return claims;
}

function findMatchingFact(claim: Claim, facts: CandidateFact[]): CandidateFact | null {
  if (!facts.length) return null;

  if (claim.project_ref) {
    const pref = claim.project_ref.toLowerCase();
    const projectHits = facts.filter((f) => {
      const projMeta = (f.metadata?.project || '').toLowerCase();
      return (
        projMeta === pref ||
        f.fact.toLowerCase().includes(pref) ||
        f.value.toLowerCase().includes(pref) ||
        f.source_document.toLowerCase().includes(pref)
      );
    });

    if (projectHits.length > 0) {
      if (claim.technologies.length > 0) {
        const claimTechs = new Set(claim.technologies.map((t) => t.toLowerCase()));
        let best: CandidateFact | null = null;
        let maxOverlap = -1;
        for (const fact of projectHits) {
          const metaTechs = (fact.metadata?.technologies || []).map((t) => t.toLowerCase());
          const factBlob = (fact.fact + ' ' + fact.value).toLowerCase();
          let overlap = 0;
          for (const t of claimTechs) {
            if (metaTechs.includes(t) || factBlob.includes(t)) overlap++;
          }
          if (overlap > maxOverlap) {
            maxOverlap = overlap;
            best = fact;
          }
        }
        if (best && maxOverlap > 0) return best;
      }
      return projectHits[0];
    }
    return null;
  }

  if (claim.technologies.length > 0) {
    const claimTechs = new Set(claim.technologies.map((t) => t.toLowerCase()));
    let best: CandidateFact | null = null;
    let maxOverlap = 0;
    for (const fact of facts) {
      const metaTechs = (fact.metadata?.technologies || []).map((t) => t.toLowerCase());
      const factBlob = (fact.fact + ' ' + fact.value).toLowerCase();
      let overlap = 0;
      for (const t of claimTechs) {
        if (metaTechs.includes(t) || factBlob.includes(t)) overlap++;
      }
      if (overlap > maxOverlap) {
        maxOverlap = overlap;
        best = fact;
      }
    }
    if (best && maxOverlap >= 2) return best;
    if (best && maxOverlap === 1 && claim.keywords.length > 0) {
      const blob = (best.fact + ' ' + best.value).toLowerCase();
      const kwMatches = claim.keywords.filter((kw) => blob.includes(kw)).length;
      if (kwMatches >= 2) return best;
    }
  }

  if (claim.keywords.length >= 3) {
    let best: CandidateFact | null = null;
    let bestScore = 0;
    for (const fact of facts) {
      const blob = (fact.fact + ' ' + fact.value).toLowerCase();
      const score = claim.keywords.filter((kw) => blob.includes(kw)).length;
      if (score > bestScore) {
        bestScore = score;
        best = fact;
      }
    }
    if (best && bestScore >= 3) return best;
  }

  return null;
}

export function validateClaims(
  claims: Claim[],
  facts: CandidateFact[],
  requireVerified: boolean = true
): ValidationResult {
  if (!claims.length) {
    return {
      verdicts: [],
      empty_claims: true,
      all_accepted: false,
      needs_manual_review: true,
      needs_rewrite: false,
    };
  }

  const verdicts: ClaimVerdict[] = [];

  for (const claim of claims) {
    const matched = findMatchingFact(claim, facts);

    if (!matched) {
      verdicts.push({
        claim,
        outcome: 'unsupported',
        reason: 'No matching candidate fact found in verified knowledge base',
      });
      continue;
    }

    if (requireVerified && !matched.verified) {
      verdicts.push({
        claim,
        outcome: 'unsupported',
        matched_fact_id: matched.id,
        actual_level: matched.evidence_level,
        reason: `Matching fact exists but is not marked verified in evidence registry`,
      });
      continue;
    }

    const actual = matched.evidence_level;

    if (!claim.claimed_level) {
      if (actual === 'verified' || actual === 'implemented') {
        verdicts.push({
          claim,
          outcome: 'accepted',
          matched_fact_id: matched.id,
          actual_level: actual,
          reason: `Unmarked claim grounded by strong ${actual} fact`,
        });
      } else {
        verdicts.push({
          claim,
          outcome: 'needs_rewrite',
          matched_fact_id: matched.id,
          actual_level: actual,
          rewrite_to_level: actual,
          reason: `Unmarked claim matches weaker evidence level ('${actual}'). Rewrite at exact level.`,
        });
      }
      continue;
    }

    if (canSupport(claim.claimed_level, actual)) {
      verdicts.push({
        claim,
        outcome: 'accepted',
        matched_fact_id: matched.id,
        actual_level: actual,
        reason: `Actual level '${actual}' safely supports claimed '${claim.claimed_level}'`,
      });
    } else {
      verdicts.push({
        claim,
        outcome: 'needs_rewrite',
        matched_fact_id: matched.id,
        actual_level: actual,
        rewrite_to_level: actual,
        reason: `Evidence violation: Claimed '${claim.claimed_level}', but repository evidence only supports '${actual}'. Downward rewrite required.`,
      });
    }
  }

  const all_accepted = verdicts.length > 0 && verdicts.every((v) => v.outcome === 'accepted');
  const needs_manual_review =
    verdicts.length === 0 || verdicts.some((v) => v.outcome === 'unsupported' || v.outcome === 'no_claims');
  const needs_rewrite = verdicts.some((v) => v.outcome === 'needs_rewrite');

  return {
    verdicts,
    empty_claims: false,
    all_accepted,
    needs_manual_review,
    needs_rewrite,
  };
}
