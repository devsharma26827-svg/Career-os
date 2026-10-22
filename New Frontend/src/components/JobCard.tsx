import React from 'react';
import { Job } from '../types/job';
import { Bookmark, Sparkles, MapPin, Building2, ArrowUpRight, ExternalLink } from 'lucide-react';

interface JobCardProps {
  job: Job;
  isSaved?: boolean;
  isApplied?: boolean;
  isActionRequired?: boolean;
  onSelect: (job: Job) => void;
  onWhyMatches: (job: Job) => void;
  onToggleSave: (job: Job) => void;
  onQuickApply: (job: Job) => void;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  isSaved = false,
  isApplied = false,
  isActionRequired = false,
  onSelect,
  onWhyMatches,
  onToggleSave,
  onQuickApply,
}) => {
  return (
    <div className="group relative rounded-xl bg-[#090d1c]/80 hover:bg-[#0c1226]/90 border border-slate-800/80 hover:border-indigo-500/40 transition-all duration-200 p-5 flex flex-col justify-between shadow-lg shadow-black/20 hover:shadow-indigo-950/20">
      <div>
        {/* Header row: Logo, title, company, match score */}
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-950/70 border border-indigo-500/30 flex items-center justify-center font-bold text-sm text-cyan-300 shrink-0">
              {job.logo}
            </div>
            <div>
              <button
                type="button"
                onClick={() => onSelect(job)}
                className="text-left font-semibold text-white group-hover:text-indigo-200 transition-colors tracking-tight text-base sm:text-lg line-clamp-1 cursor-pointer"
              >
                {job.title}
              </button>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mt-0.5">
                <span className="flex items-center gap-1 font-medium text-slate-300">
                  <Building2 className="w-3.5 h-3.5 text-slate-500" />
                  {job.company}
                </span>
                <span aria-hidden="true" className="text-slate-600">·</span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  {job.location} ({job.workplaceType})
                </span>
                {job.sourceName && (
                  <>
                    <span aria-hidden="true" className="text-slate-600">·</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-slate-900 border border-slate-800 text-slate-400 capitalize">
                      {job.sourceName}
                    </span>
                  </>
                )}
                <span aria-hidden="true" className="text-slate-600">·</span>
                <span className="text-slate-500">{job.postedDate}</span>
              </div>
            </div>
          </div>

          {/* Match Score Badge */}
          <button
            type="button"
            onClick={() => onWhyMatches(job)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition-all cursor-pointer shrink-0 border ${
              job.matchScore > 0
                ? 'bg-indigo-950/70 hover:bg-indigo-900/90 text-cyan-300 border-indigo-500/30 hover:border-cyan-400/50'
                : 'bg-slate-900/90 hover:bg-slate-800 text-slate-400 border-slate-800 hover:border-slate-700'
            }`}
            title={job.matchScore > 0 ? 'Click to view AI match breakdown' : 'Upload your resume to calculate personalized match score'}
          >
            <Sparkles className={`w-3 h-3 ${job.matchScore > 0 ? 'text-cyan-400' : 'text-slate-500'}`} />
            <span className="tabular-nums">
              {job.matchScore > 0 ? `${job.matchScore}% Match` : 'Uncalibrated'}
            </span>
          </button>
        </div>

        {/* Short summary snippet */}
        <p className="text-xs sm:text-sm text-slate-300 line-clamp-2 mb-4 leading-relaxed">
          {job.description}
        </p>

        {/* Key skills metadata */}
        <div className="flex flex-wrap items-center gap-1.5 mb-4">
          {job.skills.map((skill) => (
            <span
              key={skill}
              className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900/90 text-slate-400 border border-slate-800"
            >
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* Footer row: Salary, Why Matches button, Save, View & Apply */}
      <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <span className="font-mono text-slate-200 font-medium">
            {job.salaryRange}
          </span>
          <button
            type="button"
            onClick={() => onWhyMatches(job)}
            className="text-indigo-400 hover:text-indigo-300 underline underline-offset-4 decoration-indigo-500/40 text-[11px] cursor-pointer"
          >
            Why this matches
          </button>
          {job.sourceUrl && (
            <a
              href={job.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-slate-200 flex items-center gap-1 text-[11px] hover:underline"
              title={`View original post on ${job.sourceName || 'source'}`}
            >
              <span>{job.sourceName ? `Listing (${job.sourceName})` : 'Original Post'}</span>
              <ExternalLink className="w-2.5 h-2.5" />
            </a>
          )}
          {job.applicationUrl && job.applicationUrl !== job.sourceUrl && (
            <a
              href={job.applicationUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[11px] hover:underline"
              title="Apply on verified employer website"
            >
              <span>Employer Portal</span>
              <ExternalLink className="w-2.5 h-2.5" />
            </a>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Bookmark Save */}
          <button
            type="button"
            onClick={() => onToggleSave(job)}
            aria-label={isSaved ? 'Remove from saved' : 'Save job'}
            className={`p-2 rounded-lg border transition-colors cursor-pointer ${
              isSaved
                ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Bookmark className={`w-3.5 h-3.5 ${isSaved ? 'fill-current' : ''}`} />
          </button>

          {/* View Details */}
          <button
            type="button"
            onClick={() => onSelect(job)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium transition-colors cursor-pointer"
          >
            View
          </button>

          {/* Apply button */}
          <button
            type="button"
            onClick={() => onQuickApply(job)}
            disabled={isApplied}
            className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              isApplied
                ? 'bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 cursor-default'
                : (isActionRequired
                  ? 'bg-amber-950/70 hover:bg-amber-900/80 border border-amber-500/40 text-amber-300'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm')
            }`}
          >
            <span>{isApplied ? 'Applied' : (isActionRequired ? 'Action Needed' : 'Apply')}</span>
            {!isApplied && <ArrowUpRight className="w-3 h-3" />}
          </button>
        </div>
      </div>
    </div>
  );
};
