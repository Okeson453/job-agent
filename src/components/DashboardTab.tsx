import React from 'react';
import {
  TrendingUp,
  CheckCircle2,
  Clock,
  Layers,
  AlertTriangle,
  Radio,
  FileText,
  Briefcase,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { Application, ApplicationEvent, DailyStats, Job, SourceStats } from '../types';

interface DashboardTabProps {
  stats: DailyStats;
  sourceStats: SourceStats[];
  events: ApplicationEvent[];
  applications: Application[];
  jobs: Job[];
  isPaused: boolean;
  onNavigateToTab: (tab: string, stateFilter?: string) => void;
  onTriggerQuickScan: () => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  stats,
  sourceStats,
  events,
  applications,
  jobs,
  isPaused,
  onNavigateToTab,
  onTriggerQuickScan,
}) => {
  // Funnel counts
  const countByState = (state: string) => applications.filter((a) => a.state === state).length;

  const funnelSteps = [
    { state: 'DISCOVERED', label: 'Discovered', count: jobs.length, color: 'text-slate-400 bg-slate-900 border-slate-700' },
    { state: 'MATCHED', label: 'Matched', count: countByState('MATCHED') + countByState('READY') + countByState('SUBMITTED') + countByState('INTERVIEW'), color: 'text-blue-400 bg-blue-950/40 border-blue-800' },
    { state: 'READY', label: 'Ready for Review', count: countByState('READY'), color: 'text-amber-400 bg-amber-950/40 border-amber-700 font-bold' },
    { state: 'SUBMITTED', label: 'Submitted', count: countByState('SUBMITTED'), color: 'text-emerald-400 bg-emerald-950/40 border-emerald-800' },
    { state: 'INTERVIEW', label: 'Interviews', count: countByState('INTERVIEW'), color: 'text-purple-400 bg-purple-950/40 border-purple-800' },
    { state: 'OFFER', label: 'Offers', count: countByState('OFFER'), color: 'text-cyan-400 bg-cyan-950/40 border-cyan-700 font-bold' },
  ];

  const workers = [
    { name: 'Discovery Worker', role: 'Greenhouse/Lever/RemoteOK Poller', interval: '30m', status: isPaused ? 'PAUSED' : 'HEALTHY' },
    { name: 'Matching Worker', role: 'Deterministic & Semantic Evaluator', interval: 'Continuous', status: isPaused ? 'PAUSED' : 'HEALTHY' },
    { name: 'LLM Worker', role: 'Cover Letters & Question Answerer', interval: 'Event-driven', status: isPaused ? 'PAUSED' : 'HEALTHY' },
    { name: 'Application Worker', role: 'State Machine Decision Engine', interval: 'Event-driven', status: isPaused ? 'PAUSED' : 'HEALTHY' },
    { name: 'Browser Worker', role: 'Playwright Automated Form Submitter', interval: 'Rate-limited', status: isPaused ? 'PAUSED' : 'HEALTHY' },
    { name: 'Notification Worker', role: 'Telegram Bot Dispatcher', interval: 'Async Outbox', status: isPaused ? 'PAUSED' : 'HEALTHY' },
  ];

  return (
    <div className="space-y-6">
      {/* Banner / Overview Header */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2.5 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Continuous Autonomous Pipeline
              </span>
              <span className="text-xs text-slate-400 font-mono">Heartbeat: Active (0 lag)</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Autonomous Job Application Control Center
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Supervising multi-source job discovery, 8-criteria deterministic matching, truth-verified claim generation, and state machine automation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onTriggerQuickScan}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-600/30 transition-all cursor-pointer"
            >
              <Zap className="w-4 h-4 fill-current" />
              <span>Poll Greenhouse Boards</span>
            </button>
            <button
              onClick={() => onNavigateToTab('truth')}
              className="flex items-center space-x-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition-all cursor-pointer"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Truth Engine</span>
            </button>
          </div>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Jobs Discovered</span>
            <Briefcase className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-white tracking-tight">{stats.jobs_discovered}</div>
          <div className="mt-1 text-[11px] text-emerald-400 font-medium flex items-center gap-1">
            <span>{stats.high_match} high match (score ≥ 70)</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Applications Created</span>
            <FileText className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-white tracking-tight">{stats.applications}</div>
          <div className="mt-1 text-[11px] text-slate-400 font-mono">
            {stats.application_rate * 100}% conversion
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Submitted via ATS</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-white tracking-tight">{stats.submitted}</div>
          <div className="mt-1 text-[11px] text-slate-400 font-mono">
            {stats.failed} failed / retry
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Interviews & Offers</span>
            <TrendingUp className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-white tracking-tight">
            {stats.interviews} <span className="text-sm font-normal text-slate-400">/ {stats.offers} offers</span>
          </div>
          <div className="mt-1 text-[11px] text-purple-400 font-medium">
            {stats.interview_rate * 100}% interview rate
          </div>
        </div>
      </div>

      {/* State Machine Pipeline Funnel */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-400" />
              <span>State Machine Lifecycle Funnel</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Strict deterministic progression: DISCOVERED → MATCHED → READY → SUBMISSION → SUBMITTED → INTERVIEW
            </p>
          </div>
          <button
            onClick={() => onNavigateToTab('applications')}
            className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
          >
            <span>View All</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {funnelSteps.map((step, idx) => (
            <div
              key={step.state}
              onClick={() => onNavigateToTab('applications', step.state)}
              className={`p-3.5 rounded-xl border transition-all cursor-pointer hover:border-blue-500/60 hover:scale-[1.02] ${step.color}`}
            >
              <div className="text-[11px] uppercase tracking-wider font-semibold opacity-80">{step.label}</div>
              <div className="text-2xl font-extrabold mt-1">{step.count}</div>
              <div className="mt-1 text-[10px] opacity-70">Step {idx + 1}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Two Column Layout: Worker Supervisor + Source Statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Worker Process Supervisor */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3.5">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400" />
                <span>Asyncio Supervision Loops (§4)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Resilient bounded-backoff task supervisors running continuously
              </p>
            </div>
            <span
              className={`px-2 py-0.5 text-[10px] font-mono rounded font-bold ${
                isPaused
                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                  : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
              }`}
            >
              {isPaused ? 'SYSTEM PAUSED' : 'ALL 6 LOOPS HEALTHY'}
            </span>
          </div>

          <div className="divide-y divide-slate-800/80">
            {workers.map((w) => (
              <div key={w.name} className="py-2.5 flex items-center justify-between text-xs">
                <div>
                  <div className="font-semibold text-slate-200">{w.name}</div>
                  <div className="text-[11px] text-slate-400">{w.role}</div>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono ${
                      w.status === 'HEALTHY'
                        ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                        : 'bg-amber-950/60 text-amber-400 border border-amber-800/60'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        w.status === 'HEALTHY' ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'
                      }`}
                    ></span>
                    {w.status}
                  </span>
                  <div className="text-[10px] text-slate-500 mt-0.5 font-mono">{w.interval}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Source Breakdown & Conversion */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3.5">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <span>Source Conversion Analytics (§21)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">30-day window per discovery adapter</p>
            </div>
            <button
              onClick={() => onNavigateToTab('jobs')}
              className="text-xs text-blue-400 hover:text-blue-300 font-semibold"
            >
              Explore Jobs
            </button>
          </div>

          <div className="space-y-3">
            {sourceStats.map((s) => (
              <div key={s.source} className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-semibold capitalize text-slate-200">{s.source}</span>
                  <span className="text-slate-400 font-mono">{s.count} postings</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                  <div className="bg-slate-900/80 px-2 py-1 rounded">
                    Submit Conv:{' '}
                    <span className="text-blue-400 font-bold font-mono">
                      {(s.source_conversion * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="bg-slate-900/80 px-2 py-1 rounded">
                    Interview Conv:{' '}
                    <span className="text-purple-400 font-bold font-mono">
                      {(s.interview_conversion * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Application Audit Trail */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <span>Real-Time Audit Trail (`application_events`)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Immutable ledger of state transitions and truth engine decisions
            </p>
          </div>
        </div>

        <div className="divide-y divide-slate-800">
          {events.slice(0, 5).map((evt) => (
            <div key={evt.id} className="py-2.5 flex items-start justify-between text-xs">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-slate-500 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                    {evt.application_id}
                  </span>
                  <span className="font-semibold text-slate-300">
                    {evt.from_state ? `${evt.from_state} → ${evt.to_state}` : `Created as ${evt.to_state}`}
                  </span>
                </div>
                {evt.detail && <p className="text-slate-400 text-[11px]">{evt.detail}</p>}
              </div>
              <span className="text-[10px] font-mono text-slate-500 whitespace-nowrap ml-4">
                {new Date(evt.created_at).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
