export type EvidenceLevel =
  | 'verified'
  | 'implemented'
  | 'partially_implemented'
  | 'designed'
  | 'research'
  | 'concept';

export interface CandidateProfile {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
  skills: string[];
  technologies: string[];
  remote_ok: boolean;
  nigeria_eligible: boolean;
  min_salary: number | null;
  currency: string;
  preferred_roles: string[];
  availability: string;
  work_authorization: string;
}

export interface CandidateFact {
  id: string;
  category: string;
  fact: string;
  value: string;
  evidence_level: EvidenceLevel;
  source_document: string;
  verified: boolean;
  metadata?: {
    project?: string;
    technologies?: string[];
    [key: string]: any;
  };
  created_at: string;
}

export interface CandidateProject {
  id: string;
  name: string;
  implementation_status: EvidenceLevel;
  architecture_status: EvidenceLevel;
  production_deployment: string;
  verified_technologies: string[];
  design_experience: string;
  description: string;
  source_document: string;
  metrics?: Record<string, string>;
}

export interface CandidateSkill {
  id: string;
  name: string;
  category: string;
  proficiency: 'expert' | 'proficient' | 'working' | 'familiar';
  evidence_level: EvidenceLevel;
  source_document: string;
}

export interface AnswerBankItem {
  id: string;
  category: string;
  question: string;
  answer: string;
}

export type JobState =
  | 'DISCOVERED'
  | 'NORMALIZED'
  | 'ELIGIBILITY_CHECK'
  | 'MATCHED'
  | 'QUALIFIED'
  | 'APPLICATION_PREP'
  | 'FACT_VALIDATION'
  | 'READY'
  | 'SUBMISSION'
  | 'SUBMITTED'
  | 'INTERVIEW'
  | 'OFFER'
  | 'EMPLOYER_REJECTED'
  | 'REJECTED_BY_FILTER'
  | 'LOW_MATCH'
  | 'MISSING_INFORMATION'
  | 'MANUAL_REVIEW'
  | 'SUBMISSION_FAILED'
  | 'DUPLICATE'
  | 'HUMAN_INTERVENTION_REQUIRED';

export interface Job {
  id: string;
  source: string;
  external_id: string;
  title: string;
  company: string;
  description: string;
  location: string;
  remote: boolean;
  countries: string[];
  employment_type: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  technologies: string[];
  seniority: string;
  application_url: string;
  state: JobState;
  discovered_at: string;
}

export interface ScoreBreakdown {
  remote: number;
  nigeria: number;
  stack: number;
  role: number;
  experience: number;
  domain: number;
  salary: number;
  seniority: number;
}

export interface JobMatch {
  id: string;
  job_id: string;
  deterministic_score: number;
  semantic_score: number | null;
  match_score: number;
  breakdown: ScoreBreakdown;
  strong_matches: string[];
  gaps: string[];
  recommendation: 'APPLY' | 'REVIEW' | 'SKIP' | 'REJECT';
  hard_filter_reason?: string | null;
}

export interface Application {
  id: string;
  job_id: string;
  state: JobState;
  cv_profile_name: string;
  cover_letter: string;
  mode: 'APPROVAL' | 'AUTONOMOUS';
  failure_reason: string | null;
  screenshot_path: string | null;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  interview_at?: string | null;
  offer_at?: string | null;
  rejected_at?: string | null;
}

export interface ApplicationEvent {
  id: string;
  application_id: string;
  event_type: string;
  from_state: JobState | null;
  to_state: JobState | null;
  detail: string | null;
  created_at: string;
}

export interface Claim {
  text: string;
  claimed_level: EvidenceLevel | null;
  project_ref: string | null;
  technologies: string[];
  keywords: string[];
}

export type ValidationOutcome = 'accepted' | 'needs_rewrite' | 'unsupported' | 'no_claims';

export interface ClaimVerdict {
  claim: Claim;
  outcome: ValidationOutcome;
  matched_fact_id?: string | null;
  actual_level?: string | null;
  rewrite_to_level?: string | null;
  reason: string;
}

export interface ValidationResult {
  verdicts: ClaimVerdict[];
  empty_claims: boolean;
  all_accepted: boolean;
  needs_manual_review: boolean;
  needs_rewrite: boolean;
}

export interface DailyStats {
  jobs_discovered: number;
  applications: number;
  submitted: number;
  failed: number;
  interviews: number;
  offers: number;
  high_match: number;
  application_rate: number;
  response_rate: number;
  interview_rate: number;
}

export interface SourceStats {
  source: string;
  count: number;
  source_conversion: number;
  interview_conversion: number;
}
