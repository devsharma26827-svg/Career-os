export type FontSize = 'normal' | 'large' | 'larger';
export type DisplayMode = 'simple' | 'advanced';

export interface User {
  id: number;
  email: string;
  full_name?: string | null;
  font_size: FontSize;
  display_mode: DisplayMode;
  reduced_motion?: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ExperienceItem {
  title?: string | null;
  company?: string | null;
  location?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  current: boolean;
  description?: string | null;
}

export interface EducationItem {
  degree?: string | null;
  institution?: string | null;
  field_of_study?: string | null;
  graduation_year?: string | null;
}

export interface ProjectItem {
  name?: string | null;
  description?: string | null;
  url?: string | null;
  technologies: string[];
}

export interface ParsedResumeProfile {
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  headline?: string | null;
  summary?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  skills: string[];
  experiences: ExperienceItem[];
  education: EducationItem[];
  projects: ProjectItem[];
  missing_fields: string[];
  confidence_scores?: Record<string, number>;
  uncertain_fields?: string[];
  field_evidence?: Record<string, string>;
  parser_source: string;
  raw_extracted_text?: string | null;
}

export interface ProfileResponse extends ParsedResumeProfile {
  id: number;
  user_id: number;
  is_confirmed: boolean;
  created_at: string;
  updated_at: string;
}

export interface Resume {
  id: number;
  user_id: number;
  original_filename: string;
  file_size: number;
  mime_type: string;
  is_active: boolean;
  uploaded_at: string;
}

export interface ResumeUploadResponse {
  message: string;
  resume: Resume;
  parsed_profile?: ParsedResumeProfile | null;
}

export interface JobMatchDetails {
  score: number;
  reasons: string[];
  matched_skills: string[];
  unknown_skills: string[];
  disclaimer: string;
}

export interface JobListing {
  id: number;
  source_id: string;
  source_name: string;
  title: string;
  company: string;
  location: string;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  is_remote: boolean;
  employment_type: string;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_text?: string | null;
  url: string;
  source_listing_url?: string | null;
  application_url?: string | null;
  company_website_url?: string | null;
  last_verified_at?: string | null;
  description: string;
  skills_required: string[];
  posted_at?: string | null;
  cached_at: string;
  is_active: boolean;
  match?: JobMatchDetails | null;
  is_saved: boolean;
  is_selected_for_apply: boolean;
  is_verified_link?: boolean;
  expansion_level?: string | null;
  location_explanation?: string | null;
}

export interface SourceHealth {
  source_name: string;
  display_name: string;
  status: string;
  job_count: number;
  message?: string | null;
  requires_key: boolean;
  config_help?: string | null;
}

export interface JobSearchResponse {
  jobs: JobListing[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  source_statuses: SourceHealth[];
  last_checked: string;
  expansion_notice?: string | null;
}

export interface JobSearchParams {
  query?: string;
  country?: string;
  states?: string[];
  city?: string;
  remote_only?: boolean;
  employment_type?: string;
  min_match_score?: number;
  sort_by?: 'relevance' | 'date' | 'title';
  page?: number;
  page_size?: number;
}

export type ApplicationStatus = 'draft' | 'reviewed' | 'ready_for_apply' | 'skipped';
export type VerificationStatus = 'VERIFIED' | 'INFERRED' | 'NOT_FOUND' | 'USER_VERIFIED';

export interface ApplicationWorkspace {
  id: number;
  job_id: number;
  job_title: string;
  job_company: string;
  job_location: string;
  job_url: string;
  job_source: string;
  job_description: string;
  status: ApplicationStatus;
  include_cover_letter: boolean;
  cover_letter_content?: string | null;
  cover_letter_tone: string;
  cover_letter_template: string;
  cover_letter_updated_at?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_role?: string | null;
  contact_source_url?: string | null;
  contact_verification_status: VerificationStatus;
  contact_discovered_at?: string | null;
  contact_notes?: string | null;
  email_subject?: string | null;
  email_body?: string | null;
  email_tone: string;
  email_updated_at?: string | null;
  is_duplicate_outreach: boolean;
  duplicate_warning?: string | null;
  disclaimer: string;
}

export interface SingleApplyRequest {
  job_id: number;
  submit_portal: boolean;
  send_email: boolean;
  screening_answers?: any;
  idempotency_key?: string | null;
  user_consent_granted: boolean;
}

export interface ApplyExecutionResult {
  job_id: number;
  title: string;
  company: string;
  application_status: string;
  application_confirmation_id?: string | null;
  application_message: string;
  manual_action_url?: string | null;
  manual_action_guide?: Record<string, any> | null;
  email_status: string;
  email_message?: string | null;
  error_message?: string | null;
}

export interface TrackedApplicationItem {
  id: number;
  job_id: number;
  job_title: string;
  company: string;
  location: string;
  source_name: string;
  job_url: string;
  destination_type: string;
  application_status: string;
  application_confirmation_id?: string | null;
  application_message?: string | null;
  has_cover_letter: boolean;
  cover_letter_preview?: string | null;
  has_email_draft: boolean;
  email_outreach_status: string;
  recruiter_email?: string | null;
  screening_confirmed: boolean;
  can_retry: boolean;
  applied_at?: string | null;
  updated_at?: string | null;
}

export interface TrackerResponse {
  total: number;
  submitted_count: number;
  requires_action_count: number;
  failed_count: number;
  items: TrackedApplicationItem[];
}
