import { ApplicationItem } from '../types/job';

export const INITIAL_APPLICATIONS: ApplicationItem[] = [
  {
    id: 'app-1',
    jobId: 'job-1',
    jobTitle: 'Senior AI Engineer (Foundational Models)',
    company: 'Anthropic Labs',
    location: 'San Francisco, CA (Remote)',
    salary: '$210k - $265k',
    matchScore: 94,
    status: 'interview',
    appliedDate: '3 days ago',
    lastUpdated: 'Yesterday',
    notes: 'Technical screen scheduled for Thursday with the Foundational Models tech lead. Review vector retrieval and token caching.',
    nextStep: 'System Design Interview (Thu 2:00 PM)',
  },
  {
    id: 'app-2',
    jobId: 'job-2',
    jobTitle: 'Machine Learning Systems Engineer',
    company: 'DeepMind Core',
    location: 'New York, NY (Hybrid)',
    salary: '$185k - $225k',
    matchScore: 91,
    status: 'screening',
    appliedDate: '5 days ago',
    lastUpdated: '2 days ago',
    notes: 'Recruiter reached out with screening questionnaire. Completed on Friday.',
    nextStep: 'Waiting for recruiter debrief',
  },
  {
    id: 'app-3',
    jobId: 'job-3',
    jobTitle: 'Staff Full-Stack AI Product Engineer',
    company: 'Linear Velocity',
    location: 'Remote',
    salary: '$220k - $280k',
    matchScore: 89,
    status: 'applied',
    appliedDate: '1 day ago',
    lastUpdated: '1 day ago',
    notes: 'Submitted tailored resume emphasizing sub-100ms streaming LLM interfaces.',
    nextStep: 'Application in initial review',
  },
  {
    id: 'app-4',
    jobId: 'job-6',
    jobTitle: 'AI Research Intern / Junior Researcher',
    company: 'Meta FAIR',
    location: 'Remote',
    salary: '$120k - $145k',
    matchScore: 88,
    status: 'saved',
    appliedDate: '—',
    lastUpdated: 'Saved yesterday',
    notes: 'Bookmark to compare requirements against foundational research papers.',
    nextStep: 'Generate customized cover letter',
  },
];

export interface MarketInsight {
  metric: string;
  value: string;
  change: string;
  context: string;
}

export const MARKET_INSIGHTS: MarketInsight[] = [
  {
    metric: 'Profile Demand Index',
    value: 'Top 4%',
    change: '+18% this month',
    context: 'Across AI/ML systems engineering roles in North America and remote.',
  },
  {
    metric: 'Median Salary Benchmark',
    value: '$218,000',
    change: '+$14k vs Q4',
    context: 'Calibrated against 5+ years experience in LLM orchestration & RAG.',
  },
  {
    metric: 'Most Requested Skill',
    value: 'PyTorch + RAG',
    change: 'Present in 87% of matches',
    context: 'Vector retrieval & low-latency inference remain highest priority.',
  },
  {
    metric: 'Remote Availability',
    value: '68%',
    change: 'Consistent',
    context: 'Major tech hubs expanding remote contracts for senior AI specialists.',
  },
];

export const SKILL_DEMAND_RANKING = [
  { skill: 'PyTorch & Transformers', frequency: '94%', growth: '+28%', status: 'Surging' },
  { skill: 'RAG & Vector Retrieval', frequency: '89%', growth: '+45%', status: 'Critical' },
  { skill: 'Python / FastAPI Async', frequency: '86%', growth: '+12%', status: 'Standard' },
  { skill: 'vLLM / TensorRT Inference', frequency: '72%', growth: '+64%', status: 'High Value' },
  { skill: 'Distributed Kubernetes / Ray', frequency: '65%', growth: '+19%', status: 'Growing' },
];
