import React, { useState } from 'react';
import { Job, UserResume, ApplicationItem } from '../types/job';
import { aiService } from '../services/aiService';
import {
  X,
  Building2,
  MapPin,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Mail,
  GraduationCap,
  ArrowUpRight,
  Copy,
  Check,
  Bookmark,
  ExternalLink,
  ShieldCheck,
  Globe,
  Clock,
} from 'lucide-react';

interface JobDetailModalProps {
  job: Job | null;
  resume: UserResume | null;
  isSaved?: boolean;
  isApplied?: boolean;
  applicationItem?: ApplicationItem | null;
  onClose: () => void;
  onToggleSave: (job: Job) => void;
  onApply: (job: Job) => void;
  onMarkSubmitted?: (job: Job) => void;
  onNavigateToInterview: (job: Job) => void;
}

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  resume,
  isSaved = false,
  isApplied = false,
  applicationItem,
  onClose,
  onToggleSave,
  onApply,
  onMarkSubmitted,
  onNavigateToInterview,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'tailored_resume' | 'cover_letter' | 'evidence'>('overview');
  const [tailoredBullets, setTailoredBullets] = useState<string[]>([]);
  const [coverLetter, setCoverLetter] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!job) return null;

  const handleTailorResume = async () => {
    setActiveTab('tailored_resume');
    if (tailoredBullets.length > 0 || !resume) return;
    setIsGenerating(true);
    try {
      const bullets = await aiService.tailorResumeBulletPoints(job, resume);
      setTailoredBullets(bullets);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateCoverLetter = async () => {
    setActiveTab('cover_letter');
    if (coverLetter || !resume) return;
    setIsGenerating(true);
    try {
      const letter = await aiService.generateCoverLetter(job, resume);
      setCoverLetter(letter);
    } finally {
      setIsGenerating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isConfirmedSubmitted = isApplied || applicationItem?.status === 'applied' || applicationItem?.isVerifiedSubmission;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md overflow-y-auto"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-5xl max-h-[90vh] rounded-2xl bg-[#090d1c] border border-slate-800 shadow-2xl flex flex-col overflow-hidden text-slate-100 my-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header Bar */}
        <div className="p-5 sm:p-6 border-b border-slate-800/80 flex items-start justify-between gap-4 bg-[#0a0f22]/70">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-950/80 border border-indigo-500/30 flex items-center justify-center font-bold text-base text-cyan-300 shrink-0">
              {job.logo}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-semibold border ${
                  job.matchScore > 0
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30'
                    : 'bg-slate-900 text-slate-400 border-slate-800'
                }`}>
                  {job.matchScore > 0 ? `${job.matchScore}% Match` : 'Uncalibrated'}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {job.employmentType} · {job.experienceLevel} Level
                </span>
                {job.sourceName && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-900 border border-slate-800 text-indigo-300 capitalize flex items-center gap-1">
                    <Globe className="w-3 h-3 text-indigo-400" />
                    <span>{job.sourceName}</span>
                  </span>
                )}
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                {job.title}
              </h2>
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
                <span className="flex items-center gap-1 text-slate-300 font-medium">
                  <Building2 className="w-3.5 h-3.5 text-slate-500" />
                  {job.company}
                </span>
                <span aria-hidden="true">·</span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  {job.location} ({job.workplaceType})
                </span>
                <span aria-hidden="true">·</span>
                <span className="font-mono text-slate-300 font-semibold">{job.salaryRange}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onToggleSave(job)}
              className={`p-2 rounded-lg border transition-colors ${
                isSaved
                  ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
              }`}
              title={isSaved ? 'Remove Bookmark' : 'Bookmark Job'}
            >
              <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-2 px-6 pt-3 border-b border-slate-800/60 bg-[#080c18] text-xs">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-2.5 px-3 font-medium transition-colors border-b-2 cursor-pointer ${
              activeTab === 'overview'
                ? 'border-indigo-500 text-white'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Position & Analysis
          </button>
          <button
            onClick={handleTailorResume}
            className={`pb-2.5 px-3 font-medium transition-colors border-b-2 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'tailored_resume'
                ? 'border-indigo-500 text-white'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-indigo-400" />
            <span>Tailor Resume</span>
          </button>
          <button
            onClick={handleGenerateCoverLetter}
            className={`pb-2.5 px-3 font-medium transition-colors border-b-2 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'cover_letter'
                ? 'border-indigo-500 text-white'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Mail className="w-3.5 h-3.5 text-cyan-400" />
            <span>Generate Cover Letter</span>
          </button>
          <button
            onClick={() => setActiveTab('evidence')}
            className={`pb-2.5 px-3 font-medium transition-colors border-b-2 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'evidence'
                ? 'border-indigo-500 text-white'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Source & Evidence</span>
          </button>
        </div>

        {/* Body Container */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Job Description & Details */}
              <div className="lg:col-span-7 space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2">
                    About the Role
                  </h3>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {job.description}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2">
                    Responsibilities
                  </h3>
                  <ul className="space-y-2 text-sm text-slate-300">
                    {job.responsibilities.map((resp, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-2 shrink-0" />
                        <span>{resp}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2">
                    Technical Requirements
                  </h3>
                  <ul className="space-y-2 text-sm text-slate-300">
                    {job.requirements.map((req, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-2 shrink-0" />
                        <span>{req}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2">
                    Compensation & Benefits
                  </h3>
                  <ul className="space-y-2 text-sm text-slate-300">
                    {job.benefits.map((b, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Right Column: AI Analysis Panel */}
              <div className="lg:col-span-5 flex flex-col gap-4">
                <div className="p-5 rounded-xl bg-[#0d1326] border border-indigo-500/30 shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5 uppercase tracking-wider">
                      <Sparkles className="w-4 h-4 text-cyan-400" /> AI Alignment Analysis
                    </span>
                    <span className="text-xs font-mono font-bold text-cyan-300">
                      {job.matchScore}% Match
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed mb-4">
                    {job.breakdown.summary}
                  </p>

                  <div className="space-y-3 pt-3 border-t border-slate-800/80 text-xs">
                    <div>
                      <span className="text-slate-400 font-medium block mb-1.5">
                        Your Strengths
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {job.breakdown.strongMatches.map((s) => (
                          <span
                            key={s}
                            className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/30 text-[11px] font-mono"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 font-medium block mb-1.5">
                        Potential Gaps
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {job.breakdown.skillGaps.map((s) => (
                          <span
                            key={s}
                            className="px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-500/30 text-[11px] font-mono"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-500/20 mt-2">
                      <span className="font-semibold text-indigo-300 block mb-1">
                        Strategy Recommendation
                      </span>
                      <span className="text-slate-300 text-[11px]">
                        {job.breakdown.recommendedAction}
                      </span>
                    </div>
                  </div>
                </div>

                {/* AI Action Buttons */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                    Action Tools
                  </span>

                  <button
                    onClick={handleTailorResume}
                    className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-medium text-slate-200 flex items-center justify-between transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Tailor Resume for Role</span>
                    </span>
                    <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
                  </button>

                  <button
                    onClick={handleGenerateCoverLetter}
                    className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-medium text-slate-200 flex items-center justify-between transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Generate Tailored Cover Letter</span>
                    </span>
                    <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
                  </button>

                  <button
                    onClick={() => {
                      onClose();
                      onNavigateToInterview(job);
                    }}
                    className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-medium text-slate-200 flex items-center justify-between transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <GraduationCap className="w-3.5 h-3.5 text-amber-400" />
                      <span>Prepare for Interview</span>
                    </span>
                    <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'tailored_resume' && (
            <div className="max-w-3xl mx-auto space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white tracking-tight mb-1">
                  AI-Tailored Resume Bullet Points
                </h3>
                <p className="text-xs text-slate-400">
                  Custom achievements tuned specifically to mirror {job.company}'s requirements for {job.title}.
                </p>
              </div>

              {isGenerating ? (
                <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
                  <Sparkles className="w-6 h-6 text-indigo-400 animate-spin" />
                  <span className="text-xs font-mono">Synthesizing role-specific achievements...</span>
                </div>
              ) : (
                <div className="space-y-4">
                  {tailoredBullets.map((bullet, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start justify-between gap-4"
                    >
                      <p className="text-sm text-slate-200 leading-relaxed font-sans">{bullet}</p>
                      <button
                        onClick={() => copyToClipboard(bullet)}
                        className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white shrink-0"
                        title="Copy bullet"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}

                  <div className="flex justify-end gap-3 pt-4">
                    <button
                      onClick={() => copyToClipboard(tailoredBullets.join('\n\n'))}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors"
                    >
                      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Copied All to Clipboard' : 'Copy All Bullets'}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'cover_letter' && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white tracking-tight mb-1">
                    AI-Generated Cover Letter
                  </h3>
                  <p className="text-xs text-slate-400">
                    Targeted for {job.company} — {job.title}
                  </p>
                </div>
                {coverLetter && (
                  <button
                    onClick={() => copyToClipboard(coverLetter)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 hover:text-white transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy Letter'}</span>
                  </button>
                )}
              </div>

              {isGenerating ? (
                <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-3">
                  <Sparkles className="w-6 h-6 text-cyan-400 animate-spin" />
                  <span className="text-xs font-mono">Drafting personalized cover letter...</span>
                </div>
              ) : (
                <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 text-sm text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
                  {coverLetter}
                </div>
              )}
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="max-w-3xl mx-auto space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white tracking-tight mb-1">
                  Traceable Origin & Application Audit
                </h3>
                <p className="text-xs text-slate-400">
                  Verifiable metadata, genuine employer posting links, and submission state tracking.
                </p>
              </div>

              {/* Source Verification Card */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-cyan-400" />
                    <span className="text-xs font-semibold text-slate-200">Origin Job Source</span>
                  </div>
                  <span className="text-xs font-mono text-cyan-300 font-semibold uppercase">
                    {job.sourceName || 'Direct ATS'}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 block mb-1">Listing Identifier</span>
                    <span className="font-mono text-slate-300">{job.sourceId || job.id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-1">Retrieved / Synced At</span>
                    <span className="font-mono text-slate-300">
                      {job.retrievedAt ? new Date(job.retrievedAt).toLocaleString() : job.postedDate}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-1">Submission Destination</span>
                    <span className="font-mono text-indigo-300">
                      {applicationItem?.destinationType || 'Manual Employer Portal / ATS'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-1">Link Authenticity</span>
                    <span className="font-mono text-emerald-400 flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>{job.isVerifiedLink !== false ? 'Verified Official Source' : 'External Web Link'}</span>
                    </span>
                  </div>
                </div>

                <div className="pt-2 flex flex-wrap gap-2.5">
                  {job.applicationUrl ? (
                    <a
                      href={job.applicationUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors"
                    >
                      <span>Apply on Official Employer Website</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  ) : (
                    <span className="text-xs text-slate-500 italic flex items-center gap-1">
                      <span>Direct ATS link not published in {job.sourceName || 'board'} feed; refer to source listing.</span>
                    </span>
                  )}
                  {job.sourceUrl && (
                    <a
                      href={job.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-300 hover:text-white transition-colors"
                    >
                      <span>View Original Listing ({job.sourceName || 'Source'})</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>

              {/* Real Submission Evidence & Tracking */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-semibold text-slate-200">Application Audit Trail</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${
                    isConfirmedSubmitted
                      ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40'
                      : (applicationItem?.status === 'action_required'
                        ? 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                        : 'bg-slate-900 text-slate-400 border-slate-800')
                  }`}>
                    {isConfirmedSubmitted
                      ? 'Verified Submitted'
                      : (applicationItem?.status === 'action_required'
                        ? 'Candidate Action Required'
                        : 'Not Yet Applied')}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {applicationItem?.notes || (isConfirmedSubmitted
                    ? 'Application has been confirmed as submitted to employer.'
                    : 'External portal submission requires candidate review on employer website.')}
                </p>

                {applicationItem?.confirmationId && (
                  <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 font-mono text-[11px] text-slate-300">
                    <span className="text-slate-500 block mb-0.5">Confirmation Reference:</span>
                    <span>{applicationItem.confirmationId}</span>
                  </div>
                )}

                {/* Confirm Action for manual portals */}
                {!isConfirmedSubmitted && onMarkSubmitted && (
                  <div className="pt-2 flex flex-wrap items-center gap-3">
                    {job.sourceUrl && (
                      <a
                        href={job.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-white transition-colors"
                      >
                        <span>Step 1: Open Employer Form</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => onMarkSubmitted(job)}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-medium text-white transition-colors cursor-pointer shadow-md"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Step 2: Confirm & Mark as Submitted</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Apply Bar */}
        <div className="p-4 sm:p-5 border-t border-slate-800 bg-[#080c18] flex items-center justify-between gap-4">
          <div className="text-xs text-slate-400 font-mono hidden sm:block">
            Target Match: <span className="text-cyan-300 font-semibold">{job.matchScore > 0 ? `${job.matchScore}%` : 'Uncalibrated'}</span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-medium text-slate-300 transition-colors"
            >
              Close
            </button>
            {isConfirmedSubmitted ? (
              <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 cursor-default">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Application Submitted</span>
              </span>
            ) : (
              <div className="flex items-center gap-2">
                {job.applicationUrl ? (
                  <a
                    href={job.applicationUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => onApply(job)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white shadow-indigo-600/30 transition-colors"
                  >
                    <span>Apply on Employer Website</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                ) : (job.sourceUrl ? (
                  <a
                    href={job.sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => onApply(job)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white shadow-indigo-600/30 transition-colors"
                  >
                    <span>Apply via {job.sourceName ? `${job.sourceName} Listing` : 'Listing'}</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                ) : (
                  <button
                    onClick={() => onApply(job)}
                    className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30 transition-colors"
                  >
                    <span>Submit Application</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                ))}
                {onMarkSubmitted && (
                  <button
                    type="button"
                    onClick={() => onMarkSubmitted(job)}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 hover:text-white transition-colors cursor-pointer"
                    title="Mark application as finished and submitted on employer site"
                  >
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Mark Submitted</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
