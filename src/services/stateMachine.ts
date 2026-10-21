import { Application, ApplicationEvent, JobState } from '../types';

export const VALID_TRANSITIONS: Record<JobState, JobState[]> = {
  DISCOVERED: ['NORMALIZED', 'REJECTED_BY_FILTER', 'DUPLICATE'],
  NORMALIZED: ['ELIGIBILITY_CHECK', 'REJECTED_BY_FILTER'],
  ELIGIBILITY_CHECK: ['MATCHED', 'REJECTED_BY_FILTER'],
  MATCHED: ['QUALIFIED', 'LOW_MATCH', 'REJECTED_BY_FILTER'],
  QUALIFIED: ['APPLICATION_PREP', 'MISSING_INFORMATION'],
  APPLICATION_PREP: ['FACT_VALIDATION', 'MISSING_INFORMATION'],
  FACT_VALIDATION: ['READY', 'MANUAL_REVIEW'],
  READY: ['SUBMISSION', 'MANUAL_REVIEW'],
  SUBMISSION: ['SUBMITTED', 'SUBMISSION_FAILED', 'HUMAN_INTERVENTION_REQUIRED'],
  SUBMITTED: ['INTERVIEW', 'EMPLOYER_REJECTED', 'OFFER'],
  INTERVIEW: ['OFFER', 'EMPLOYER_REJECTED'],
  OFFER: [],
  EMPLOYER_REJECTED: [],
  REJECTED_BY_FILTER: [],
  LOW_MATCH: [],
  MISSING_INFORMATION: [],
  MANUAL_REVIEW: ['READY', 'REJECTED_BY_FILTER', 'SUBMISSION'],
  SUBMISSION_FAILED: ['SUBMISSION', 'MANUAL_REVIEW', 'HUMAN_INTERVENTION_REQUIRED'],
  HUMAN_INTERVENTION_REQUIRED: ['SUBMISSION', 'MANUAL_REVIEW', 'REJECTED_BY_FILTER'],
  DUPLICATE: [],
};

export function canTransition(current: JobState, toState: JobState): boolean {
  return VALID_TRANSITIONS[current]?.includes(toState) ?? false;
}

export function isTerminal(state: JobState): boolean {
  return (VALID_TRANSITIONS[state] || []).length === 0;
}

export function advanceApplication(
  app: Application,
  toState: JobState,
  detail?: string,
  extra?: Partial<Application>
): { updatedApp: Application; event: ApplicationEvent } {
  if (!canTransition(app.state, toState)) {
    throw new Error(`Illegal state transition: ${app.state} → ${toState} for application ${app.id}`);
  }

  const now = new Date().toISOString();
  const updatedApp: Application = {
    ...app,
    state: toState,
    updated_at: now,
    ...(extra || {}),
  };

  if (toState === 'SUBMITTED' && !updatedApp.submitted_at) {
    updatedApp.submitted_at = now;
  } else if (toState === 'INTERVIEW' && !updatedApp.interview_at) {
    updatedApp.interview_at = now;
  } else if (toState === 'OFFER' && !updatedApp.offer_at) {
    updatedApp.offer_at = now;
  } else if (toState === 'EMPLOYER_REJECTED' && !updatedApp.rejected_at) {
    updatedApp.rejected_at = now;
  }

  const event: ApplicationEvent = {
    id: `evt-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    application_id: app.id,
    event_type: 'state_transition',
    from_state: app.state,
    to_state: toState,
    detail: detail || null,
    created_at: now,
  };

  return { updatedApp, event };
}
