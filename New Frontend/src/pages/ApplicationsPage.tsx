import React, { useState } from 'react';
import { ApplicationItem, ApplicationStatus } from '../types/job';
import { Building2, Calendar, ChevronRight, CheckCircle2, ExternalLink, ShieldCheck, Check } from 'lucide-react';

interface ApplicationsPageProps {
  applications: ApplicationItem[];
  onUpdateStatus: (id: string, status: ApplicationStatus) => void;
  onOpenJob: (jobId: string) => void;
  onMarkSubmitted?: (jobId: string) => void;
}

const COLUMNS: Array<{ id: ApplicationStatus; label: string; countColor: string }> = [
  { id: 'saved', label: 'Saved', countColor: 'text-slate-400' },
  { id: 'action_required', label: 'Action Needed', countColor: 'text-amber-400' },
  { id: 'applied', label: 'Applied', countColor: 'text-indigo-400' },
  { id: 'screening', label: 'Screening', countColor: 'text-cyan-400' },
  { id: 'interview', label: 'Interview', countColor: 'text-purple-400' },
  { id: 'offer', label: 'Offer', countColor: 'text-emerald-400' },
  { id: 'rejected', label: 'Archived', countColor: 'text-rose-400' },
];

export const ApplicationsPage: React.FC<ApplicationsPageProps> = ({
  applications,
  onUpdateStatus,
  onOpenJob,
  onMarkSubmitted,
}) => {
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('all');

  const filteredApps = selectedStatusFilter === 'all'
    ? applications
    : applications.filter((app) => app.status === selectedStatusFilter);

  const getNextStatus = (current: ApplicationStatus): ApplicationStatus => {
    switch (current) {
      case 'saved': return 'action_required';
      case 'action_required': return 'applied';
      case 'applied': return 'screening';
      case 'screening': return 'interview';
      case 'interview': return 'offer';
      default: return 'interview';
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1">
            Application Pipeline
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Track active interview cycles, recruiter screenings, and saved positions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">
            {applications.length} total active records
          </span>
        </div>
      </div>

      {/* Kanban Board / Pipeline Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => {
          const colApps = applications.filter((app) => app.status === col.id);

          return (
            <div
              key={col.id}
              className="flex flex-col rounded-xl bg-[#080d1a] border border-slate-800/80 p-3 min-w-[200px]"
            >
              {/* Column Header */}
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800/60">
                <span className="text-xs font-semibold text-slate-200">
                  {col.label}
                </span>
                <span className={`text-xs font-mono font-semibold ${col.countColor}`}>
                  {colApps.length}
                </span>
              </div>

              {/* Column Cards */}
              <div className="space-y-3 flex-1">
                {colApps.length > 0 ? (
                  colApps.map((app) => (
                    <div
                      key={app.id}
                      className="p-3 rounded-lg bg-[#0b1022] hover:bg-[#0f162e] border border-slate-800 hover:border-indigo-500/40 transition-all text-xs flex flex-col justify-between shadow-sm"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <button
                            type="button"
                            onClick={() => onOpenJob(app.jobId)}
                            className="font-medium text-white hover:text-indigo-200 line-clamp-1 text-left cursor-pointer"
                          >
                            {app.jobTitle}
                          </button>
                          {app.matchScore > 0 ? (
                            <span className="shrink-0 text-[10px] font-mono text-cyan-300 font-semibold">
                              {app.matchScore}%
                            </span>
                          ) : (
                            app.isVerifiedSubmission && (
                              <span className="shrink-0 text-[10px] font-mono text-emerald-400 flex items-center gap-0.5" title="Verified submission">
                                <ShieldCheck className="w-3 h-3" />
                              </span>
                            )
                          )}
                        </div>

                        <p className="text-[11px] text-slate-400 flex items-center justify-between gap-1 mb-2">
                          <span className="flex items-center gap-1">
                            <Building2 className="w-3 h-3 text-slate-500" />
                            <span>{app.company}</span>
                          </span>
                          {app.sourceName && (
                            <span className="text-[10px] font-mono text-slate-500 capitalize">
                              {app.sourceName}
                            </span>
                          )}
                        </p>

                        {app.nextStep && (
                          <div className={`mb-2 p-1.5 rounded border text-[10px] font-mono truncate ${
                            app.status === 'action_required'
                              ? 'bg-amber-950/40 border-amber-500/30 text-amber-300'
                              : 'bg-slate-900/80 border-slate-800 text-indigo-300'
                          }`}>
                            {app.nextStep}
                          </div>
                        )}

                        {/* Action buttons if action required */}
                        {app.status === 'action_required' && (
                          <div className="mb-2 flex flex-col gap-1.5">
                            {(app.manualActionUrl || app.applicationUrl) && (
                              <a
                                href={app.manualActionUrl || app.applicationUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center justify-center gap-1 py-1 px-2 rounded bg-indigo-600/80 hover:bg-indigo-600 text-white text-[10px] font-medium transition-colors"
                              >
                                <span>Open Official Form</span>
                                <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                            <button
                              type="button"
                              onClick={() => {
                                if (onMarkSubmitted) {
                                  onMarkSubmitted(app.jobId);
                                } else {
                                  onUpdateStatus(app.id, 'applied');
                                }
                              }}
                              className="inline-flex items-center justify-center gap-1 py-1 px-2 rounded bg-emerald-950/60 hover:bg-emerald-900/80 border border-emerald-500/40 text-emerald-300 text-[10px] font-medium transition-colors cursor-pointer"
                            >
                              <Check className="w-2.5 h-2.5" />
                              <span>Confirm Submitted</span>
                            </button>
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-2.5 h-2.5" />
                          <span>{app.lastUpdated}</span>
                        </span>

                        {col.id !== 'offer' && col.id !== 'rejected' && (
                          <button
                            type="button"
                            onClick={() => onUpdateStatus(app.id, getNextStatus(app.status))}
                            className="text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5 cursor-pointer"
                            title={`Move to ${getNextStatus(app.status)}`}
                          >
                            <span>Advance</span>
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-24 rounded-lg border border-dashed border-slate-800/60 flex items-center justify-center text-slate-600 text-[11px]">
                    No jobs
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
