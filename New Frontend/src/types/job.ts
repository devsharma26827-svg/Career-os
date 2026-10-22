export type AppState =
  | 'idle'
  | 'uploading'
  | 'analyzing'
  | 'searching'
  | 'portal'
  | 'results'
  | 'error';

export type ActiveTab =
  | 'search'
  | 'applications'
  | 'saved'
  | 'resume'
  | 'interview'
  | 'insights';

export interface SkillMatch {
  name: string;
  matched: boolean;
  category: 'core' | 'preferred' | 'bonus';
}

export interface MatchBreakdown {
  score: number;
  strongMatches: string[];
  skillGaps: string[];
  experienceAlignment: 'Exceptional' | 'Strong' | 'Moderate' | 'Developing';
  summary: string;
  strengths: string[];
  recommendedAction: string;
}

export interface Job {
  id: string;
  title: string;
  company: string;
  logo: string;
  location: string;
  workplaceType: 'Remote' | 'Hybrid' | 'On-site';
  employmentType: 'Full-time' | 'Contract' | 'Internship';
  experienceLevel: 'Entry' | 'Mid' | 'Senior' | 'Lead' | 'Staff';
  salaryRange: string;
  minSalary: number;
  maxSalary: number;
  postedDate: string;
  matchScore: number;
  skills: string[];
  description: string;
  responsibilities: string[];
  requirements: string[];
  benefits: string[];
  breakdown: MatchBreakdown;
  featured?: boolean;
  sourceName?: string;
  sourceUrl?: string;
  applicationUrl?: string;
  companyWebsiteUrl?: string;
  lastVerifiedAt?: string;
  sourceId?: string;
  retrievedAt?: string;
  isVerifiedLink?: boolean;
}

export type ApplicationStatus =
  | 'saved'
  | 'action_required'
  | 'applied'
  | 'screening'
  | 'interview'
  | 'offer'
  | 'rejected';

export interface ApplicationItem {
  id: string;
  jobId: string;
  jobTitle: string;
  company: string;
  location: string;
  salary: string;
  matchScore: number;
  status: ApplicationStatus;
  appliedDate: string;
  lastUpdated: string;
  notes?: string;
  nextStep?: string;
  sourceName?: string;
  destinationType?: string;
  applicationUrl?: string;
  manualActionUrl?: string;
  manualActionGuide?: Record<string, any>;
  confirmationId?: string;
  confirmationMessage?: string;
  isVerifiedSubmission?: boolean;
}

export interface UserResume {
  fileName: string;
  fileSize: string;
  uploadedAt: string;
  parsedProfile: {
    fullName: string;
    title: string;
    summary: string;
    yearsOfExperience: number;
    skills: string[];
    coreDomains: string[];
    experience: {
      role: string;
      company: string;
      period: string;
      highlights: string[];
    }[];
    education: {
      degree: string;
      institution: string;
      year: string;
    }[];
    targetRoles: string[];
    preferredLocations: string[];
  };
}

export interface JobFilterState {
  searchQuery: string;
  role: string;
  location: string;
  workplaceType: string;
  experienceLevel: string;
  minMatch: number;
  sortBy: 'match' | 'date' | 'salary';
}
