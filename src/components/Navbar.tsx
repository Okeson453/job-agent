import React from 'react';
import {
  ShieldAlert,
  Play,
  Pause,
  Terminal,
  Activity,
  Briefcase,
  FileCheck2,
  Cpu,
  UserCheck,
  RotateCcw,
} from 'lucide-react';
import { storage } from '../services/storage';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isPaused: boolean;
  onTogglePause: () => void;
  onOpenTelegram: () => void;
  onResetData: () => void;
  readyCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isPaused,
  onTogglePause,
  onOpenTelegram,
  onResetData,
  readyCount,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 p-0.5 shadow-lg shadow-blue-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <ShieldAlert className="w-5 h-5 text-blue-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                  Job Agent
                </span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/60 font-semibold">
                  v2.0 React
                </span>
              </div>
              <div className="text-xs text-slate-400 flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Truth Engine Autonomous Supervisor</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Pipeline & Stats</span>
            </button>

            <button
              onClick={() => setActiveTab('jobs')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'jobs'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Briefcase className="w-3.5 h-3.5" />
              <span>Jobs & Matcher</span>
            </button>

            <button
              onClick={() => setActiveTab('applications')}
              className={`relative flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'applications'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <FileCheck2 className="w-3.5 h-3.5" />
              <span>Applications</span>
              {readyCount > 0 && (
                <span className="px-1.5 py-0.2 text-[10px] font-bold rounded-full bg-amber-500 text-slate-950">
                  {readyCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('truth')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'truth'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Truth Engine</span>
            </button>

            <button
              onClick={() => setActiveTab('candidate')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'candidate'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Candidate KB</span>
            </button>
          </nav>

          {/* Controls & Actions */}
          <div className="flex items-center space-x-2.5">
            {/* System Pause Toggle */}
            <button
              onClick={onTogglePause}
              title={isPaused ? 'Resume Autonomous Loops' : 'Pause Autonomous Loops'}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                isPaused
                  ? 'bg-amber-950/60 border-amber-600/60 text-amber-300 hover:bg-amber-900/60'
                  : 'bg-emerald-950/50 border-emerald-600/50 text-emerald-300 hover:bg-emerald-900/50'
              }`}
            >
              {isPaused ? (
                <>
                  <Pause className="w-3.5 h-3.5 fill-current" />
                  <span>PAUSED</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>RUNNING</span>
                </>
              )}
            </button>

            {/* Telegram Command Bot Console Launcher */}
            <button
              onClick={onOpenTelegram}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 hover:bg-slate-800 transition-all"
              title="Open Telegram Bot CLI"
            >
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden sm:inline">Bot Terminal</span>
            </button>

            {/* Reset Data */}
            <button
              onClick={onResetData}
              title="Reset sample data"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 border border-transparent hover:border-slate-700 transition-all"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile Nav Bar */}
        <div className="flex md:hidden overflow-x-auto py-2 space-x-2 border-t border-slate-800 text-xs">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-3 py-1 rounded-md whitespace-nowrap ${
              activeTab === 'dashboard' ? 'bg-blue-600 text-white' : 'text-slate-400'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('jobs')}
            className={`px-3 py-1 rounded-md whitespace-nowrap ${
              activeTab === 'jobs' ? 'bg-blue-600 text-white' : 'text-slate-400'
            }`}
          >
            Jobs
          </button>
          <button
            onClick={() => setActiveTab('applications')}
            className={`px-3 py-1 rounded-md whitespace-nowrap ${
              activeTab === 'applications' ? 'bg-blue-600 text-white' : 'text-slate-400'
            }`}
          >
            Applications {readyCount > 0 ? `(${readyCount})` : ''}
          </button>
          <button
            onClick={() => setActiveTab('truth')}
            className={`px-3 py-1 rounded-md whitespace-nowrap ${
              activeTab === 'truth' ? 'bg-blue-600 text-white' : 'text-slate-400'
            }`}
          >
            Truth Engine
          </button>
          <button
            onClick={() => setActiveTab('candidate')}
            className={`px-3 py-1 rounded-md whitespace-nowrap ${
              activeTab === 'candidate' ? 'bg-blue-600 text-white' : 'text-slate-400'
            }`}
          >
            Candidate KB
          </button>
        </div>
      </div>
    </header>
  );
};
