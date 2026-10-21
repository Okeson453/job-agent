import { CandidateProfile, Job, JobMatch, ScoreBreakdown } from '../types';

const ONSITE_TOKENS = [
  'on-site',
  'onsite',
  'on site',
  'in-office',
  'in office',
  'office-based',
  'office based',
  'must be in office',
  'required in office',
  'days in office',
  'hybrid onsite',
  'hybrid (on-site',
  'come into the office',
  'relocate to',
  'based in our office',
];

const REMOTE_TOKENS = [
  'remote',
  'work from home',
  'work-from-home',
  'wfh',
  'home-based',
  'anywhere',
  'distributed team',
  'fully remote',
  'remote-first',
  'remote first',
  '100% remote',
  'work remotely',
];

export function checkHardFilter(job: Job): string | null {
  const emp = (job.employment_type || '').toLowerCase();
  const location = (job.location || '').toLowerCase();
  const blob = `${job.title} ${job.description || ''} ${emp} ${location}`.toLowerCase();

  const isRemote = Boolean(job.remote) || REMOTE_TOKENS.some((tok) => blob.includes(tok));
  if (!isRemote) {
    return 'not_remote';
  }

  const hasOnsite = ONSITE_TOKENS.some((tok) => blob.includes(tok));
  const fullyRemotePhrase = [
    'fully remote',
    '100% remote',
    'remote only',
    'remote-only',
    'work from home',
    'work-from-home',
  ].some((tok) => blob.includes(tok));

  if (hasOnsite && !fullyRemotePhrase && !Boolean(job.remote)) {
    return 'onsite_required';
  }

  if (hasOnsite && blob.includes('hybrid') && !fullyRemotePhrase) {
    return 'onsite_required';
  }

  return null;
}

const CORE_STACK = new Set([
  'typescript',
  'javascript',
  'python',
  'postgresql',
  'postgres',
  'node.js',
  'nodejs',
  'node',
  'redis',
  'fastapi',
  'sqlalchemy',
]);

const DOMAIN_KEYWORDS = [
  'fintech',
  'trading',
  'finance',
  'backend',
  'platform',
  'infrastructure',
  'systems',
  'architecture',
];

const ROLE_KEYWORDS = [
  'backend',
  'software engineer',
  'systems engineer',
  'platform engineer',
  'trading systems',
  'full stack',
  'fullstack',
];

export function computeJobMatch(job: Job, profile: CandidateProfile): JobMatch {
  const hardReason = checkHardFilter(job);

  // 1. Remote (20 pts)
  let scoreRemote = 0;
  if (job.remote && profile.remote_ok) {
    scoreRemote = 20;
  }

  // 2. Nigeria Eligible (20 pts)
  let scoreNigeria = 0;
  if (profile.nigeria_eligible) {
    const countries = (job.countries || []).map((c) => c.toLowerCase());
    const loc = (job.location || '').toLowerCase();
    if (countries.includes('nigeria') || countries.includes('ng') || loc.includes('nigeria') || job.remote) {
      scoreNigeria = 20;
    }
  }

  // 3. Core Stack Match (20 pts)
  let scoreStack = 0;
  const strongMatches: string[] = [];
  const gaps: string[] = [];
  const jobTechs = new Set((job.technologies || []).map((t) => t.toLowerCase()));
  const blob = `${job.title} ${job.description}`.toLowerCase();
  for (const term of CORE_STACK) {
    if (blob.includes(term)) jobTechs.add(term);
  }

  const candidateTechs = new Set([
    ...profile.technologies.map((t) => t.toLowerCase()),
    ...profile.skills.map((s) => s.toLowerCase()),
  ]);

  let overlapCount = 0;
  let coreOverlapCount = 0;

  for (const tech of jobTechs) {
    if (candidateTechs.has(tech)) {
      overlapCount++;
      strongMatches.push(tech);
      if (CORE_STACK.has(tech)) {
        coreOverlapCount++;
      }
    } else {
      gaps.push(tech);
    }
  }

  if (coreOverlapCount >= 3) {
    scoreStack = 20;
  } else if (coreOverlapCount >= 1 || overlapCount >= 2) {
    scoreStack = 10;
  }

  // 4. Role Match (10 pts)
  let scoreRole = 0;
  const titleLower = job.title.toLowerCase();
  for (const kw of ROLE_KEYWORDS) {
    if (titleLower.includes(kw)) {
      scoreRole = 10;
      break;
    }
  }
  if (scoreRole === 0 && profile.preferred_roles) {
    for (const pref of profile.preferred_roles) {
      if (titleLower.includes(pref.toLowerCase())) {
        scoreRole = 10;
        break;
      }
    }
  }

  // 5. Experience Match (10 pts)
  let scoreExperience = 5;
  const seniority = (job.seniority || '').toLowerCase();
  if (['junior', 'entry', 'intern'].includes(seniority)) {
    scoreExperience = 5;
  } else if (['mid', 'middle', 'intermediate', 'senior', 'staff', 'principal'].includes(seniority)) {
    scoreExperience = 10;
  }

  // 6. Domain Match (10 pts)
  let scoreDomain = 0;
  let domainHits = 0;
  for (const kw of DOMAIN_KEYWORDS) {
    if (blob.includes(kw)) domainHits++;
  }
  if (domainHits >= 2) scoreDomain = 10;
  else if (domainHits === 1) scoreDomain = 5;

  // 7. Salary Acceptable (5 pts)
  let scoreSalary = 5;
  if (profile.min_salary != null) {
    if (job.salary_max != null && job.salary_max < profile.min_salary) {
      scoreSalary = 0;
    } else if (job.salary_min != null && job.salary_min >= profile.min_salary) {
      scoreSalary = 5;
    } else {
      scoreSalary = 2;
    }
  }

  // 8. Seniority Appropriate (5 pts)
  let scoreSeniority = 5;
  if (['intern', 'junior', 'entry'].includes(seniority)) {
    scoreSeniority = 0;
  }

  const breakdown: ScoreBreakdown = {
    remote: scoreRemote,
    nigeria: scoreNigeria,
    stack: scoreStack,
    role: scoreRole,
    experience: scoreExperience,
    domain: scoreDomain,
    salary: scoreSalary,
    seniority: scoreSeniority,
  };

  const total = Math.min(
    scoreRemote +
      scoreNigeria +
      scoreStack +
      scoreRole +
      scoreExperience +
      scoreDomain +
      scoreSalary +
      scoreSeniority,
    100
  );

  let recommendation: 'APPLY' | 'REVIEW' | 'SKIP' | 'REJECT' = 'REVIEW';
  if (hardReason) {
    recommendation = 'REJECT';
  } else if (total >= 70) {
    recommendation = 'APPLY';
  } else if (total >= 40) {
    recommendation = 'REVIEW';
  } else {
    recommendation = 'SKIP';
  }

  return {
    id: `match-${job.id}`,
    job_id: job.id,
    deterministic_score: total,
    semantic_score: total >= 60 ? Math.min(0.95, total / 100 + 0.05) : Math.max(0.2, total / 100 - 0.05),
    match_score: total,
    breakdown,
    strong_matches: strongMatches.slice(0, 6),
    gaps: gaps.slice(0, 4),
    recommendation,
    hard_filter_reason: hardReason,
  };
}
