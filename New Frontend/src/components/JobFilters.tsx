import React from 'react';
import { JobFilterState } from '../types/job';
import { Search, SlidersHorizontal, RotateCcw } from 'lucide-react';

interface JobFiltersProps {
  filters: JobFilterState;
  onChange: (newFilters: JobFilterState) => void;
  onReset: () => void;
  totalResults: number;
}

export const JobFilters: React.FC<JobFiltersProps> = ({
  filters,
  onChange,
  onReset,
  totalResults,
}) => {
  return (
    <div className="w-full space-y-3 mb-6">
      {/* Search Input Bar */}
      <div className="relative flex items-center">
        <Search className="absolute left-3.5 w-4 h-4 text-slate-500 pointer-events-none" />
        <input
          type="text"
          value={filters.searchQuery}
          onChange={(e) => onChange({ ...filters, searchQuery: e.target.value })}
          placeholder="Search by title, skills (e.g. PyTorch, RAG), company, or location..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#090d1c] border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/50 transition-all"
        />
        {filters.searchQuery && (
          <button
            onClick={() => onChange({ ...filters, searchQuery: '' })}
            className="absolute right-3 text-xs text-slate-500 hover:text-slate-300"
          >
            Clear
          </button>
        )}
      </div>

      {/* Filter Row: Workplace, Experience, Min Match, Sort By */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Workplace Type */}
          <div className="flex items-center gap-1 bg-[#090d1c] p-1 rounded-lg border border-slate-800">
            {['All', 'Remote', 'Hybrid', 'On-site'].map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => onChange({ ...filters, workplaceType: type })}
                className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                  filters.workplaceType === type
                    ? 'bg-indigo-600/90 text-white font-medium shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Experience Level */}
          <select
            value={filters.experienceLevel}
            onChange={(e) => onChange({ ...filters, experienceLevel: e.target.value })}
            className="px-2.5 py-1.5 rounded-lg bg-[#090d1c] border border-slate-800 text-slate-300 focus:outline-none focus:border-indigo-500/50 cursor-pointer"
          >
            <option value="All">All Experience</option>
            <option value="Entry">Entry Level / Intern</option>
            <option value="Mid">Mid Level</option>
            <option value="Senior">Senior</option>
            <option value="Staff">Staff / Lead</option>
          </select>

          {/* Min Match Score */}
          <select
            value={filters.minMatch}
            onChange={(e) => onChange({ ...filters, minMatch: Number(e.target.value) })}
            className="px-2.5 py-1.5 rounded-lg bg-[#090d1c] border border-slate-800 text-slate-300 focus:outline-none focus:border-indigo-500/50 cursor-pointer"
          >
            <option value={0}>Any Match %</option>
            <option value={85}>85%+ Match</option>
            <option value={90}>90%+ Match</option>
          </select>

          {/* Reset Filters */}
          {(filters.searchQuery ||
            filters.workplaceType !== 'All' ||
            filters.experienceLevel !== 'All' ||
            filters.minMatch > 0) && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 px-2 py-1 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          )}
        </div>

        {/* Sort & Count */}
        <div className="flex items-center gap-3 text-slate-400">
          <span className="font-mono text-slate-400">
            {totalResults} {totalResults === 1 ? 'position' : 'positions'}
          </span>
          <span aria-hidden="true" className="text-slate-700">|</span>
          <div className="flex items-center gap-1.5">
            <SlidersHorizontal className="w-3 h-3 text-slate-500" />
            <select
              value={filters.sortBy}
              onChange={(e) => onChange({ ...filters, sortBy: e.target.value as any })}
              className="bg-transparent border-0 text-slate-300 focus:outline-none cursor-pointer pr-1"
            >
              <option value="match" className="bg-[#090d1c]">Highest Match</option>
              <option value="salary" className="bg-[#090d1c]">Top Salary</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};
