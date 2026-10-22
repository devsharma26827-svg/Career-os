import { UserResume } from '../types/job';
import { api } from './api';
import { profileResponseToUserResume } from './dataAdapter';

let storedResume: UserResume | null = null;

export const resumeService = {
  async uploadResume(file: File): Promise<UserResume> {
    const uploadResp = await api.resume.upload(file);
    if (!uploadResp || !uploadResp.resume) {
      throw new Error('Upload failed. Please ensure file is a valid PDF or DOCX.');
    }

    let profile = uploadResp.parsed_profile;
    if (!profile) {
      try {
        profile = await api.profile.get();
      } catch {
        // Fallback
      }
    }

    if (!profile) {
      throw new Error('Failed to parse structured resume profile.');
    }

    const userResume = profileResponseToUserResume(profile as any, uploadResp.resume);
    storedResume = userResume;
    return userResume;
  },

  async getParsedResume(): Promise<UserResume | null> {
    try {
      const profile = await api.profile.get();
      const resume = await api.resume.getCurrent();
      if (profile && (profile.full_name || profile.headline || (profile.skills && profile.skills.length > 0))) {
        const loaded = profileResponseToUserResume(profile, resume);
        storedResume = loaded;
        return loaded;
      }
    } catch {
      // User may be unauthenticated or has not yet uploaded a resume
    }

    return storedResume;
  },

  clearResume(): void {
    storedResume = null;
  },
};
