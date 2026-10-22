import { ApplicationItem, ApplicationStatus, Job } from '../types/job';
import { api } from './api';
import { jobListingToJob, trackedAppToApplicationItem } from './dataAdapter';

let applicationsStore: ApplicationItem[] = [];

export const applicationService = {
  async getApplications(): Promise<ApplicationItem[]> {
    try {
      const items: ApplicationItem[] = [];

      // 1. Fetch saved jobs from backend
      try {
        const savedListings = await api.jobs.getSaved();
        if (savedListings && savedListings.length > 0) {
          savedListings.forEach((sl) => {
            const j = jobListingToJob(sl);
            items.push({
              id: `saved-${j.id}`,
              jobId: j.id,
              jobTitle: j.title,
              company: j.company,
              location: `${j.location} (${j.workplaceType})`,
              salary: j.salaryRange,
              matchScore: j.matchScore,
              status: 'saved',
              appliedDate: '—',
              lastUpdated: 'Recently',
              notes: 'Saved for review via CareerOS.',
              nextStep: 'Review requirements and submit',
              sourceName: j.sourceName,
              applicationUrl: j.sourceUrl,
            });
          });
        }
      } catch {
        // Continue to tracker
      }

      // 2. Fetch tracked applications from backend
      try {
        const tracker = await api.applications.getTracker();
        if (tracker && tracker.items && tracker.items.length > 0) {
          tracker.items.forEach((t) => {
            // Avoid duplicate with saved if tracker already has it
            const existingIdx = items.findIndex((i) => i.jobId === String(t.job_id));
            const trackedItem = trackedAppToApplicationItem(t);
            if (existingIdx >= 0) {
              items[existingIdx] = trackedItem;
            } else {
              items.push(trackedItem);
            }
          });
        }
      } catch {
        // Continue
      }

      applicationsStore = items;
      return items;
    } catch {
      // Return cached
    }

    return [...applicationsStore];
  },

  async applyToJob(job: Job, notes?: string): Promise<ApplicationItem> {
    const numericId = Number(job.id);
    let appStatus: ApplicationStatus = 'action_required';
    let manualUrl = job.applicationUrl || job.sourceUrl;
    let manualGuide: Record<string, any> | undefined = undefined;
    let appMsg = 'External portal application required.';
    let confirmationId: string | undefined = undefined;
    let isVerified = false;

    if (!isNaN(numericId) && numericId > 0) {
      try {
        const result = await api.applications.applySingle({
          job_id: numericId,
          submit_portal: true,
          send_email: false,
          user_consent_granted: true,
        });

        if (result) {
          if (result.application_status === 'submitted') {
            appStatus = 'applied';
            isVerified = true;
            confirmationId = result.application_confirmation_id || undefined;
            appMsg = result.application_message || 'Application submitted successfully.';
          } else if (result.application_status === 'requires_user_action') {
            appStatus = 'action_required';
            manualUrl = result.manual_action_url || manualUrl;
            manualGuide = result.manual_action_guide || undefined;
            appMsg = result.application_message || 'Employer requires application on their official portal.';
          } else if (result.application_status === 'failed') {
            appStatus = 'action_required';
            appMsg = result.error_message || result.application_message || 'Application requires manual completion.';
          }
        }
      } catch (err: any) {
        appStatus = 'action_required';
        appMsg = err?.message || 'External portal requires manual candidate submission.';
      }
    }

    const existingIndex = applicationsStore.findIndex((a) => a.jobId === job.id);
    const itemData: ApplicationItem = {
      id: existingIndex >= 0 ? applicationsStore[existingIndex].id : `app-${Date.now()}`,
      jobId: job.id,
      jobTitle: job.title,
      company: job.company,
      location: `${job.location} (${job.workplaceType})`,
      salary: job.salaryRange,
      matchScore: job.matchScore,
      status: appStatus,
      appliedDate: isVerified ? 'Just now' : 'In Progress',
      lastUpdated: 'Just now',
      notes: notes || appMsg,
      nextStep: appStatus === 'action_required'
        ? 'Complete application on official employer portal'
        : 'Awaiting recruiter response',
      sourceName: job.sourceName,
      applicationUrl: job.applicationUrl || job.sourceUrl,
      manualActionUrl: manualUrl,
      manualActionGuide: manualGuide,
      confirmationId,
      confirmationMessage: appMsg,
      isVerifiedSubmission: isVerified,
    };

    if (existingIndex >= 0) {
      applicationsStore[existingIndex] = itemData;
    } else {
      applicationsStore.unshift(itemData);
    }

    return itemData;
  },

  async markAsSubmitted(jobId: string | number, userNote?: string): Promise<ApplicationItem | undefined> {
    const numericId = Number(jobId);
    if (!isNaN(numericId) && numericId > 0) {
      try {
        await api.applications.markSubmitted(numericId);
      } catch {
        // Backend mark submitted
      }
    }

    const item = applicationsStore.find((a) => a.jobId === String(jobId));
    if (item) {
      item.status = 'applied';
      item.appliedDate = 'Just now';
      item.lastUpdated = 'Just now';
      item.isVerifiedSubmission = true;
      item.notes = userNote || 'Application verified and marked as submitted by candidate.';
      item.nextStep = 'Awaiting recruiter response';
    }
    return item;
  },

  async updateStatus(id: string, status: ApplicationStatus): Promise<ApplicationItem | undefined> {
    const item = applicationsStore.find((a) => a.id === id);
    if (item) {
      item.status = status;
      item.lastUpdated = 'Just now';

      const numericId = Number(item.jobId);
      if (!isNaN(numericId) && numericId > 0) {
        try {
          if (status === 'applied') {
            await api.applications.markSubmitted(numericId);
          } else {
            await api.applications.updateStatus(numericId, status);
          }
        } catch {
          // Local status preserved
        }
      }
    }
    return item;
  },

  async saveJob(job: Job): Promise<ApplicationItem> {
    const numericId = Number(job.id);
    if (!isNaN(numericId) && numericId > 0) {
      try {
        await api.jobs.toggleSave(numericId, 'Saved from CareerOS');
      } catch {
        // Fallback
      }
    }

    const existing = applicationsStore.find((a) => a.jobId === job.id);
    if (existing) {
      existing.status = 'saved';
      return existing;
    }

    const newSaved: ApplicationItem = {
      id: `app-${Date.now()}`,
      jobId: job.id,
      jobTitle: job.title,
      company: job.company,
      location: `${job.location} (${job.workplaceType})`,
      salary: job.salaryRange,
      matchScore: job.matchScore,
      status: 'saved',
      appliedDate: '—',
      lastUpdated: 'Just now',
      notes: 'Saved for review.',
      nextStep: 'Review requirements and apply',
      sourceName: job.sourceName,
      applicationUrl: job.applicationUrl || job.sourceUrl,
    };
    applicationsStore.unshift(newSaved);
    return newSaved;
  },

  async removeSaved(id: string): Promise<boolean> {
    const item = applicationsStore.find((a) => a.id === id);
    if (item) {
      const numericId = Number(item.jobId);
      if (!isNaN(numericId) && numericId > 0) {
        try {
          await api.jobs.unsave(numericId);
        } catch {
          // Ignored
        }
      }
    }

    applicationsStore = applicationsStore.filter((a) => a.id !== id);
    return true;
  },

  clearApplications(): void {
    applicationsStore = [];
  },
};
