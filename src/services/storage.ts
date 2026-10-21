import {
  AnswerBankItem,
  Application,
  ApplicationEvent,
  CandidateFact,
  CandidateProfile,
  CandidateProject,
  CandidateSkill,
  DailyStats,
  Job,
  JobMatch,
  JobState,
  SourceStats,
} from '../types';
import { SEED_ANSWERS, SEED_FACTS, SEED_PROFILE, SEED_PROJECTS, SEED_SKILLS } from '../data/seedCandidate';
import { INITIAL_APPLICATIONS, INITIAL_JOBS } from '../data/initialJobs';
import { computeJobMatch } from './matcherEngine';
import { advanceApplication } from './stateMachine';

const STORAGE_KEYS = {
  PROFILE: 'jobagent_profile',
  FACTS: 'jobagent_facts',
  PROJECTS: 'jobagent_projects',
  SKILLS: 'jobagent_skills',
  ANSWERS: 'jobagent_answers',
  JOBS: 'jobagent_jobs',
  APPLICATIONS: 'jobagent_applications',
  EVENTS: 'jobagent_events',
  SYSTEM_PAUSED: 'jobagent_system_paused',
  APP_MODE: 'jobagent_app_mode',
};

class StorageService {
  private get<T>(key: string, defaultValue: T): T {
    try {
      const stored = localStorage.getItem(key);
      if (!stored) return defaultValue;
      return JSON.parse(stored) as T;
    } catch {
      return defaultValue;
    }
  }

  private set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.warn('Failed to save to localStorage:', e);
    }
  }

  // --- System State ---
  isSystemPaused(): boolean {
    return this.get<boolean>(STORAGE_KEYS.SYSTEM_PAUSED, false);
  }

  setSystemPaused(paused: boolean): boolean {
    this.set(STORAGE_KEYS.SYSTEM_PAUSED, paused);
    return paused;
  }

  getAppMode(): 'APPROVAL' | 'AUTONOMOUS' {
    return this.get<'APPROVAL' | 'AUTONOMOUS'>(STORAGE_KEYS.APP_MODE, 'APPROVAL');
  }

  setAppMode(mode: 'APPROVAL' | 'AUTONOMOUS'): void {
    this.set(STORAGE_KEYS.APP_MODE, mode);
  }

  // --- Profile ---
  getProfile(): CandidateProfile {
    return this.get<CandidateProfile>(STORAGE_KEYS.PROFILE, SEED_PROFILE);
  }

  updateProfile(updates: Partial<CandidateProfile>): CandidateProfile {
    const current = this.getProfile();
    const updated = { ...current, ...updates };
    this.set(STORAGE_KEYS.PROFILE, updated);
    return updated;
  }

  // --- Facts & Evidence ---
  getFacts(): CandidateFact[] {
    return this.get<CandidateFact[]>(STORAGE_KEYS.FACTS, SEED_FACTS);
  }

  addFact(fact: Omit<CandidateFact, 'id' | 'created_at'>): CandidateFact {
    const facts = this.getFacts();
    const newFact: CandidateFact = {
      ...fact,
      id: `fact-${Date.now()}`,
      created_at: new Date().toISOString(),
    };
    facts.unshift(newFact);
    this.set(STORAGE_KEYS.FACTS, facts);
    return newFact;
  }

  updateFact(id: string, updates: Partial<CandidateFact>): CandidateFact | null {
    const facts = this.getFacts();
    const idx = facts.findIndex((f) => f.id === id);
    if (idx === -1) return null;
    facts[idx] = { ...facts[idx], ...updates };
    this.set(STORAGE_KEYS.FACTS, facts);
    return facts[idx];
  }

  // --- Projects & Skills ---
  getProjects(): CandidateProject[] {
    return this.get<CandidateProject[]>(STORAGE_KEYS.PROJECTS, SEED_PROJECTS);
  }

  getSkills(): CandidateSkill[] {
    return this.get<CandidateSkill[]>(STORAGE_KEYS.SKILLS, SEED_SKILLS);
  }

  getAnswers(): AnswerBankItem[] {
    return this.get<AnswerBankItem[]>(STORAGE_KEYS.ANSWERS, SEED_ANSWERS);
  }

  addAnswer(category: string, question: string, answer: string): AnswerBankItem {
    const answers = this.getAnswers();
    const newItem: AnswerBankItem = {
      id: `ans-${Date.now()}`,
      category,
      question,
      answer,
    };
    answers.unshift(newItem);
    this.set(STORAGE_KEYS.ANSWERS, answers);
    return newItem;
  }

  // --- Jobs ---
  getJobs(): Job[] {
    return this.get<Job[]>(STORAGE_KEYS.JOBS, INITIAL_JOBS);
  }

  getJob(id: string): Job | undefined {
    return this.getJobs().find((j) => j.id === id);
  }

  addJobs(newJobs: Job[]): number {
    const existing = this.getJobs();
    const existingIds = new Set(existing.map((j) => `${j.source}:${j.external_id}`));
    const added: Job[] = [];

    for (const job of newJobs) {
      const key = `${job.source}:${job.external_id}`;
      if (!existingIds.has(key)) {
        existingIds.add(key);
        added.push(job);
      }
    }

    if (added.length > 0) {
      const combined = [...added, ...existing];
      this.set(STORAGE_KEYS.JOBS, combined);

      // Auto create application record in DISCOVERED/NORMALIZED state
      const profile = this.getProfile();
      for (const job of added) {
        this.createApplicationForJob(job, profile);
      }
    }
    return added.length;
  }

  // --- Matches ---
  getJobMatch(jobId: string): JobMatch | null {
    const job = this.getJob(jobId);
    if (!job) return null;
    const profile = this.getProfile();
    return computeJobMatch(job, profile);
  }

  // --- Applications ---
  getApplications(): Application[] {
    return this.get<Application[]>(STORAGE_KEYS.APPLICATIONS, INITIAL_APPLICATIONS);
  }

  getApplication(id: string): Application | undefined {
    return this.getApplications().find((a) => a.id === id);
  }

  getApplicationForJob(jobId: string): Application | undefined {
    return this.getApplications().find((a) => a.job_id === jobId);
  }

  createApplicationForJob(job: Job, profile: CandidateProfile): Application {
    const apps = this.getApplications();
    const existing = apps.find((a) => a.job_id === job.id);
    if (existing) return existing;

    const match = computeJobMatch(job, profile);
    let initialState: JobState = 'DISCOVERED';
    let failureReason: string | null = null;

    if (match.hard_filter_reason) {
      initialState = 'REJECTED_BY_FILTER';
      failureReason = `Hard filter: ${match.hard_filter_reason}`;
    } else if (match.match_score >= 70) {
      initialState = 'READY';
    } else if (match.match_score < 40) {
      initialState = 'LOW_MATCH';
      failureReason = `Match score ${match.match_score} below minimum threshold`;
    } else {
      initialState = 'MATCHED';
    }

    const newApp: Application = {
      id: `app-${job.id.replace('job-', '')}`,
      job_id: job.id,
      state: initialState,
      cv_profile_name: 'backend',
      cover_letter: `Dear ${job.company} Team,\n\nI am applying for the ${job.title} role. My background in distributed systems, TypeScript, and high-reliability backend engineering directly aligns with this position.`,
      mode: this.getAppMode(),
      failure_reason: failureReason,
      screenshot_path: null,
      metadata: { score: match.match_score },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    apps.unshift(newApp);
    this.set(STORAGE_KEYS.APPLICATIONS, apps);

    this.recordEvent({
      id: `evt-${Date.now()}`,
      application_id: newApp.id,
      event_type: 'created',
      from_state: null,
      to_state: initialState,
      detail: failureReason || `Discovered with match score ${match.match_score}`,
      created_at: new Date().toISOString(),
    });

    return newApp;
  }

  transitionApplication(
    appId: string,
    toState: JobState,
    detail?: string,
    extra?: Partial<Application>
  ): Application {
    const apps = this.getApplications();
    const idx = apps.findIndex((a) => a.id === appId);
    if (idx === -1) throw new Error(`Application ${appId} not found`);

    const current = apps[idx];
    const { updatedApp, event } = advanceApplication(current, toState, detail, extra);

    apps[idx] = updatedApp;
    this.set(STORAGE_KEYS.APPLICATIONS, apps);
    this.recordEvent(event);

    return updatedApp;
  }

  // --- Events ---
  getEvents(applicationId?: string): ApplicationEvent[] {
    const events = this.get<ApplicationEvent[]>(STORAGE_KEYS.EVENTS, [
      {
        id: 'evt-init-1',
        application_id: 'app-stripe-001',
        event_type: 'state_transition',
        from_state: 'FACT_VALIDATION',
        to_state: 'READY',
        detail: 'Evidence validation passed (all claims verified against candidate KB)',
        created_at: '2026-10-21T07:00:00Z',
      },
      {
        id: 'evt-init-2',
        application_id: 'app-remoteok-002',
        event_type: 'state_transition',
        from_state: 'SUBMISSION',
        to_state: 'SUBMITTED',
        detail: 'Form successfully submitted via browser automation',
        created_at: '2026-10-20T16:20:00Z',
      },
    ]);
    if (applicationId) {
      return events.filter((e) => e.application_id === applicationId);
    }
    return events;
  }

  recordEvent(event: ApplicationEvent): void {
    const events = this.getEvents();
    events.unshift(event);
    this.set(STORAGE_KEYS.EVENTS, events.slice(0, 200));
  }

  // --- Stats Calculations (§21) ---
  getDailyStats(): DailyStats {
    const jobs = this.getJobs();
    const apps = this.getApplications();

    const jobsDiscovered = jobs.length;
    const totalApps = apps.length;
    const submitted = apps.filter((a) => a.state === 'SUBMITTED').length;
    const failed = apps.filter((a) => a.state === 'SUBMISSION_FAILED').length;
    const interviews = apps.filter((a) => a.state === 'INTERVIEW').length;
    const offers = apps.filter((a) => a.state === 'OFFER').length;
    const responded = apps.filter((a) => ['INTERVIEW', 'OFFER', 'EMPLOYER_REJECTED'].includes(a.state)).length;

    const highMatch = jobs.filter((j) => {
      const match = this.getJobMatch(j.id);
      return match && match.match_score >= 70;
    }).length;

    const applicationRate = jobsDiscovered > 0 ? Number((totalApps / jobsDiscovered).toFixed(3)) : 0;
    const responseRate = submitted > 0 ? Number((responded / submitted).toFixed(3)) : 0;
    const interviewRate = submitted > 0 ? Number((interviews / submitted).toFixed(3)) : 0;

    return {
      jobs_discovered: jobsDiscovered,
      applications: totalApps,
      submitted,
      failed,
      interviews,
      offers,
      high_match: highMatch,
      application_rate: applicationRate,
      response_rate: responseRate,
      interview_rate: interviewRate,
    };
  }

  getSourceStats(): SourceStats[] {
    const jobs = this.getJobs();
    const apps = this.getApplications();

    const sourceCounts: Record<string, number> = {};
    for (const j of jobs) {
      sourceCounts[j.source] = (sourceCounts[j.source] || 0) + 1;
    }

    const result: SourceStats[] = [];
    for (const [source, count] of Object.entries(sourceCounts)) {
      const sourceJobs = new Set(jobs.filter((j) => j.source === source).map((j) => j.id));
      const sourceApps = apps.filter((a) => sourceJobs.has(a.job_id));
      const submitted = sourceApps.filter((a) => a.state === 'SUBMITTED').length;
      const interviews = sourceApps.filter((a) => a.state === 'INTERVIEW').length;

      result.push({
        source,
        count,
        source_conversion: count > 0 ? Number((submitted / count).toFixed(3)) : 0,
        interview_conversion: submitted > 0 ? Number((interviews / submitted).toFixed(3)) : 0,
      });
    }

    return result.sort((a, b) => b.count - a.count);
  }

  resetToDefaults(): void {
    Object.values(STORAGE_KEYS).forEach((k) => localStorage.removeItem(k));
  }
}

export const storage = new StorageService();
