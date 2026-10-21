import React, { useState } from 'react';
import {
  Search,
  Filter,
  CheckCircle,
  XCircle,
  AlertCircle,
  ExternalLink,
  Zap,
  Globe,
  Loader2,
  ChevronDown,
  ChevronUp,
  FileText,
  SlidersHorizontal,
} from 'lucide-react';
import { CandidateProfile, Job, JobMatch } from '../types';
import { computeJobMatch } from '../services/matcherEngine';
import { fetchGreenhouseBoard, generateSimulatedJobs } from '../services/discoveryService';

interface JobsTabProps {
  jobs: Job[];
  profile: CandidateProfile;
  onAddJobs: (newJobs: Job[]) => void;
  onSelectJobForApplication: (jobId: string) => void;
}

export const JobsTab: React.FC<JobsTabProps> = ({
  jobs,
  profile,
  onAddJobs,
  onSelectJobForApplication,
}) => {
  const [search, setSearch] = useState('');
  const [filterRec, setFilterRec] = useState<string>('ALL');
  const [filterSource, setFilterSource] = useState<string>('ALL');
  const [boardToken, setBoardToken] = useState('stripe');
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [expandedMatchId, setExpandedMatchId] = useState<string | null>(null);

  // Compute matches for all jobs
  const jobMatches: Record<string, JobMatch> = {};
  for (const j of jobs) {
    jobMatches[j.id] = computeJobMatch(j, profile);
  }

  // Filter jobs
  const filteredJobs = jobs.filter((job) => {
    const match = jobMatches[job.id];
    const matchQuery =
      job.title.toLowerCase().includes(search.toLowerCase()) ||
      job.company.toLowerCase().includes(search.toLowerCase()) ||
      (job.technologies || []).some((t) => t.toLowerCase().includes(search.toLowerCase()));

    if (!matchQuery) return false;

    if (filterSource !== 'ALL' && job.source !== filterSource) return false;

    if (filterRec === 'HIGH' && (match?.match_score || 0) < 70) return false;
    if (filterRec === 'REVIEW' && ((match?.match_score || 0) < 40 || (match?.match_score || 0) >= 70))
      return false;
    if (filterRec === 'REJECT' && !match?.hard_filter_reason) return false;

    return true;
  });

  const handleLiveGreenhouseScan = async (token: string) => {
    setIsScanning(true);
    setScanMessage(null);
    try {
      const fetched = await fetchGreenhouseBoard(token);
      if (fetched.length === 0) {
        setScanMessage(`Board '${token}' returned 0 active positions.`);
      } else {
        onAddJobs(fetched);
        setScanMessage(`Discovered ${fetched.length} positions from Greenhouse: ${token.toUpperCase()}`);
      }
    } catch (err: any) {
      setScanMessage(`Failed to reach board '${token}': ${err.message || 'Network error'}`);
    } finally {
      setIsScanning(false);
    }
  };

  const handleSimulateSource = (source: string) => {
    const simJobs = generateSimulatedJobs(source, 3);
    onAddJobs(simJobs);
    setScanMessage(`Generated 3 verified mock postings from ${source.toUpperCase()}`);
  };

  return (
    <div className="space-y-6">
      {/* Live Discovery Control Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Multi-Source Autonomous Job Discovery</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Live Greenhouse boards API poller and source-native parsers with auto-deduplication
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Quick Poll:</span>
            {['stripe', 'discord', 'airbnb', 'cloudflare'].map((token) => (
              <button
                key={token}
                disabled={isScanning}
                onClick={() => {
                  setBoardToken(token);
                  handleLiveGreenhouseScan(token);
                }}
                className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50 transition-all cursor-pointer"
              >
                {token.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Board Input */}
        <div className="mt-4 pt-4 border-t border-slate-800 flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={boardToken}
              onChange={(e) => setBoardToken(e.target.value)}
              placeholder="Enter Greenhouse board token (e.g. reddit, stripe, datadog)..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            onClick={() => handleLiveGreenhouseScan(boardToken)}
            disabled={isScanning || !boardToken.trim()}
            className="flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold disabled:opacity-50 transition-all cursor-pointer"
          >
            {isScanning ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <Globe className="w-3.5 h-3.5" />
                <span>Scan Greenhouse API</span>
              </>
            )}
          </button>
          <button
            onClick={() => handleSimulateSource('remoteok')}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition-all cursor-pointer"
          >
            + RemoteOK
          </button>
          <button
            onClick={() => handleSimulateSource('lever')}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition-all cursor-pointer"
          >
            + Lever
          </button>
        </div>

        {scanMessage && (
          <div className="mt-3 text-xs font-medium text-cyan-400 bg-cyan-950/40 border border-cyan-800/60 px-3 py-2 rounded-xl">
            {scanMessage}
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, company, or stack..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 p-1 rounded-xl text-xs">
            <span className="text-slate-500 px-2 font-medium">Match:</span>
            {['ALL', 'HIGH', 'REVIEW', 'REJECT'].map((r) => (
              <button
                key={r}
                onClick={() => setFilterRec(r)}
                className={`px-2.5 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                  filterRec === r
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {r === 'HIGH' ? '≥70 High' : r === 'REVIEW' ? '40–69' : r === 'REJECT' ? 'Rejected' : 'All'}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 p-1 rounded-xl text-xs">
            <span className="text-slate-500 px-2 font-medium">Source:</span>
            {['ALL', 'greenhouse', 'lever', 'remoteok', 'himalayas'].map((s) => (
              <button
                key={s}
                onClick={() => setFilterSource(s)}
                className={`px-2 py-1 rounded-lg font-semibold capitalize transition-all cursor-pointer ${
                  filterSource === s
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Jobs Listing Grid */}
      <div className="space-y-4">
        {filteredJobs.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/40 border border-slate-800 rounded-2xl">
            <AlertCircle className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-300">No matching jobs found</h3>
            <p className="text-xs text-slate-500 mt-1">
              Try adjusting your search query, filters, or scan a Greenhouse board above.
            </p>
          </div>
        ) : (
          filteredJobs.map((job) => {
            const match = jobMatches[job.id];
            const isExpanded = expandedMatchId === job.id;
            const isRejected = Boolean(match?.hard_filter_reason);

            return (
              <div
                key={job.id}
                className={`bg-slate-900/80 border rounded-2xl p-5 transition-all shadow-sm ${
                  isRejected
                    ? 'border-red-950/70 hover:border-red-900/70 bg-red-950/10'
                    : (match?.match_score || 0) >= 70
                    ? 'border-blue-900/60 hover:border-blue-700/80 bg-blue-950/10'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  {/* Job Details */}
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-extrabold text-white text-base hover:text-blue-400 transition-colors">
                        {job.title}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                        {job.source}
                      </span>
                      {job.remote && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                          REMOTE
                        </span>
                      )}
                      {job.seniority && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                          {job.seniority}
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-slate-400 flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="font-semibold text-slate-200">{job.company}</span>
                      <span>•</span>
                      <span>{job.location}</span>
                      {job.salary_min && (
                        <>
                          <span>•</span>
                          <span className="font-mono text-emerald-400 font-medium">
                            ${(job.salary_min / 1000).toFixed(0)}k–${(job.salary_max! / 1000).toFixed(0)}k {job.salary_currency}
                          </span>
                        </>
                      )}
                      <span>•</span>
                      <span className="text-slate-500 font-mono text-[11px]">
                        Discovered {new Date(job.discovered_at).toLocaleDateString()}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 line-clamp-2 mt-2 leading-relaxed">
                      {job.description}
                    </p>

                    {/* Technologies */}
                    <div className="flex flex-wrap gap-1.5 pt-2">
                      {(job.technologies || []).map((tech) => (
                        <span
                          key={tech}
                          className="px-2 py-0.5 rounded-md text-[11px] font-mono bg-slate-950 text-slate-300 border border-slate-800"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Match Score Badge & Actions */}
                  <div className="flex sm:flex-col items-center sm:items-end justify-between gap-3 shrink-0">
                    <div className="text-right">
                      {isRejected ? (
                        <div className="px-3 py-1.5 rounded-xl bg-red-950/80 border border-red-800 text-red-300 text-xs font-bold flex items-center gap-1.5">
                          <XCircle className="w-4 h-4 text-red-400" />
                          <span>REJECTED</span>
                        </div>
                      ) : (
                        <div
                          className={`px-3 py-1.5 rounded-xl border text-xs font-extrabold flex items-center gap-1.5 ${
                            (match?.match_score || 0) >= 70
                              ? 'bg-blue-950/80 border-blue-600 text-blue-300'
                              : 'bg-amber-950/80 border-amber-700 text-amber-300'
                          }`}
                        >
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                          <span>{match?.match_score} / 100 MATCH</span>
                        </div>
                      )}

                      {isRejected && (
                        <div className="text-[10px] text-red-400 mt-1 font-mono">
                          {match?.hard_filter_reason}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setExpandedMatchId(isExpanded ? null : job.id)}
                        className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1 transition-all cursor-pointer"
                        title="View Score Breakdown"
                      >
                        <SlidersHorizontal className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Score</span>
                        {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>

                      <button
                        onClick={() => onSelectJobForApplication(job.id)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>Application</span>
                      </button>

                      <a
                        href={job.application_url}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 bg-slate-800 border border-slate-700 transition-all"
                        title="Open Source Posting"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>
                </div>

                {/* Score Breakdown Detail Accordion */}
                {isExpanded && match && (
                  <div className="mt-4 pt-4 border-t border-slate-800 bg-slate-950/60 p-4 rounded-xl text-xs space-y-3">
                    <div className="font-bold text-slate-200 flex items-center justify-between">
                      <span>Deterministic Point Breakdown (Max 100)</span>
                      <span className="font-mono text-blue-400">{match.match_score} pts</span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Remote Eligible (20):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.remote}</span>
                      </div>
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Nigeria Eligible (20):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.nigeria}</span>
                      </div>
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Core Stack (20):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.stack}</span>
                      </div>
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Role Title (10):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.role}</span>
                      </div>
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Experience (10):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.experience}</span>
                      </div>
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Domain Match (10):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.domain}</span>
                      </div>
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Salary Target (5):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.salary}</span>
                      </div>
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded">
                        <span className="text-slate-400">Seniority (5):</span>{' '}
                        <span className="font-bold text-white">{match.breakdown.seniority}</span>
                      </div>
                    </div>

                    {match.strong_matches.length > 0 && (
                      <div>
                        <span className="text-slate-400 font-semibold">Matched Stack: </span>
                        <span className="text-emerald-400 font-mono">{match.strong_matches.join(', ')}</span>
                      </div>
                    )}
                    {match.gaps.length > 0 && (
                      <div>
                        <span className="text-slate-400 font-semibold">Stack Gaps: </span>
                        <span className="text-amber-400 font-mono">{match.gaps.join(', ')}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
