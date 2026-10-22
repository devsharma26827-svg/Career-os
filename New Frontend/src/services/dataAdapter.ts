import { Job, UserResume, ApplicationItem, ApplicationStatus } from '../types/job';
import { JobListing, ProfileResponse, Resume, TrackedApplicationItem } from '../types/backend';

export function jobListingToJob(listing: JobListing): Job {
  const hasMatch = listing.match !== null && listing.match !== undefined;
  const matchScore = hasMatch ? Math.round(listing.match!.score) : 0;
  const skills = Array.isArray(listing.skills_required) ? listing.skills_required : [];

  const matchedSkills = listing.match?.matched_skills && listing.match.matched_skills.length > 0
    ? listing.match.matched_skills
    : [];

  const skillGaps = listing.match?.unknown_skills && listing.match.unknown_skills.length > 0
    ? listing.match.unknown_skills
    : [];

  const workplaceType: 'Remote' | 'Hybrid' | 'On-site' = listing.is_remote
    ? 'Remote'
    : (listing.location.toLowerCase().includes('hybrid') ? 'Hybrid' : 'On-site');

  const empTypeLower = (listing.employment_type || '').toLowerCase();
  const employmentType: 'Full-time' | 'Contract' | 'Internship' = empTypeLower.includes('contract')
    ? 'Contract'
    : (empTypeLower.includes('intern') ? 'Internship' : 'Full-time');

  const titleLower = listing.title.toLowerCase();
  const experienceLevel: 'Entry' | 'Mid' | 'Senior' | 'Lead' | 'Staff' = titleLower.includes('staff')
    ? 'Staff'
    : titleLower.includes('lead')
    ? 'Lead'
    : (titleLower.includes('senior') || titleLower.includes('sr.'))
    ? 'Senior'
    : (titleLower.includes('intern') || titleLower.includes('junior'))
    ? 'Entry'
    : 'Mid';

  const minSalary = listing.salary_min ? Math.round(listing.salary_min) : 0;
  const maxSalary = listing.salary_max ? Math.round(listing.salary_max) : 0;
  const salaryRange = listing.salary_text
    ? listing.salary_text
    : (minSalary > 0 && maxSalary > 0
      ? `$${Math.round(minSalary / 1000)}k – $${Math.round(maxSalary / 1000)}k`
      : (minSalary > 0 ? `From $${Math.round(minSalary / 1000)}k` : 'Competitive / Unspecified'));

  const reasons = listing.match?.reasons && listing.match.reasons.length > 0
    ? listing.match.reasons
    : (hasMatch
      ? [`Evaluated against candidate profile for ${listing.title}.`]
      : ['Upload your resume to see personalized skill and title matching.']);

  const experienceAlignment = matchScore >= 85
    ? 'Exceptional'
    : matchScore >= 70
    ? 'Strong'
    : matchScore >= 50
    ? 'Moderate'
    : 'Developing';

  return {
    id: String(listing.id),
    title: listing.title,
    company: listing.company,
    logo: listing.company.slice(0, 2).toUpperCase(),
    location: listing.location || (listing.is_remote ? 'Remote' : 'Location Not Specified'),
    workplaceType,
    employmentType,
    experienceLevel,
    salaryRange,
    minSalary,
    maxSalary,
    postedDate: listing.posted_at
      ? new Date(listing.posted_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      : 'Active',
    matchScore,
    skills,
    description: listing.description || `Job opportunity at ${listing.company} for ${listing.title}.`,
    responsibilities: [
      `Design, implement, and maintain solutions for ${listing.title}.`,
      `Collaborate across engineering and product teams to deliver high-quality releases.`,
      `Continuously improve architectural resilience and performance.`,
    ],
    requirements: skills.length > 0
      ? skills.map((s) => `Demonstrated hands-on experience with ${s}.`)
      : ['Experience with core domain requirements specified in description.'],
    benefits: [
      'Comprehensive Health, Dental & Vision Insurance',
      'Flexible Remote / Hybrid Schedule',
      'Competitive Equity Compensation',
      'Generous Learning & Professional Development Budget',
    ],
    breakdown: {
      score: matchScore,
      strongMatches: matchedSkills,
      skillGaps: skillGaps,
      experienceAlignment,
      summary: reasons.join(' '),
      strengths: reasons,
      recommendedAction: matchScore >= 70
        ? 'Priority candidate for application. Highlight relevant skills.'
        : (matchScore > 0
          ? 'Review technical requirements and consider tailored cover letter.'
          : 'Upload your verified resume in Step 1 to calculate personalized match score.'),
    },
    featured: matchScore >= 85,
    sourceName: listing.source_name,
    sourceUrl: listing.source_listing_url || listing.url,
    applicationUrl: listing.application_url || (listing.source_name === 'jobicy' ? undefined : listing.url),
    companyWebsiteUrl: listing.company_website_url || undefined,
    lastVerifiedAt: listing.last_verified_at || listing.cached_at,
    sourceId: listing.source_id,
    retrievedAt: listing.cached_at,
    isVerifiedLink: listing.is_verified_link,
  };
}

export function profileResponseToUserResume(profile: ProfileResponse, resume?: Resume | null): UserResume {
  const experiences = profile.experiences && profile.experiences.length > 0
    ? profile.experiences.map((e) => ({
        role: e.title || 'Software Engineer',
        company: e.company || 'Company',
        period: `${e.start_date || ''} – ${e.end_date || (e.current ? 'Present' : '')}`.trim() || 'Experience',
        highlights: e.description ? [e.description] : [],
      }))
    : [];

  const education = profile.education && profile.education.length > 0
    ? profile.education.map((ed) => ({
        degree: ed.degree || 'Degree',
        institution: ed.institution || 'Institution',
        year: ed.graduation_year || '',
      }))
    : [];

  const skills = profile.skills && profile.skills.length > 0 ? profile.skills : [];
  const coreDomains = skills.slice(0, 4);

  return {
    fileName: resume?.original_filename || 'Uploaded_Resume.pdf',
    fileSize: resume?.file_size ? `${(resume.file_size / (1024 * 1024)).toFixed(1)} MB` : '1.0 MB',
    uploadedAt: resume?.uploaded_at
      ? new Date(resume.uploaded_at).toLocaleDateString()
      : 'Active Index',
    parsedProfile: {
      fullName: profile.full_name || 'Verified Candidate',
      title: profile.headline || 'Software Engineer',
      summary: profile.summary || '',
      yearsOfExperience: Math.max(1, experiences.length * 2),
      skills,
      coreDomains,
      experience: experiences,
      education: education,
      targetRoles: [profile.headline || 'Software Engineer'].filter(Boolean),
      preferredLocations: [profile.location || 'Remote'].filter(Boolean),
    },
  };
}

export function trackedAppToApplicationItem(tracked: TrackedApplicationItem): ApplicationItem {
  let status: ApplicationStatus = 'applied';
  const rawStatus = (tracked.application_status || '').toLowerCase();

  if (rawStatus === 'requires_user_action') {
    status = 'action_required';
  } else if (rawStatus === 'submitted') {
    status = 'applied';
  } else if (rawStatus === 'in_progress') {
    status = 'applied';
  } else if (rawStatus === 'screening') {
    status = 'screening';
  } else if (rawStatus === 'interview') {
    status = 'interview';
  } else if (rawStatus === 'offer') {
    status = 'offer';
  } else if (rawStatus === 'failed' || rawStatus === 'rejected') {
    status = 'rejected';
  }

  return {
    id: `app-${tracked.id}`,
    jobId: String(tracked.job_id),
    jobTitle: tracked.job_title,
    company: tracked.company,
    location: tracked.location,
    salary: 'Per employer listing',
    matchScore: 0,
    status,
    appliedDate: tracked.applied_at
      ? new Date(tracked.applied_at).toLocaleDateString()
      : 'Recently',
    lastUpdated: tracked.updated_at
      ? new Date(tracked.updated_at).toLocaleDateString()
      : 'Recently',
    notes: tracked.application_message || 'Application record tracked via CareerOS.',
    nextStep: status === 'action_required'
      ? 'Complete application on official employer portal'
      : (status === 'applied' ? 'Awaiting recruiter response' : undefined),
    sourceName: tracked.source_name,
    destinationType: tracked.destination_type,
    applicationUrl: tracked.job_url,
    confirmationId: tracked.application_confirmation_id || undefined,
    confirmationMessage: tracked.application_message || undefined,
    isVerifiedSubmission: rawStatus === 'submitted',
  };
}
