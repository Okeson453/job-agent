import React, { useState } from 'react';
import {
  FileCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Send,
  Eye,
  FileText,
  Clock,
  Briefcase,
  ChevronRight,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  X,
  ExternalLink,
} from 'lucide-react';
import { Application, ApplicationEvent, CandidateFact, Job, JobState } from '../types';
import { extractClaims, validateClaims } from '../services/evidenceEngine';

interface ApplicationsTabProps {
  applications: Application[];
  jobs: Job[];
  facts: CandidateFact[];
  events: ApplicationEvent[];
  selectedAppId: string | null;
  onSelectApp: (id: string | null) => void;
  onTransition: (appId: string, toState: JobState, detail?: string, extra?: Partial<Application>) => void;
  initialFilterState?: string | null;
}

export const ApplicationsTab: React.FC<ApplicationsTabProps> = ({
  applications,
  jobs,
  facts,
  events,
  selectedAppId,
  onSelectApp,
  onTransition,
  initialFilterState,
}) => {
  const [filterTab, setFilterTab] = useState<string>(initialFilterState || 'ALL');
  const [reviewModalApp, setReviewModalApp] = useState<Application | null>(null);

  const jobMap = new Map(jobs.map((j) => [j.id, j]));

  // Auto-open if selectedAppId was passed
  React.useEffect(() => {
    if (selectedAppId) {
      const target = applications.find((a) => a.id === selectedAppId || a.job_id === selectedAppId);
      if (target) {
        setReviewModalApp(target);
      }
    }
  }, [selectedAppId, applications]);

  const filteredApps = applications.filter((app) => {
    if (filterTab === 'ALL') return true;
    if (filterTab === 'READY') return app.state === 'READY';
    if (filterTab === 'SUBMITTED') return app.state === 'SUBMITTED';
    if (filterTab === 'OUTCOMES') return app.state === 'INTERVIEW' || app.state === 'OFFER';
    if (filterTab === 'MANUAL_REVIEW')
      return app.state === 'MANUAL_REVIEW' || app.state === 'HUMAN_INTERVENTION_REQUIRED';
    if (filterTab === 'REJECTED')
      return (
        app.state === 'REJECTED_BY_FILTER' ||
        app.state === 'LOW_MATCH' ||
        app.state === 'SUBMISSION_FAILED' ||
        app.state === 'EMPLOYER_REJECTED'
      );
    return app.state === filterTab;
  });

  const getStatusBadge = (state: JobState) => {
    switch (state) {
      case 'READY':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-950/80 text-amber-300 border border-amber-700/80">READY FOR APPROVAL</span>;
      case 'SUBMITTED':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-700/80">SUBMITTED</span>;
      case 'INTERVIEW':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-950/80 text-purple-300 border border-purple-700/80">INTERVIEW SCHEDULED</span>;
      case 'OFFER':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-700/80">OFFER RECEIVED</span>;
      case 'MANUAL_REVIEW':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-950/80 text-rose-300 border border-rose-800/80">MANUAL REVIEW REQUIRED</span>;
      case 'REJECTED_BY_FILTER':
      case 'LOW_MATCH':
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-900 text-slate-400 border border-slate-800">FILTERED OUT</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-950 text-blue-300 border border-blue-800">{state}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Filter Tabs */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-blue-400" />
              <span>Application Pipeline & State Transitions</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Review generated cover letters, validated answers, CV selections, and submit or advance outcomes.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 bg-slate-950 p-1.5 rounded-xl border border-slate-800 text-xs">
            {[
              { id: 'ALL', label: 'All' },
              { id: 'READY', label: 'Ready (Approval)' },
              { id: 'SUBMITTED', label: 'Submitted' },
              { id: 'OUTCOMES', label: 'Interviews & Offers' },
              { id: 'MANUAL_REVIEW', label: 'Manual Review' },
              { id: 'REJECTED', label: 'Filtered / Terminated' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterTab(tab.id)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all cursor-pointer ${
                  filterTab === tab.id
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Applications List */}
      <div className="space-y-3">
        {filteredApps.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/40 border border-slate-800 rounded-2xl">
            <FileText className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-300">No applications in this view</h3>
            <p className="text-xs text-slate-500 mt-1">Switch tabs or discover new jobs to populate this queue.</p>
          </div>
        ) : (
          filteredApps.map((app) => {
            const job = jobMap.get(app.job_id);
            const appEvents = events.filter((e) => e.application_id === app.id);

            return (
              <div
                key={app.id}
                className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 transition-all shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-blue-400 font-semibold bg-blue-950/60 px-2 py-0.5 rounded border border-blue-800/60">
                      {app.id}
                    </span>
                    {getStatusBadge(app.state)}
                    <span className="text-xs text-slate-400 font-mono">
                      CV: <strong className="text-slate-200">{app.cv_profile_name}.pdf</strong>
                    </span>
                  </div>

                  <div className="text-sm font-bold text-white">
                    {job?.title || 'Job Listing'} — <span className="text-slate-300 font-medium">{job?.company || 'Company'}</span>
                  </div>

                  <div className="text-xs text-slate-400 flex flex-wrap items-center gap-3">
                    <span>{job?.location}</span>
                    <span>•</span>
                    <span className="font-mono">Created {new Date(app.created_at).toLocaleDateString()}</span>
                    {app.submitted_at && (
                      <>
                        <span>•</span>
                        <span className="text-emerald-400 font-mono">
                          Submitted {new Date(app.submitted_at).toLocaleDateString()}
                        </span>
                      </>
                    )}
                  </div>

                  {app.failure_reason && (
                    <div className="text-xs text-rose-400 bg-rose-950/30 border border-rose-900/40 px-3 py-1.5 rounded-lg flex items-center gap-2">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>{app.failure_reason}</span>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  {app.state === 'READY' && (
                    <>
                      <button
                        onClick={() => {
                          onTransition(
                            app.id,
                            'SUBMITTED',
                            'Approved by operator via UI; submission confirmed'
                          );
                        }}
                        className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Approve & Submit</span>
                      </button>
                      <button
                        onClick={() => {
                          onTransition(app.id, 'REJECTED_BY_FILTER', 'Skipped by operator in review queue');
                        }}
                        className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition-all cursor-pointer"
                      >
                        Skip
                      </button>
                    </>
                  )}

                  {app.state === 'SUBMITTED' && (
                    <button
                      onClick={() => {
                        onTransition(app.id, 'INTERVIEW', 'Interview invite received from recruiter');
                      }}
                      className="px-3.5 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                    >
                      <span>+ Interview</span>
                    </button>
                  )}

                  {app.state === 'INTERVIEW' && (
                    <button
                      onClick={() => {
                        onTransition(app.id, 'OFFER', 'Formal job offer extended to candidate');
                      }}
                      className="px-3.5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                    >
                      <span>+ Record Offer</span>
                    </button>
                  )}

                  <button
                    onClick={() => setReviewModalApp(app)}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 flex items-center gap-1 transition-all cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>Review Application</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Review & State Inspector Modal */}
      {reviewModalApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-6">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs text-blue-400 font-bold bg-blue-950 px-2 py-0.5 rounded border border-blue-800">
                    {reviewModalApp.id}
                  </span>
                  {getStatusBadge(reviewModalApp.state)}
                </div>
                <h3 className="text-lg font-bold text-white">
                  {jobMap.get(reviewModalApp.job_id)?.title}
                </h3>
                <p className="text-xs text-slate-400">
                  {jobMap.get(reviewModalApp.job_id)?.company} • {jobMap.get(reviewModalApp.job_id)?.location}
                </p>
              </div>
              <button
                onClick={() => setReviewModalApp(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Generated Cover Letter with Truth Engine Check */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-bold text-slate-300 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-400" />
                  <span>Generated Cover Letter</span>
                </label>
                <span className="text-[11px] text-slate-400 font-mono">
                  Target CV: <span className="text-blue-400 font-bold">{reviewModalApp.cv_profile_name}.pdf</span>
                </span>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                {reviewModalApp.cover_letter || 'No cover letter generated yet.'}
              </div>

              {/* Inline Truth Validation Summary */}
              {(() => {
                const claims = extractClaims(reviewModalApp.cover_letter || '');
                const validation = validateClaims(claims, facts);

                return (
                  <div className="mt-3 p-3 rounded-xl border bg-slate-950/60 border-slate-800 text-xs space-y-2">
                    <div className="flex items-center justify-between font-bold">
                      <span className="flex items-center gap-1.5 text-slate-200">
                        {validation.all_accepted ? (
                          <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <ShieldAlert className="w-4 h-4 text-rose-400" />
                        )}
                        <span>Truth Engine Validation Verdict</span>
                      </span>
                      <span
                        className={`font-mono text-[11px] px-2 py-0.5 rounded ${
                          validation.all_accepted
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-rose-950 text-rose-400 border border-rose-800'
                        }`}
                      >
                        {validation.all_accepted ? 'ALL CLAIMS VERIFIED' : 'EVIDENCE VIOLATION DETECTED'}
                      </span>
                    </div>

                    <div className="space-y-1 text-[11px]">
                      {validation.verdicts.map((v, i) => (
                        <div
                          key={i}
                          className={`p-2 rounded border ${
                            v.outcome === 'accepted'
                              ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-300'
                              : 'bg-rose-950/30 border-rose-900/50 text-rose-300'
                          }`}
                        >
                          <div className="font-semibold">"{v.claim.text}"</div>
                          <div className="text-[10px] opacity-80 mt-0.5">{v.reason}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Application Questions / Answers if any */}
            {reviewModalApp.metadata?.generated_answers && (
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-2">
                  Form Question Answers (Answer Bank Seeded)
                </label>
                <div className="space-y-2">
                  {reviewModalApp.metadata.generated_answers.map((qa: any, idx: number) => (
                    <div key={idx} className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs space-y-1">
                      <div className="font-semibold text-slate-200">Q: {qa.question}</div>
                      <div className="text-slate-400">A: {qa.answer}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Audit Trail for this Application */}
            <div>
              <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5 mb-2">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>Audit Trail (Application Events)</span>
              </label>
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs space-y-2 max-h-36 overflow-y-auto">
                {events
                  .filter((e) => e.application_id === reviewModalApp.id)
                  .map((e) => (
                    <div key={e.id} className="flex items-start justify-between text-[11px] pb-1 border-b border-slate-900 last:border-0">
                      <div>
                        <span className="font-mono text-blue-400 font-bold">{e.event_type}</span>:{' '}
                        <span className="text-slate-300">{e.from_state ? `${e.from_state} → ${e.to_state}` : e.to_state}</span>
                        {e.detail && <p className="text-slate-500 text-[10px] mt-0.5">{e.detail}</p>}
                      </div>
                      <span className="text-slate-500 font-mono text-[10px]">
                        {new Date(e.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-800">
              <div className="flex items-center gap-2">
                {reviewModalApp.state === 'READY' && (
                  <button
                    onClick={() => {
                      onTransition(reviewModalApp.id, 'SUBMITTED', 'Approved and submitted via review drawer');
                      setReviewModalApp(null);
                    }}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Approve & Submit</span>
                  </button>
                )}

                {reviewModalApp.state === 'MANUAL_REVIEW' && (
                  <button
                    onClick={() => {
                      onTransition(reviewModalApp.id, 'READY', 'Manual review resolved by operator');
                      setReviewModalApp(null);
                    }}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold cursor-pointer"
                  >
                    Resolve & Move to Ready
                  </button>
                )}

                {reviewModalApp.state === 'SUBMITTED' && (
                  <button
                    onClick={() => {
                      onTransition(reviewModalApp.id, 'INTERVIEW', 'Interview scheduled with candidate');
                      setReviewModalApp(null);
                    }}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold cursor-pointer"
                  >
                    Move to Interview
                  </button>
                )}

                <button
                  onClick={() => {
                    onTransition(reviewModalApp.id, 'REJECTED_BY_FILTER', 'Skipped by operator');
                    setReviewModalApp(null);
                  }}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold cursor-pointer"
                >
                  Skip
                </button>
              </div>

              <button
                onClick={() => setReviewModalApp(null)}
                className="px-4 py-2 bg-slate-800 text-slate-400 hover:text-white rounded-xl text-xs font-semibold cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
