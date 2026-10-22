import { UserResume } from '../types/job';

export const SAMPLE_RESUME: UserResume = {
  fileName: 'Alex_Chen_Senior_AI_Engineer_2026.pdf',
  fileSize: '1.8 MB',
  uploadedAt: 'Today, 09:42 AM',
  parsedProfile: {
    fullName: 'Alex Chen',
    title: 'Senior AI & Machine Learning Systems Engineer',
    summary:
      '5+ years building and deploying high-throughput neural inference systems, hybrid RAG pipelines, and agentic LLM workflows. Experienced in scaling Python, PyTorch, and vector search across distributed cloud architectures.',
    yearsOfExperience: 5.5,
    skills: [
      'Python',
      'PyTorch',
      'LLMs',
      'RAG',
      'Vector DBs',
      'FastAPI',
      'Docker',
      'Kubernetes',
      'React',
      'TypeScript',
      'SQL',
      'System Design',
      'Transformers',
      'TensorRT',
    ],
    coreDomains: [
      'Generative AI Infrastructure',
      'Low-Latency Vector Search',
      'Agentic Systems & Tool Calling',
      'Distributed Systems & MLOps',
    ],
    experience: [
      {
        role: 'Senior Machine Learning Engineer',
        company: 'Synthetix AI Systems',
        period: '2023 - Present',
        highlights: [
          'Architected hybrid RAG engine reducing query latency by 42% while serving 8M daily queries.',
          'Built multi-stage reranking pipeline combining BM25 with cross-encoder embeddings.',
          'Mentored 4 junior ML engineers and established unit test standards for non-deterministic model outputs.',
        ],
      },
      {
        role: 'Full-Stack Software Engineer',
        company: 'Veloce Data Labs',
        period: '2021 - 2023',
        highlights: [
          'Engineered real-time analytics streaming pipelines using Kafka, FastAPI, and React.',
          'Containerized microservices with Docker & Kubernetes, attaining 99.98% service uptime.',
        ],
      },
    ],
    education: [
      {
        degree: 'B.S. in Computer Science & Applied Mathematics',
        institution: 'University of California, Berkeley',
        year: '2021',
      },
    ],
    targetRoles: [
      'Senior AI Engineer',
      'Machine Learning Systems Engineer',
      'Staff AI Product Engineer',
      'AI Solutions Architect',
    ],
    preferredLocations: ['Remote', 'San Francisco, CA', 'New York, NY'],
  },
};
