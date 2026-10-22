import { Job, JobFilterState } from '../types/job';
import { api, getAuthToken } from './api';
import { jobListingToJob } from './dataAdapter';

let cachedJobs: Job[] = [];

export const jobService = {
  async getJobs(filters?: Partial<JobFilterState>): Promise<Job[]> {
    if (!getAuthToken()) {
      return [];
    }

    try {
      const backendResponse = await api.jobs.search({
        query: filters?.searchQuery?.trim() || undefined,
        remote_only: filters?.workplaceType === 'Remote' ? true : undefined,
        min_match_score: filters?.minMatch && filters.minMatch > 0 ? filters.minMatch : undefined,
        sort_by: filters?.sortBy === 'salary' ? 'relevance' : (filters?.sortBy === 'match' ? 'relevance' : 'date'),
        page: 1,
        page_size: 50,
      });

      if (backendResponse && backendResponse.jobs) {
        let list = backendResponse.jobs.map(jobListingToJob);

        // Apply remaining in-memory UI filters
        if (filters?.workplaceType && filters.workplaceType !== 'All') {
          list = list.filter((j) => j.workplaceType === filters.workplaceType);
        }

        if (filters?.experienceLevel && filters.experienceLevel !== 'All') {
          list = list.filter((j) => j.experienceLevel === filters.experienceLevel);
        }

        const minMatch = filters?.minMatch;
        if (minMatch && minMatch > 0) {
          list = list.filter((j) => j.matchScore >= minMatch);
        }

        if (filters?.sortBy === 'salary') {
          list.sort((a, b) => b.maxSalary - a.maxSalary);
        } else if (filters?.sortBy === 'match') {
          list.sort((a, b) => b.matchScore - a.matchScore);
        }

        cachedJobs = list;
        return list;
      }
    } catch {
      // Return cached jobs or empty array if offline
    }

    return cachedJobs;
  },

  async getJobById(id: string): Promise<Job | undefined> {
    return cachedJobs.find((j) => j.id === id);
  },

  clearCache(): void {
    cachedJobs = [];
  },
};
