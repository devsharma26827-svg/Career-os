import { Job, UserResume } from '../types/job';
import { api } from './api';

export interface AIResponse {
  answer: string;
  suggestedFollowUps?: string[];
}

export const aiService = {
  async askAssistant(question: string, context?: { job?: Job; resume?: UserResume }): Promise<AIResponse> {
    await new Promise((resolve) => setTimeout(resolve, 500));

    const qLower = question.toLowerCase();

    if (qLower.includes('why') && qLower.includes('match') && context?.job) {
      return {
        answer: `This ${context.job.title} role at ${context.job.company} matches your profile (${context.job.matchScore}%) because your expertise in ${context.job.breakdown.strongMatches.slice(0, 3).join(', ')} directly satisfies their tier-1 criteria. Their stack requires building high-throughput services, matching your 5+ years of experience with Python and vector retrieval pipelines.`,
        suggestedFollowUps: [
          'What are my key skill gaps for this role?',
          'Generate tailored bullet points for this position',
          'What questions should I ask the hiring manager?',
        ],
      };
    }

    if (qLower.includes('improve') || qLower.includes('resume')) {
      return {
        answer: `To maximize your match rate for top-tier AI engineering roles:
1. Quantify inference throughput: Add exact latencies (e.g. "p99 < 85ms across 12M daily requests").
2. Highlight evaluation benchmarks: Mention specific automated evals (hallucination reduction metrics, recall@k).
3. Showcase deployment tooling: Emphasize experience with vLLM, TensorRT-LLM, or Kubernetes clusters.`,
        suggestedFollowUps: [
          'Show me sample bullet points with metrics',
          'How should I format my RAG project highlight?',
        ],
      };
    }

    if (qLower.includes('interview') || qLower.includes('prepare')) {
      return {
        answer: `For ${context?.job ? context.job.title : 'AI Systems Engineer'} interviews, expect 3 core evaluation pillars:
1. Systems Design: Designing scalable vector search with reranking under 100ms.
2. Production ML / RAG: Chunking strategies, hybrid retrieval, token optimization.
3. Live Coding: Efficient array operations, tensor manipulation, and concurrent worker queues.`,
        suggestedFollowUps: [
          'Generate a mock system design scenario',
          'Give me 3 behavioral questions for this role',
        ],
      };
    }

    // Default intelligent response
    return {
      answer: `Based on your profile as an AI Systems Specialist, your highest leverage opportunities are in low-latency generative pipelines and foundational model deployment. I've highlighted 6 high-affinity roles averaging 90%+ skill overlap.`,
      suggestedFollowUps: [
        'Why does Anthropic Labs have the highest match?',
        'How can I negotiate for the higher salary bracket?',
        'Prepare me for a technical screen',
      ],
    };
  },

  async tailorResumeBulletPoints(job: Job, resume: UserResume): Promise<string[]> {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return [
      `Engineered resilient ${job.skills[0] || 'Python'} & ${job.skills[1] || 'PyTorch'} microservices serving high-throughput inference requests with sub-90ms p95 latency.`,
      `Architected hybrid retrieval pipeline with vector embeddings and cross-encoder rerankers, accelerating semantic search precision by 34%.`,
      `Streamlined model governance and regression evals on Kubernetes clusters, maintaining 99.9% uptime across production model updates.`,
    ];
  },

  async generateCoverLetter(job: Job, resume: UserResume): Promise<string> {
    const numericId = Number(job.id);
    if (!isNaN(numericId) && numericId > 0) {
      try {
        const workspace = await api.applications.generateCoverLetter(numericId, {
          tone: 'professional',
          template_style: 'modern',
        });
        if (workspace && workspace.cover_letter_content) {
          return workspace.cover_letter_content;
        }
      } catch {
        // Fall back to template below
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 600));
    return `Dear Hiring Team at ${job.company},

I am writing to express my enthusiastic interest in the ${job.title} position. Having scaled production deep learning pipelines and generative AI retrieval workflows over the past 5+ years, I have followed ${job.company}'s work with great admiration.

My background centers on architecting latency-critical systems with ${job.skills.slice(0, 3).join(', ')}. In my recent work at Synthetix AI Systems, I reduced semantic retrieval query latency by 42% across millions of daily user interactions, while maintaining rigorous evaluation harnesses against model hallucinations.

${job.company}'s focus on ${job.responsibilities[0]?.toLowerCase() || 'advancing state-of-the-art model infrastructure'} directly aligns with where I do my best engineering work. I would welcome the opportunity to bring my hands-on experience in distributed systems and modern AI orchestration to your team.

Thank you for your time and consideration.

Sincerely,
${resume.parsedProfile.fullName}
${resume.parsedProfile.title}`;
  },

  async getInterviewQuestions(job: Job): Promise<{ category: string; question: string; guidance: string }[]> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    return [
      {
        category: 'System Architecture',
        question: `How would you architect a production RAG system for ${job.company} that handles 10,000 queries per second with a 150ms p99 SLA?`,
        guidance: 'Discuss multi-tier caching (semantic vs exact), vector index sharding (HNSW), asynchronous reranking, and token streaming.',
      },
      {
        category: 'Deep Learning & ML Fundamentals',
        question: 'What are the trade-offs between dense semantic embeddings and sparse lexical search (BM25), and how would you implement reciprocal rank fusion?',
        guidance: 'Explain why hybrid search protects against out-of-vocabulary technical identifiers, and outline the math behind RRF scoring.',
      },
      {
        category: 'Production Reliability & MLOps',
        question: 'How do you detect and mitigate silent data drift or model hallucination regressions in continuous deployment pipelines?',
        guidance: 'Detail golden test datasets, automated LLM-as-a-judge evaluators, confidence thresholding, and shadow canary releases.',
      },
    ];
  },
};
