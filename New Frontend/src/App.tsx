import React, { useState, useEffect, useCallback } from 'react';
import { AppState, ActiveTab, Job, UserResume, ApplicationItem, ApplicationStatus } from './types/job';
import { User } from './types/backend';
import { jobService } from './services/jobService';
import { resumeService } from './services/resumeService';
import { applicationService } from './services/applicationService';
import { api, getAuthToken, setAuthToken } from './services/api';

import { AtmosphereBackground } from './three/AtmosphereBackground';
import { GlobeAndPortalCanvas } from './three/GlobeAndPortalCanvas';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { ResumeDropZone } from './sections/ResumeDropZone';
import { SkillOrbitOverlay } from './sections/SkillOrbitOverlay';
import { AnalysisStatusPanel } from './sections/AnalysisStatusPanel';
import { PortalTransitionView } from './sections/PortalTransitionView';
import { JobResultsSection } from './sections/JobResultsSection';
import { HowItWorksSection } from './sections/HowItWorksSection';
import { FeaturesSection } from './sections/FeaturesSection';
import { JobDetailModal } from './components/JobDetailModal';
import { WhyMatchesModal } from './components/WhyMatchesModal';
import { AIAssistantModal } from './components/AIAssistantModal';
import { AuthModal } from './components/AuthModal';

import { ApplicationsPage } from './pages/ApplicationsPage';
import { SavedJobsPage } from './pages/SavedJobsPage';
import { ResumePage } from './pages/ResumePage';
import { InterviewPrepPage } from './pages/InterviewPrepPage';
import { InsightsPage } from './pages/InsightsPage';

export default function App() {
  const [appState, setAppState] = useState<AppState>('idle');
  const [activeTab, setActiveTab] = useState<ActiveTab>('search');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [resume, setResume] = useState<UserResume | null>(null);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [analysisPhase, setAnalysisPhase] = useState<string>('AI is analyzing your profile...');
  const [analysisProgress, setAnalysisProgress] = useState<number>(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Modals state
  const [selectedJobForDetail, setSelectedJobForDetail] = useState<Job | null>(null);
  const [selectedJobForWhyMatches, setSelectedJobForWhyMatches] = useState<Job | null>(null);
  const [targetInterviewJobId, setTargetInterviewJobId] = useState<string | undefined>(undefined);

  // Initialize Auth & Live Data
  useEffect(() => {
    const initData = async () => {
      let activeUser: User | null = null;
      const token = getAuthToken();
      if (token) {
        try {
          activeUser = await api.auth.me();
          setUser(activeUser);
        } catch {
          setAuthToken(null);
        }
      }

      if (activeUser) {
        const [fetchedJobs, fetchedApps, fetchedResume] = await Promise.all([
          jobService.getJobs(),
          applicationService.getApplications(),
          resumeService.getParsedResume(),
        ]);
        setJobs(fetchedJobs);
        setApplications(fetchedApps);
        if (fetchedResume) setResume(fetchedResume);
      } else {
        // Unauthenticated initial state: wait for candidate authentication before querying protected endpoints
        setJobs([]);
        setApplications([]);
        setResume(null);
      }
    };

    initData();
  }, []);

  // Handle session expiration from api.ts
  useEffect(() => {
    const handleAuthExpired = () => {
      setUser(null);
      setResume(null);
      setApplications([]);
      setJobs([]);
      resumeService.clearResume();
      applicationService.clearApplications();
      jobService.clearCache();
      setIsAuthModalOpen(true);
    };

    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, []);

  // Run the staged AI analysis sequence
  const startAnalysisFlow = useCallback(async (uploadedResume: UserResume) => {
    setResume(uploadedResume);
    setUploadError(null);
    setAppState('analyzing');
    setAnalysisProgress(12);
    setAnalysisPhase('Extracting skills & architecture depth...');

    await new Promise((r) => setTimeout(r, 900));
    setAnalysisProgress(38);
    setAnalysisPhase('Understanding systems experience...');

    await new Promise((r) => setTimeout(r, 1100));
    setAnalysisProgress(68);
    setAnalysisPhase('Matching profile against live opportunities...');

    // Refresh jobs calibrated to new resume profile
    const freshJobs = await jobService.getJobs();
    setJobs(freshJobs);

    await new Promise((r) => setTimeout(r, 1100));
    setAppState('searching');
    setAnalysisProgress(88);
    setAnalysisPhase('Searching global opportunity network...');

    await new Promise((r) => setTimeout(r, 1000));
    setAnalysisProgress(100);
    setAppState('portal');
  }, []);

  const processFileUpload = async (file: File) => {
    try {
      setAppState('uploading');
      setAnalysisPhase('Ingesting resume document...');
      setAnalysisProgress(8);
      const parsed = await resumeService.uploadResume(file);
      await startAnalysisFlow(parsed);
    } catch (err: any) {
      setUploadError(err?.message || 'Failed to parse resume document. Please verify file format.');
      setAppState('idle');
    }
  };

  // Handle file drop or selection
  const handleFileSelected = async (file: File) => {
    if (!user) {
      setPendingFile(file);
      setIsAuthModalOpen(true);
      return;
    }
    await processFileUpload(file);
  };

  const handleAuthSuccess = async (authUser: User) => {
    setUser(authUser);
    const [fetchedJobs, fetchedApps, fetchedResume] = await Promise.all([
      jobService.getJobs(),
      applicationService.getApplications(),
      resumeService.getParsedResume(),
    ]);
    setJobs(fetchedJobs);
    setApplications(fetchedApps);
    if (fetchedResume) setResume(fetchedResume);

    if (pendingFile) {
      const fileToUpload = pendingFile;
      setPendingFile(null);
      await processFileUpload(fileToUpload);
    }
  };

  const handleLogout = () => {
    setAuthToken(null);
    setUser(null);
    setResume(null);
    resumeService.clearResume();
    setApplications([]);
    applicationService.clearApplications();
    jobService.clearCache();
    setJobs([]);
    setAppState('idle');
    setActiveTab('search');
  };

  const savedJobIds = applications.filter((a) => a.status === 'saved').map((a) => a.jobId);
  const submittedJobIds = applications
    .filter((a) => a.status === 'applied' && a.isVerifiedSubmission)
    .map((a) => a.jobId);
  const actionRequiredJobIds = applications
    .filter((a) => a.status === 'action_required')
    .map((a) => a.jobId);
  const savedJobs = jobs.filter((j) => savedJobIds.includes(j.id));

  // Applications & Bookmark actions
  const handleToggleSave = async (job: Job) => {
    if (!user) {
      setIsAuthModalOpen(true);
      return;
    }

    const isSaved = savedJobIds.includes(job.id);
    if (isSaved) {
      const appItem = applications.find((a) => a.jobId === job.id && a.status === 'saved');
      if (appItem) {
        await applicationService.removeSaved(appItem.id);
        setApplications((prev) => prev.filter((a) => a.id !== appItem.id));
      }
    } else {
      const newApp = await applicationService.saveJob(job);
      setApplications((prev) => [newApp, ...prev.filter((a) => a.jobId !== job.id)]);
    }
  };

  const handleQuickApply = async (job: Job) => {
    if (!user) {
      setIsAuthModalOpen(true);
      return;
    }

    const updated = await applicationService.applyToJob(job);
    setApplications((prev) => [updated, ...prev.filter((a) => a.jobId !== updated.jobId)]);

    if (updated.status === 'action_required') {
      const targetUrl = updated.manualActionUrl || updated.applicationUrl || job.applicationUrl || job.sourceUrl;
      if (targetUrl && targetUrl.startsWith('http')) {
        window.open(targetUrl, '_blank', 'noopener,noreferrer');
      }
      setSelectedJobForDetail(job);
    }
  };

  const handleMarkSubmitted = async (jobOrId: Job | string) => {
    if (!user) {
      setIsAuthModalOpen(true);
      return;
    }

    const jobId = typeof jobOrId === 'string' ? jobOrId : jobOrId.id;
    const updated = await applicationService.markAsSubmitted(jobId);
    if (updated) {
      setApplications((prev) => [updated, ...prev.filter((a) => a.jobId !== updated.jobId)]);
    }
  };

  const handleUpdateStatus = async (id: string, status: ApplicationStatus) => {
    const updated = await applicationService.updateStatus(id, status);
    if (updated) {
      setApplications((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)));
    }
  };

  const handleNavigateToInterview = (job: Job) => {
    setTargetInterviewJobId(job.id);
    setActiveTab('interview');
  };

  const handleResetToUpload = () => {
    setAppState('idle');
    setActiveTab('search');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#050914] text-slate-100 relative">
      {/* Background Atmosphere */}
      <AtmosphereBackground />

      {/* Navigation */}
      <Navbar
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        savedCount={savedJobs.length}
        applicationsCount={applications.filter((a) => a.status !== 'saved').length}
        onUploadClick={handleResetToUpload}
        user={user}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative z-10">
        {/* Render Page based on active tab */}
        {activeTab === 'applications' && (
          <ApplicationsPage
            applications={applications}
            onUpdateStatus={handleUpdateStatus}
            onOpenJob={(jobId) => {
              const j = jobs.find((x) => x.id === jobId);
              if (j) setSelectedJobForDetail(j);
            }}
            onMarkSubmitted={handleMarkSubmitted}
          />
        )}

        {activeTab === 'saved' && (
          <SavedJobsPage
            savedJobs={savedJobs}
            appliedJobIds={submittedJobIds}
            actionRequiredJobIds={actionRequiredJobIds}
            onSelectJob={setSelectedJobForDetail}
            onWhyMatches={setSelectedJobForWhyMatches}
            onToggleSave={handleToggleSave}
            onQuickApply={handleQuickApply}
            onNavigateToSearch={() => setActiveTab('search')}
          />
        )}

        {activeTab === 'resume' && (
          <ResumePage
            resume={resume}
            onReplaceResume={handleFileSelected}
            onReanalyze={() => {
              if (resume) {
                setActiveTab('search');
                startAnalysisFlow(resume);
              }
            }}
          />
        )}

        {activeTab === 'interview' && (
          <InterviewPrepPage
            jobs={jobs}
            selectedJobId={targetInterviewJobId}
            onSelectJob={(j) => setTargetInterviewJobId(j.id)}
          />
        )}

        {activeTab === 'insights' && (
          <InsightsPage jobs={jobs} applications={applications} />
        )}

        {/* Search Tab: The Central 3D AI Journey */}
        {activeTab === 'search' && (
          <div className="w-full flex-1 flex flex-col">
            {/* Step 1: Idle & Uploading State */}
            {(appState === 'idle' || appState === 'uploading') && (
              <div className="w-full flex flex-col items-center justify-center pt-8 sm:pt-14 pb-12 px-4">
                {/* Concise Hero Heading */}
                <div className="text-center max-w-xl mx-auto mb-8 sm:mb-10">
                  <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-white mb-3 leading-tight">
                    Find jobs that fit you.
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
                    Upload your resume and let AI discover opportunities matched to your verified skills.
                  </p>
                </div>

                {/* Central Circular Upload Dropzone */}
                <ResumeDropZone
                  onFileSelected={handleFileSelected}
                  error={uploadError}
                  onClearError={() => setUploadError(null)}
                />

                {/* Explanatory Landing Sections */}
                <HowItWorksSection />
                <FeaturesSection />
              </div>
            )}

            {/* Step 2: 3D AI Analysis & Opportunity Searching State */}
            {(appState === 'analyzing' || appState === 'searching') && (
              <div className="w-full flex-1 flex flex-col items-center justify-center py-12 px-4">
                <div className="text-center max-w-lg mx-auto mb-6">
                  <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-2">
                    {appState === 'searching'
                      ? 'Scanning Opportunity Networks'
                      : 'AI Analysis in Progress'}
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-400">
                    Extracting technical competencies, engineering depth, and role alignment.
                  </p>
                </div>

                {/* 3D Particle Globe Scene with floating resume inside */}
                <div className="relative w-80 h-80 sm:w-[480px] sm:h-[480px] flex items-center justify-center">
                  <GlobeAndPortalCanvas
                    mode={appState === 'searching' ? 'searching' : 'analyzing'}
                    progress={analysisProgress}
                  />
                  <SkillOrbitOverlay />
                </div>

                {/* Status Panel below globe */}
                <AnalysisStatusPanel
                  phase={analysisPhase}
                  progress={analysisProgress}
                  fileName={resume?.fileName || 'Uploaded_Resume.pdf'}
                />
              </div>
            )}

            {/* Step 3: Portal Transition State (Cards Emerging from Portal) */}
            {appState === 'portal' && (
              <PortalTransitionView
                jobs={jobs}
                onComplete={() => setAppState('results')}
              />
            )}

            {/* Step 4: Final Job Results Experience */}
            {appState === 'results' && (
              <JobResultsSection
                jobs={jobs}
                resume={resume}
                savedJobIds={savedJobIds}
                appliedJobIds={submittedJobIds}
                actionRequiredJobIds={actionRequiredJobIds}
                onSelectJob={setSelectedJobForDetail}
                onWhyMatches={setSelectedJobForWhyMatches}
                onToggleSave={handleToggleSave}
                onQuickApply={handleQuickApply}
                onReupload={handleResetToUpload}
              />
            )}
          </div>
        )}
      </main>

      {/* Persistent AI Assistant */}
      <AIAssistantModal
        currentJob={selectedJobForDetail || undefined}
        resume={resume}
        onSelectSuggestedAction={(action) => {
          if (action.includes('interview')) setActiveTab('interview');
        }}
      />

      {/* Why Matches Modal */}
      <WhyMatchesModal
        job={selectedJobForWhyMatches}
        onClose={() => setSelectedJobForWhyMatches(null)}
        onOpenDetails={(job) => {
          setSelectedJobForWhyMatches(null);
          setSelectedJobForDetail(job);
        }}
      />

      {/* Job Detail Modal */}
      <JobDetailModal
        job={selectedJobForDetail}
        resume={resume}
        isSaved={selectedJobForDetail ? savedJobIds.includes(selectedJobForDetail.id) : false}
        isApplied={selectedJobForDetail ? submittedJobIds.includes(selectedJobForDetail.id) : false}
        applicationItem={selectedJobForDetail ? applications.find((a) => a.jobId === selectedJobForDetail.id) : null}
        onClose={() => setSelectedJobForDetail(null)}
        onToggleSave={handleToggleSave}
        onApply={handleQuickApply}
        onMarkSubmitted={handleMarkSubmitted}
        onNavigateToInterview={handleNavigateToInterview}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />

      {/* Footer */}
      <Footer />
    </div>
  );
}
