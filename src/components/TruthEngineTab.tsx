import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
  ArrowRight,
  Play,
  RotateCcw,
  Sparkles,
  Search,
  BookOpen,
} from 'lucide-react';
import { CandidateFact, Claim, EvidenceLevel, ValidationResult } from '../types';
import { canSupport, EVIDENCE_ORDER, extractClaims, getEvidenceRank, validateClaims } from '../services/evidenceEngine';

interface TruthEngineTabProps {
  facts: CandidateFact[];
  onAddFact: (fact: Omit<CandidateFact, 'id' | 'created_at'>) => void;
}

const SAMPLE_TESTS = [
  {
    title: 'Overstated Deployment Claim (Violates Rule)',
    text: 'I built and deployed TestingEngine as a production trading platform using TypeScript and PostgreSQL.',
    expected: 'BLOCKED: TestingEngine is only DESIGNED; cannot support IMPLEMENTED claim',
  },
  {
    title: 'Legitimate Implemented Claim (Passes)',
    text: 'I built CrashWave real-time streaming engine with WebSockets and Redis, handling low-latency telemetry.',
    expected: 'ACCEPTED: CrashWave is verified IMPLEMENTED in the repository',
  },
  {
    title: 'Legitimate Design Claim (Passes)',
    text: 'I designed TestingEngine architecture for automated multi-environment test runs.',
    expected: 'ACCEPTED: TestingEngine is DESIGNED, so claiming DESIGNED matches',
  },
  {
    title: 'Research Analysis Claim (Passes)',
    text: 'I researched OrionSentinel automated intrusion detection heuristics using Python and Linux.',
    expected: 'ACCEPTED: OrionSentinel is verified in research evidence tier',
  },
];

export const TruthEngineTab: React.FC<TruthEngineTabProps> = ({ facts, onAddFact }) => {
  const [inputText, setInputText] = useState(SAMPLE_TESTS[0].text);
  const [extracted, setExtracted] = useState<Claim[]>(() => extractClaims(SAMPLE_TESTS[0].text));
  const [validation, setValidation] = useState<ValidationResult>(() =>
    validateClaims(extractClaims(SAMPLE_TESTS[0].text), facts)
  );

  const [simClaimed, setSimClaimed] = useState<EvidenceLevel>('implemented');
  const [simActual, setSimActual] = useState<EvidenceLevel>('designed');

  const handleValidateText = (text: string) => {
    setInputText(text);
    const claims = extractClaims(text);
    setExtracted(claims);
    const val = validateClaims(claims, facts);
    setValidation(val);
  };

  const isRuleSupported = canSupport(simClaimed, simActual);

  return (
    <div className="space-y-6">
      {/* Governing Principle Banner */}
      <div className="bg-gradient-to-r from-blue-950/70 via-slate-900 to-indigo-950/60 border border-blue-900/50 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                Governing Principle (§6)
              </span>
              <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" /> Fail-Closed Truth Engine
              </span>
            </div>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">
              Evidence Hierarchy & can_support(claimed, actual)
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              "The system may describe what the candidate designed or researched. It must never imply deployment or production operation unless that is separately, explicitly verified in the candidate knowledge base."
            </p>
          </div>
        </div>

        {/* Visual Hierarchy Track */}
        <div className="mt-5 pt-4 border-t border-slate-800">
          <div className="text-[11px] font-mono font-semibold text-slate-400 mb-2 uppercase tracking-wider">
            Strict Precedence: Strongest → Weakest
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {EVIDENCE_ORDER.map((level, idx) => (
              <React.Fragment key={level}>
                <div
                  className={`px-3 py-1.5 rounded-xl border text-xs font-mono font-bold uppercase transition-all ${
                    level === 'verified'
                      ? 'bg-emerald-950/80 border-emerald-500 text-emerald-300'
                      : level === 'implemented'
                      ? 'bg-blue-950/80 border-blue-500 text-blue-300'
                      : level === 'partially_implemented'
                      ? 'bg-cyan-950/80 border-cyan-500 text-cyan-300'
                      : level === 'designed'
                      ? 'bg-amber-950/80 border-amber-500 text-amber-300'
                      : level === 'research'
                      ? 'bg-purple-950/80 border-purple-500 text-purple-300'
                      : 'bg-slate-900 border-slate-700 text-slate-400'
                  }`}
                >
                  <span className="opacity-60 text-[10px] mr-1.5 font-normal">#{idx + 1}</span>
                  {level.replace('_', ' ')}
                </div>
                {idx < EVIDENCE_ORDER.length - 1 && (
                  <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Two Column Layout: Interactive Validator & can_support Matrix Playground */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Claim Validator (2 columns) */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Real-Time Claim Validator & Sandbox</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Tests sentence splitting, marker verb inference, and repository fact grounding.
              </p>
            </div>
            <button
              onClick={() => handleValidateText(SAMPLE_TESTS[0].text)}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          </div>

          {/* Test Presets */}
          <div className="flex flex-wrap gap-2 pt-1">
            {SAMPLE_TESTS.map((test, i) => (
              <button
                key={i}
                onClick={() => handleValidateText(test.text)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
                  inputText === test.text
                    ? 'bg-blue-600 text-white border-blue-500 shadow-sm'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border-slate-800'
                }`}
              >
                {test.title}
              </button>
            ))}
          </div>

          {/* Text Input */}
          <div>
            <textarea
              rows={3}
              value={inputText}
              onChange={(e) => handleValidateText(e.target.value)}
              placeholder="Paste generated cover letter text or claim assertion..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 leading-relaxed"
            />
          </div>

          {/* Output Verdict Card */}
          <div
            className={`p-4 rounded-xl border ${
              validation.all_accepted
                ? 'bg-emerald-950/30 border-emerald-800 text-emerald-200'
                : 'bg-rose-950/30 border-rose-800 text-rose-200'
            }`}
          >
            <div className="flex items-center justify-between font-bold text-sm">
              <span className="flex items-center gap-2">
                {validation.all_accepted ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-400" />
                )}
                <span>
                  {validation.all_accepted
                    ? 'GATE PASSED: SAFE FOR SUBMISSION'
                    : 'GATE BLOCKED: SUBMISSION HALTED'}
                </span>
              </span>
              <span className="font-mono text-xs px-2.5 py-0.5 rounded uppercase font-bold bg-slate-950/80 border border-current">
                {validation.verdicts.length} Claims Extracted
              </span>
            </div>

            {/* Verdict details */}
            <div className="mt-3 space-y-2 text-xs">
              {validation.verdicts.map((v, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border bg-slate-950/80 ${
                    v.outcome === 'accepted'
                      ? 'border-emerald-800/60 text-slate-200'
                      : 'border-rose-800/80 text-rose-200'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-white">"{v.claim.text}"</span>
                    <span
                      className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold uppercase shrink-0 ${
                        v.outcome === 'accepted'
                          ? 'bg-emerald-950 text-emerald-400'
                          : 'bg-rose-950 text-rose-300'
                      }`}
                    >
                      {v.outcome}
                    </span>
                  </div>

                  <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-slate-400">
                    {v.claim.claimed_level && (
                      <span>
                        Claimed:{' '}
                        <strong className="text-amber-400">{v.claim.claimed_level}</strong>
                      </span>
                    )}
                    {v.actual_level && (
                      <span>
                        Repository Fact:{' '}
                        <strong className="text-blue-400">{v.actual_level}</strong>
                      </span>
                    )}
                    {v.claim.project_ref && (
                      <span>
                        Project: <strong className="text-cyan-400">{v.claim.project_ref}</strong>
                      </span>
                    )}
                  </div>

                  <div className="mt-1 text-[11px] text-slate-300 italic">
                    Reason: {v.reason}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Rule Math Playground: can_support(claimed, actual) (1 column) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-amber-400" />
              <span>can_support() Rule Sandbox</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Verify any pair of claimed vs actual evidence levels.
            </p>
          </div>

          <div className="space-y-3 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs">
            <div>
              <label className="block text-slate-400 font-semibold mb-1">
                Claimed Level in Output:
              </label>
              <select
                value={simClaimed}
                onChange={(e) => setSimClaimed(e.target.value as EvidenceLevel)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white font-mono"
              >
                {EVIDENCE_ORDER.map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {lvl.toUpperCase()} (rank {getEvidenceRank(lvl)})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-400 font-semibold mb-1">
                Actual Verified Level in KB:
              </label>
              <select
                value={simActual}
                onChange={(e) => setSimActual(e.target.value as EvidenceLevel)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white font-mono"
              >
                {EVIDENCE_ORDER.map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {lvl.toUpperCase()} (rank {getEvidenceRank(lvl)})
                  </option>
                ))}
              </select>
            </div>

            <div
              className={`p-3.5 rounded-xl border text-center font-bold font-mono transition-all ${
                isRuleSupported
                  ? 'bg-emerald-950/60 border-emerald-600 text-emerald-300'
                  : 'bg-rose-950/60 border-rose-600 text-rose-300'
              }`}
            >
              <div className="text-sm">
                can_support('{simClaimed}', '{simActual}')
              </div>
              <div className="text-lg font-black mt-1">
                {isRuleSupported ? 'TRUE (ALLOWED)' : 'FALSE (BLOCKED)'}
              </div>
              <div className="text-[10px] font-normal opacity-80 mt-1">
                {isRuleSupported
                  ? `Actual (${simActual}) is rank ${getEvidenceRank(simActual)} ≤ Claimed (${simClaimed}) rank ${getEvidenceRank(simClaimed)}`
                  : `Actual (${simActual}) rank ${getEvidenceRank(simActual)} > Claimed (${simClaimed}) rank ${getEvidenceRank(simClaimed)} (downgrade violation)`}
              </div>
            </div>
          </div>

          <div className="text-xs text-slate-400 bg-slate-950/40 p-3 rounded-xl border border-slate-800/80 leading-relaxed">
            <strong className="text-slate-300">Unit Test Reference:</strong>
            <p className="font-mono text-[11px] mt-1 text-slate-400">
              `scripts/verify_evidence_rule.py`
            </p>
            <p className="mt-1">
              "DESIGNED must not support IMPLEMENTED. Overstated deployment claim is blocked by default."
            </p>
          </div>
        </div>
      </div>

      {/* Candidate Facts Registry */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-emerald-400" />
              <span>Verified Evidence Registry (Facts Grounding Table)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Source documents, evidence tiers, and verification tags stored in candidate repository.
            </p>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
            {facts.length} Verified Facts
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-mono uppercase text-[10px] border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3">Evidence Tier</th>
                <th className="py-2.5 px-3">Fact Summary</th>
                <th className="py-2.5 px-3">Source Document</th>
                <th className="py-2.5 px-3">Verified</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {facts.map((fact) => (
                <tr key={fact.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-2.5 px-3 uppercase text-blue-400 font-semibold">{fact.category}</td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                        fact.evidence_level === 'verified'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : fact.evidence_level === 'implemented'
                          ? 'bg-blue-950 text-blue-300 border border-blue-800'
                          : fact.evidence_level === 'designed'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-purple-950 text-purple-300 border border-purple-800'
                      }`}
                    >
                      {fact.evidence_level}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-sans text-slate-200">
                    <div className="font-semibold">{fact.fact}</div>
                    <div className="text-[11px] text-slate-400">{fact.value}</div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-400 text-[11px]">{fact.source_document}</td>
                  <td className="py-2.5 px-3">
                    {fact.verified ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>YES</span>
                      </span>
                    ) : (
                      <span className="text-amber-400">NO</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
