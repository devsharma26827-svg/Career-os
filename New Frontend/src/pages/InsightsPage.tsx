import React, { useMemo } from 'react';
import { Job, ApplicationItem } from '../types/job';
import { TrendingUp, BarChart3, Users, DollarSign, Award, ShieldCheck, Clock } from 'lucide-react';

interface InsightsPageProps {
  jobs: Job[];
  applications: ApplicationItem[];
}

export const InsightsPage: React.FC<InsightsPageProps> = ({
  jobs,
  applications,
}) => {
  const savedCount = applications.filter((a) => a.status === 'saved').length;
  const actionCount = applications.filter((a) => a.status === 'action_required').length;
  const appliedCount = applications.filter((a) => a.status === 'applied').length;
  const interviewCount = applications.filter((a) => a.status === 'interview').length;

  const calibratedJobs = useMemo(() => jobs.filter((j) => j.matchScore > 0), [jobs]);
  const avgMatch = useMemo(() => {
    if (calibratedJobs.length === 0) return 0;
    return Math.round(calibratedJobs.reduce((acc, j) => acc + j.matchScore, 0) / calibratedJobs.length);
  }, [calibratedJobs]);

  const remotePct = useMemo(() => {
    if (jobs.length === 0) return 0;
    const remoteCount = jobs.filter((j) => j.workplaceType === 'Remote').length;
    return Math.round((remoteCount / jobs.length) * 100);
  }, [jobs]);

  const skillDemands = useMemo(() => {
    const counts: Record<string, number> = {};
    jobs.forEach((j) => {
      j.skills.forEach((s) => {
        counts[s] = (counts[s] || 0) + 1;
      });
    });

    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([skill, count]) => {
        const pct = Math.round((count / (jobs.length || 1)) * 100);
        return {
          skill,
          frequency: `${pct}% (${count} ${count === 1 ? 'role' : 'roles'})`,
          percentage: pct,
          status: pct >= 40 ? 'High Demand' : (pct >= 20 ? 'Core Requirement' : 'Preferred Skill'),
        };
      });
  }, [jobs]);

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1">
            Career & Market Insights
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Real-time pipeline metrics and skill demand telemetry computed dynamically from verified listings.
          </p>
        </div>
      </div>

      {/* Primary Pipeline Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80">
          <span className="text-xs text-slate-400 font-medium block mb-1">Total Discovered</span>
          <span className="text-2xl font-bold text-white tabular-nums">{jobs.length}</span>
          <span className="text-[11px] text-indigo-400 block mt-1">Live active listings</span>
        </div>

        <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80">
          <span className="text-xs text-slate-400 font-medium block mb-1">Saved Roles</span>
          <span className="text-2xl font-bold text-white tabular-nums">{savedCount}</span>
          <span className="text-[11px] text-slate-500 block mt-1">Under candidate review</span>
        </div>

        <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80">
          <span className="text-xs text-slate-400 font-medium block mb-1">Action Needed</span>
          <span className="text-2xl font-bold text-amber-400 tabular-nums">{actionCount}</span>
          <span className="text-[11px] text-amber-500 block mt-1">Portal submission needed</span>
        </div>

        <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80">
          <span className="text-xs text-slate-400 font-medium block mb-1">Active Pipeline</span>
          <span className="text-2xl font-bold text-emerald-400 tabular-nums">{appliedCount + interviewCount}</span>
          <span className="text-[11px] text-emerald-500 block mt-1">
            {interviewCount > 0 ? `${interviewCount} in interview stage` : 'Applications submitted'}
          </span>
        </div>
      </div>

      {/* Dynamic Market Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-start justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Average Profile Compatibility</span>
            <span className="text-xs font-mono text-cyan-400">
              {calibratedJobs.length > 0 ? `${calibratedJobs.length} scored` : 'Uncalibrated'}
            </span>
          </div>
          <div className="text-xl font-bold text-white mb-1 tabular-nums">
            {avgMatch > 0 ? `${avgMatch}% Match` : 'Awaiting Resume'}
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            {avgMatch > 0
              ? 'Computed from verified skill overlap, seniority alignment, and role domain compatibility.'
              : 'Upload your resume to calculate personalized alignment scores across discovered jobs.'}
          </p>
        </div>

        <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-start justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Remote Distribution</span>
            <span className="text-xs font-mono text-indigo-400">{remotePct}% Remote</span>
          </div>
          <div className="text-xl font-bold text-white mb-1 tabular-nums">
            {jobs.filter((j) => j.workplaceType === 'Remote').length} of {jobs.length} roles
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Distribution of location-flexible and remote-friendly opportunities in your active search feed.
          </p>
        </div>
      </div>

      {/* In-Demand Skills Table */}
      <div className="p-6 rounded-xl bg-[#080d1a] border border-slate-800/80">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800/60">
          <div>
            <h3 className="text-sm font-semibold text-white tracking-tight">
              Skill Frequency Across Live Opportunities
            </h3>
            <p className="text-xs text-slate-400">
              Aggregated directly from technical requirements in current job listings.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">Live Telemetry</span>
        </div>

        {skillDemands.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 font-mono">
                  <th className="py-2.5 font-medium">Domain Skill</th>
                  <th className="py-2.5 font-medium">Listing Frequency</th>
                  <th className="py-2.5 font-medium">Market Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {skillDemands.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 font-medium text-white font-mono">{item.skill}</td>
                    <td className="py-3 text-slate-300 font-mono tabular-nums">{item.frequency}</td>
                    <td className="py-3">
                      <span className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                        item.percentage >= 40
                          ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-300'
                          : 'bg-indigo-950/60 border-indigo-500/20 text-indigo-300'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500">
            No skill telemetry available yet. Discover jobs in the search tab to view live demand patterns.
          </div>
        )}
      </div>
    </div>
  );
};
