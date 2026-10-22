import React, { useState } from 'react';
import { Job } from '../types/job';
import { JobCard } from '../components/JobCard';
import { Bookmark, Search, ArrowRight } from 'lucide-react';

interface SavedJobsPageProps {
  savedJobs: Job[];
  appliedJobIds: string[];
  actionRequiredJobIds?: string[];
  onSelectJob: (job: Job) => void;
  onWhyMatches: (job: Job) => void;
  onToggleSave: (job: Job) => void;
  onQuickApply: (job: Job) => void;
  onNavigateToSearch: () => void;
}

export const SavedJobsPage: React.FC<SavedJobsPageProps> = ({
  savedJobs,
  appliedJobIds,
  actionRequiredJobIds = [],
  onSelectJob,
  onWhyMatches,
  onToggleSave,
  onQuickApply,
  onNavigateToSearch,
}) => {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'match' | 'salary'>('match');

  const filteredJobs = savedJobs
    .filter((j) => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (
        j.title.toLowerCase().includes(q) ||
        j.company.toLowerCase().includes(q) ||
        j.skills.some((s) => s.toLowerCase().includes(q))
      );
    })
    .sort((a, b) => {
      if (sortBy === 'salary') return b.maxSalary - a.maxSalary;
      return b.matchScore - a.matchScore;
    });

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1">
            Saved Opportunities
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Bookmarked positions curated for deeper review or upcoming application deadlines.
          </p>
        </div>

        <span className="text-xs text-slate-400 font-mono">
          {savedJobs.length} {savedJobs.length === 1 ? 'saved role' : 'saved roles'}
        </span>
      </div>

      {savedJobs.length > 0 ? (
        <>
          {/* Search & Sort Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mb-6">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search saved positions..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-[#090d1c] border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400 self-end">
              <span>Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-[#090d1c] border border-slate-800 rounded-lg px-2.5 py-1 text-slate-300 focus:outline-none cursor-pointer"
              >
                <option value="match">Match Score</option>
                <option value="salary">Compensation</option>
              </select>
            </div>
          </div>

          {/* List */}
          <div className="space-y-4">
            {filteredJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isSaved={true}
                isApplied={appliedJobIds.includes(job.id)}
                isActionRequired={actionRequiredJobIds.includes(job.id)}
                onSelect={onSelectJob}
                onWhyMatches={onWhyMatches}
                onToggleSave={onToggleSave}
                onQuickApply={onQuickApply}
              />
            ))}
          </div>
        </>
      ) : (
        /* Empty State */
        <div className="p-12 text-center rounded-2xl bg-[#080d1c] border border-slate-800 space-y-4">
          <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 mx-auto flex items-center justify-center text-slate-500">
            <Bookmark className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white mb-1">No saved jobs yet</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Bookmark positions while exploring matches to compare compensation, evaluate skill gaps, and prepare applications.
            </p>
          </div>
          <button
            onClick={onNavigateToSearch}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors"
          >
            <span>Explore Matched Jobs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
