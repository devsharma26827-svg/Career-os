import type {
  AuthResponse,
  FontSize,
  DisplayMode,
  ProfileResponse,
  Resume,
  ResumeUploadResponse,
  User,
  JobListing,
  JobSearchParams,
  JobSearchResponse,
  ApplicationWorkspace,
  SingleApplyRequest,
  ApplyExecutionResult,
  TrackedApplicationItem,
  TrackerResponse,
} from '../types/backend';

const CONFIGURED_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
}

function isNetworkError(err: any): boolean {
  if (!err) return false;
  const msg = String(err.message || '').toLowerCase();
  return (
    err.name === 'TypeError' ||
    msg.includes('failed to fetch') ||
    msg.includes('networkerror') ||
    msg.includes('network error') ||
    msg.includes('load failed') ||
    msg.includes('connection refused') ||
    msg.includes('failed to load')
  );
}

function formatDetailMessage(detail: any): string {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const formatted = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object') {
          const loc = Array.isArray(item.loc) ? item.loc.filter((l: any) => l !== 'body').join(' ') : '';
          const msg = item.msg || item.message || 'Invalid value';
          return loc ? `${loc}: ${msg}` : msg;
        }
        return 'Validation error';
      })
      .filter(Boolean);
    return formatted.join('. ') || 'Validation error';
  }
  if (typeof detail === 'object') {
    return detail.message || detail.msg || JSON.stringify(detail);
  }
  return String(detail);
}

function getStatusFallbackMessage(status: number): string {
  switch (status) {
    case 400:
      return 'Invalid request. Please check your information and try again.';
    case 401:
      return 'Incorrect email or password, or session expired.';
    case 403:
      return 'Access denied. You do not have permission to perform this action.';
    case 404:
      return 'The requested resource could not be found.';
    case 409:
      return 'A conflict occurred. This record already exists.';
    case 422:
      return 'Validation error. Please verify the submitted information.';
    case 429:
      return 'Too many requests. Please wait a moment and try again.';
    case 500:
      return 'The backend server encountered an error. Please try again shortly.';
    case 502:
    case 503:
    case 504:
      return 'The backend server is temporarily unavailable. Please verify it is running on http://127.0.0.1:8000.';
    default:
      return 'An unexpected error occurred. Please try again.';
  }
}

function getCandidateUrls(endpoint: string): string[] {
  const base = CONFIGURED_API_URL.replace(/\/+$/, '');
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const candidates: string[] = [`${base}${cleanEndpoint}`];

  if (base.startsWith('http')) {
    candidates.push(`/api/v1${cleanEndpoint}`);
  } else {
    candidates.push(`http://127.0.0.1:8000/api/v1${cleanEndpoint}`);
  }

  return Array.from(new Set(candidates));
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const candidateUrls = getCandidateUrls(endpoint);
  let lastNetworkError: any = null;

  for (let i = 0; i < candidateUrls.length; i++) {
    const targetUrl = candidateUrls[i];
    try {
      const response = await fetch(targetUrl, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorMessage = '';
        let errorData = null;

        try {
          errorData = await response.json();
          if (errorData && errorData.detail) {
            errorMessage = formatDetailMessage(errorData.detail);
          } else if (errorData && errorData.message) {
            errorMessage = String(errorData.message);
          }
        } catch {
          errorMessage = response.statusText;
        }

        if (!errorMessage) {
          errorMessage = getStatusFallbackMessage(response.status);
        }

        if (response.status === 401) {
          setAuthToken(null);
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('auth:expired', { detail: { message: errorMessage } }));
          }
        }

        throw new ApiError(errorMessage, response.status, errorData);
      }

      if (response.status === 204) {
        return {} as T;
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }

      return (await response.text()) as unknown as T;
    } catch (err: any) {
      if (err instanceof ApiError) {
        throw err;
      }

      lastNetworkError = err;
      if (i < candidateUrls.length - 1) {
        continue;
      }
    }
  }

  if (isNetworkError(lastNetworkError)) {
    throw new ApiError(
      'Unable to connect to the backend server. Please verify it is running on http://127.0.0.1:8000.',
      0,
      { isNetworkError: true, original: lastNetworkError?.message }
    );
  }

  throw new ApiError(
    lastNetworkError?.message || 'A network error occurred while reaching the server.',
    0,
    { isNetworkError: true, original: lastNetworkError }
  );
}

export const api = {
  auth: {
    signup: (email: string, password: string, fullName?: string) =>
      request<AuthResponse>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: fullName }),
      }),

    login: (email: string, password: string) =>
      request<AuthResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),

    me: () => request<User>('/auth/me'),

    updatePreferences: (preferences: {
      font_size?: FontSize;
      display_mode?: DisplayMode;
      reduced_motion?: boolean;
    }) =>
      request<User>('/auth/preferences', {
        method: 'PUT',
        body: JSON.stringify(preferences),
      }),
  },

  resume: {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return request<ResumeUploadResponse>('/resume/upload', {
        method: 'POST',
        body: formData,
      });
    },

    getCurrent: () => request<Resume | null>('/resume'),
  },

  profile: {
    get: () => request<ProfileResponse>('/profile'),

    update: (profileData: any) =>
      request<ProfileResponse>('/profile', {
        method: 'PUT',
        body: JSON.stringify(profileData),
      }),

    reparse: () =>
      request<ProfileResponse>('/profile/reparse', {
        method: 'POST',
      }),
  },

  jobs: {
    search: (params: JobSearchParams) => {
      const queryParams = new URLSearchParams();
      if (params.query) queryParams.set('query', params.query);
      if (params.country) queryParams.set('country', params.country);
      if (params.states && params.states.length > 0) {
        params.states.forEach((st) => queryParams.append('states', st));
      }
      if (params.city) queryParams.set('city', params.city);
      if (params.remote_only) queryParams.set('remote_only', 'true');
      if (params.employment_type && params.employment_type !== 'all') {
        queryParams.set('employment_type', params.employment_type);
      }
      if (params.min_match_score !== undefined && params.min_match_score !== null) {
        queryParams.set('min_match_score', params.min_match_score.toString());
      }
      if (params.sort_by) queryParams.set('sort_by', params.sort_by);
      if (params.page) queryParams.set('page', params.page.toString());
      if (params.page_size) queryParams.set('page_size', params.page_size.toString());

      return request<JobSearchResponse>(`/jobs/search?${queryParams.toString()}`);
    },

    toggleSave: (jobId: number, notes?: string) =>
      request<{ message: string; is_saved: boolean }>('/jobs/save', {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId, notes }),
      }),

    unsave: (jobId: number) =>
      request<{ message: string }>(`/jobs/save/${jobId}`, {
        method: 'DELETE',
      }),

    getSaved: () => request<JobListing[]>('/jobs/saved'),
  },

  applications: {
    getTracker: () => request<TrackerResponse>('/applications/tracker'),

    getWorkspace: (jobId: number) => request<ApplicationWorkspace>(`/applications/${jobId}`),

    generateCoverLetter: (jobId: number, data?: { tone?: string; template_style?: string }) =>
      request<ApplicationWorkspace>(`/applications/${jobId}/cover-letter/generate`, {
        method: 'POST',
        body: JSON.stringify(data || { tone: 'professional', template_style: 'modern' }),
      }),

    applySingle: (data: SingleApplyRequest) =>
      request<ApplyExecutionResult>('/applications/apply/single', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    updateStatus: (jobId: number, status: string) =>
      request<ApplicationWorkspace>(`/applications/${jobId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      }),

    markSubmitted: (jobId: number, confirmationNote?: string) =>
      request<{ message: string; application_status: string }>(
        `/applications/${jobId}/mark-submitted`,
        {
          method: 'POST',
          body: JSON.stringify({ confirmation_note: confirmationNote }),
        }
      ),
  },
};
