import React from 'react';
import { Job } from '../types/job';
import { X, Sparkles, CheckCircle2, AlertTriangle, ArrowRight, Compass } from 'lucide-react';

interface WhyMatchesModalProps {
  job: Job | null;
  onClose: () => void;
  onOpenDetails: (job: Job) => void;
}

export const WhyMatchesModal: React.FC<WhyMatchesModalProps> = ({
  job,
  onClose,
  onOpenDetails,
}) => {
  if (!job) return null;

  const { breakdown } = job;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg rounded-2xl bg-[#0a0f20] border border-indigo-500/30 p-6 shadow-2xl shadow-indigo-950/50 text-slate-100 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Glow decoration */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-4 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-indigo-950/80 text-cyan-300 border border-indigo-500/30">
                {job.matchScore}% Match
              </span>
              <span className="text-xs text-slate-400">· {job.company}</span>
            </div>
            <h3 className="text-lg font-semibold text-white tracking-tight">
              {job.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
            aria-label="Close match breakdown"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* AI Alignment Overview */}
        <div className="mb-5 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs sm:text-sm text-slate-300 leading-relaxed">
          <p>{breakdown.summary}</p>
        </div>

        <div className="space-y-4 mb-6">
          {/* Strong Matches */}
          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Strong Matches</span>
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {breakdown.strongMatches.map((skill) => (
                <span
                  key={skill}
                  className="px-2.5 py-1 rounded-md text-xs font-mono bg-emerald-950/40 text-emerald-300 border border-emerald-500/30"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>

          {/* Skill Gaps */}
          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Identified Skill Gaps</span>
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {breakdown.skillGaps.length > 0 ? (
                breakdown.skillGaps.map((gap) => (
                  <span
                    key={gap}
                    className="px-2.5 py-1 rounded-md text-xs font-mono bg-amber-950/40 text-amber-300 border border-amber-500/30"
                  >
                    {gap}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-400">None identified for your level.</span>
              )}
            </div>
          </div>

          {/* Experience Alignment */}
          <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Experience Alignment</span>
            <span className="font-semibold text-cyan-300 font-mono">
              {breakdown.experienceAlignment}
            </span>
          </div>

          {/* Recommended Action */}
          <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-500/20 text-xs">
            <span className="font-semibold text-indigo-300 block mb-1 flex items-center gap-1">
              <Compass className="w-3.5 h-3.5 text-cyan-400" /> Recommended Strategy
            </span>
            <span className="text-slate-300">{breakdown.recommendedAction}</span>
          </div>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-medium text-slate-300 transition-colors"
          >
            Close
          </button>
          <button
            onClick={() => {
              onClose();
              onOpenDetails(job);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors shadow-md shadow-indigo-600/30"
          >
            <span>View Full Position</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
