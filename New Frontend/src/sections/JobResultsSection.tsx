import React, { useState, useMemo } from 'react';
import { Job, JobFilterState, UserResume } from '../types/job';
import { JobCard } from '../components/JobCard';
import { JobFilters } from '../components/JobFilters';
import { RefreshCw, FileText } from 'lucide-react';

interface JobResultsSectionProps {
  jobs: Job[];
  resume?: UserResume | null;
  savedJobIds: string[];
  appliedJobIds: string[];
  actionRequiredJobIds?: string[];
  onSelectJob: (job: Job) => void;
  onWhyMatches: (job: Job) => void;
  onToggleSave: (job: Job) => void;
  onQuickApply: (job: Job) => void;
  onReupload: () => void;
}

export const JobResultsSection: React.FC<JobResultsSectionProps> = ({
  jobs,
  resume,
  savedJobIds,
  appliedJobIds,
  actionRequiredJobIds = [],
  onSelectJob,
  onWhyMatches,
  onToggleSave,
  onQuickApply,
  onReupload,
}) => {
  const [filters, setFilters] = useState<JobFilterState>({
    searchQuery: '',
    role: 'All',
    location: 'All',
    workplaceType: 'All',
    experienceLevel: 'All',
    minMatch: 0,
    sortBy: 'match',
  });

  const filteredJobs = useMemo(() => {
    let list = [...jobs];

    if (filters.searchQuery.trim()) {
      const q = filters.searchQuery.toLowerCase().trim();
      list = list.filter(
        (j) =>
          j.title.toLowerCase().includes(q) ||
          j.company.toLowerCase().includes(q) ||
          j.skills.some((s) => s.toLowerCase().includes(q)) ||
          j.location.toLowerCase().includes(q)
      );
    }

    if (filters.workplaceType !== 'All') {
      list = list.filter((j) => j.workplaceType === filters.workplaceType);
    }

    if (filters.experienceLevel !== 'All') {
      list = list.filter((j) => j.experienceLevel === filters.experienceLevel);
    }

    if (filters.minMatch > 0) {
      list = list.filter((j) => j.matchScore >= filters.minMatch);
    }

    if (filters.sortBy === 'salary') {
      list.sort((a, b) => b.maxSalary - a.maxSalary);
    } else {
      list.sort((a, b) => b.matchScore - a.matchScore);
    }

    return list;
  }, [jobs, filters]);

  const handleResetFilters = () => {
    setFilters({
      searchQuery: '',
      role: 'All',
      location: 'All',
      workplaceType: 'All',
      experienceLevel: 'All',
      minMatch: 0,
      sortBy: 'match',
    });
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8">
      {/* Top Heading & Resume Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-800/80">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1">
            Jobs found for you
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            {resume ? (
              <>
                Opportunities matched to your profile as a{' '}
                <span className="text-indigo-300 font-medium">
                  {resume.parsedProfile.title}
                </span>
                .
              </>
            ) : (
              'Live genuine opportunities. Upload your resume to calculate personalized match scores.'
            )}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {resume && (
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
              <FileText className="w-3.5 h-3.5 text-indigo-400" />
              <span className="truncate max-w-[150px]">{resume.fileName}</span>
            </div>
          )}

          <button
            type="button"
            onClick={onReupload}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 hover:text-white transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3 h-3 text-slate-400" />
            <span>New Analysis</span>
          </button>
        </div>
      </div>

      {/* Filter and Search controls */}
      <JobFilters
        filters={filters}
        onChange={setFilters}
        onReset={handleResetFilters}
        totalResults={filteredJobs.length}
      />

      {/* Vertical Jobs List */}
      {filteredJobs.length > 0 ? (
        <div className="space-y-4">
          {filteredJobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              isSaved={savedJobIds.includes(job.id)}
              isApplied={appliedJobIds.includes(job.id)}
              isActionRequired={actionRequiredJobIds.includes(job.id)}
              onSelect={onSelectJob}
              onWhyMatches={onWhyMatches}
              onToggleSave={onToggleSave}
              onQuickApply={onQuickApply}
            />
          ))}
        </div>
      ) : (
        <div className="p-12 text-center rounded-2xl bg-[#080d1c] border border-slate-800 space-y-3">
          <p className="text-sm font-medium text-slate-300">
            No matching opportunities found.
          </p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your search criteria or resetting filters to view all recommended positions.
          </p>
          <button
            type="button"
            onClick={handleResetFilters}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      )}
    </div>
  );
};
