import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardTab } from './components/DashboardTab';
import { JobsTab } from './components/JobsTab';
import { ApplicationsTab } from './components/ApplicationsTab';
import { TruthEngineTab } from './components/TruthEngineTab';
import { CandidateTab } from './components/CandidateTab';
import { TelegramBotModal } from './components/TelegramBotModal';
import { storage } from './services/storage';
import {
  Application,
  ApplicationEvent,
  CandidateFact,
  CandidateProfile,
  DailyStats,
  Job,
  JobState,
  SourceStats,
} from './types';
import { fetchGreenhouseBoard } from './services/discoveryService';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [isPaused, setIsPaused] = useState<boolean>(() => storage.isSystemPaused());
  const [isTelegramOpen, setIsTelegramOpen] = useState<boolean>(false);

  // Application selection & filtering across tabs
  const [appFilterState, setAppFilterState] = useState<string | null>(null);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);

  // Reactive state synced with storage
  const [profile, setProfile] = useState<CandidateProfile>(() => storage.getProfile());
  const [facts, setFacts] = useState<CandidateFact[]>(() => storage.getFacts());
  const [projects, setProjects] = useState(() => storage.getProjects());
  const [skills, setSkills] = useState(() => storage.getSkills());
  const [answers, setAnswers] = useState(() => storage.getAnswers());
  const [jobs, setJobs] = useState<Job[]>(() => storage.getJobs());
  const [applications, setApplications] = useState<Application[]>(() => storage.getApplications());
  const [events, setEvents] = useState<ApplicationEvent[]>(() => storage.getEvents());
  const [stats, setStats] = useState<DailyStats>(() => storage.getDailyStats());
  const [sourceStats, setSourceStats] = useState<SourceStats[]>(() => storage.getSourceStats());

  const refreshAllData = () => {
    setIsPaused(storage.isSystemPaused());
    setProfile(storage.getProfile());
    setFacts(storage.getFacts());
    setProjects(storage.getProjects());
    setSkills(storage.getSkills());
    setAnswers(storage.getAnswers());
    setJobs(storage.getJobs());
    setApplications(storage.getApplications());
    setEvents(storage.getEvents());
    setStats(storage.getDailyStats());
    setSourceStats(storage.getSourceStats());
  };

  const handleTogglePause = () => {
    const next = !isPaused;
    storage.setSystemPaused(next);
    setIsPaused(next);
    refreshAllData();
  };

  const handleResetData = () => {
    if (window.confirm('Reset all jobs, applications, and settings back to repository seeds?')) {
      storage.resetToDefaults();
      refreshAllData();
    }
  };

  const handleAddJobs = (newJobs: Job[]) => {
    storage.addJobs(newJobs);
    refreshAllData();
  };

  const handleTransitionApp = (
    appId: string,
    toState: JobState,
    detail?: string,
    extra?: Partial<Application>
  ) => {
    storage.transitionApplication(appId, toState, detail, extra);
    refreshAllData();
  };

  const handleNavigateToApplications = (tab: string, stateFilter?: string) => {
    setActiveTab(tab);
    if (stateFilter) {
      setAppFilterState(stateFilter);
    }
  };

  const handleSelectJobForApplication = (jobId: string) => {
    const app = storage.getApplicationForJob(jobId);
    if (app) {
      setSelectedAppId(app.id);
    } else {
      setSelectedAppId(jobId);
    }
    setActiveTab('applications');
  };

  const handleTriggerQuickScan = async () => {
    try {
      const fetched = await fetchGreenhouseBoard('discord');
      if (fetched.length > 0) {
        storage.addJobs(fetched);
        refreshAllData();
      }
    } catch (e) {
      console.warn('Quick scan error:', e);
    }
  };

  const readyCount = applications.filter((a) => a.state === 'READY').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={(t) => {
          setActiveTab(t);
          setAppFilterState(null);
          setSelectedAppId(null);
        }}
        isPaused={isPaused}
        onTogglePause={handleTogglePause}
        onOpenTelegram={() => setIsTelegramOpen(true)}
        onResetData={handleResetData}
        readyCount={readyCount}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <DashboardTab
            stats={stats}
            sourceStats={sourceStats}
            events={events}
            applications={applications}
            jobs={jobs}
            isPaused={isPaused}
            onNavigateToTab={handleNavigateToApplications}
            onTriggerQuickScan={handleTriggerQuickScan}
          />
        )}

        {activeTab === 'jobs' && (
          <JobsTab
            jobs={jobs}
            profile={profile}
            onAddJobs={handleAddJobs}
            onSelectJobForApplication={handleSelectJobForApplication}
          />
        )}

        {activeTab === 'applications' && (
          <ApplicationsTab
            applications={applications}
            jobs={jobs}
            facts={facts}
            events={events}
            selectedAppId={selectedAppId}
            onSelectApp={setSelectedAppId}
            onTransition={handleTransitionApp}
            initialFilterState={appFilterState}
          />
        )}

        {activeTab === 'truth' && (
          <TruthEngineTab
            facts={facts}
            onAddFact={(f) => {
              storage.addFact(f);
              refreshAllData();
            }}
          />
        )}

        {activeTab === 'candidate' && (
          <CandidateTab
            profile={profile}
            projects={projects}
            skills={skills}
            answers={answers}
            onUpdateProfile={(up) => {
              storage.updateProfile(up);
              refreshAllData();
            }}
            onAddAnswer={(cat, q, a) => {
              storage.addAnswer(cat, q, a);
              refreshAllData();
            }}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/60 py-4 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            Truth Principle: <code className="text-slate-400">VERIFIED → IMPLEMENTED → DESIGNED → RESEARCH → CONCEPT</code>
          </div>
          <div>Autonomous Job Agent • React SPA Port</div>
        </div>
      </footer>

      {/* Telegram Command CLI Modal */}
      <TelegramBotModal
        isOpen={isTelegramOpen}
        onClose={() => setIsTelegramOpen(false)}
        onRefreshData={refreshAllData}
      />
    </div>
  );
};
export default App;
