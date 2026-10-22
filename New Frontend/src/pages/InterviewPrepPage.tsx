import React, { useState, useEffect } from 'react';
import { Job } from '../types/job';
import { aiService } from '../services/aiService';
import { GraduationCap, Sparkles, CheckCircle2, ChevronRight, MessageSquare, Play, HelpCircle } from 'lucide-react';

interface InterviewPrepPageProps {
  jobs: Job[];
  selectedJobId?: string;
  onSelectJob: (job: Job) => void;
}

export const InterviewPrepPage: React.FC<InterviewPrepPageProps> = ({
  jobs,
  selectedJobId,
  onSelectJob,
}) => {
  const activeJob = jobs.find((j) => j.id === selectedJobId) || jobs[0];
  const [questions, setQuestions] = useState<Array<{ category: string; question: string; guidance: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [practiceActive, setPracticeActive] = useState(false);
  const [practiceAnswer, setPracticeAnswer] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!activeJob) return;
    setLoading(true);
    setPracticeActive(false);
    setFeedback(null);
    aiService.getInterviewQuestions(activeJob).then((q) => {
      setQuestions(q);
      setLoading(false);
    });
  }, [activeJob?.id]);

  const handleSimulateAnswer = () => {
    if (!practiceAnswer.trim() || !activeJob) return;
    setFeedback(
      `Strong answer structure! You clearly addressed caching and token latencies. To strengthen for ${activeJob.company}'s interview bar, consider explicitly mentioning fallback degrade paths if the vector index experiences partition latency.`
    );
  };

  if (!activeJob) {
    return (
      <div className="w-full max-w-5xl mx-auto px-4 py-8">
        <div className="p-12 text-center rounded-2xl bg-[#080d1c] border border-slate-800 space-y-3">
          <GraduationCap className="w-12 h-12 text-indigo-400 mx-auto" />
          <h3 className="text-xl font-bold text-white">No Target Roles Available</h3>
          <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
            Discover and explore jobs in the Search tab to unlock role-specific interview preparation rubrics and questions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1">
            Interview Preparation
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Targeted technical & behavioral simulation tailored to specific role rubrics.
          </p>
        </div>

        {/* Job selector dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Active Target:</span>
          <select
            value={activeJob.id}
            onChange={(e) => {
              const selected = jobs.find((j) => j.id === e.target.value);
              if (selected) onSelectJob(selected);
            }}
            className="px-3 py-1.5 rounded-lg bg-[#090d1c] border border-slate-800 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.company} — {j.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Target Role Context Banner */}
      <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-semibold text-cyan-300">
              {activeJob.matchScore}% Profile Alignment
            </span>
            <span className="text-xs text-slate-500">· {activeJob.location}</span>
          </div>
          <h3 className="text-lg font-bold text-white tracking-tight">
            {activeJob.title} @ {activeJob.company}
          </h3>
        </div>

        <button
          onClick={() => setPracticeActive(!practiceActive)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors self-start sm:self-auto cursor-pointer"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{practiceActive ? 'Close Mock Simulator' : 'Start Mock Practice'}</span>
        </button>
      </div>

      {/* Practice Interactive Simulator */}
      {practiceActive && (
        <div className="mb-8 p-6 rounded-xl bg-[#0a1024] border border-indigo-500/30 space-y-4">
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-300">
            <Sparkles className="w-4 h-4" />
            <span>Interactive AI Mock Evaluator</span>
          </div>

          <h4 className="text-sm font-semibold text-white">
            {questions[0]?.question || 'Explain your approach to architecting a scalable RAG pipeline.'}
          </h4>

          <textarea
            rows={4}
            value={practiceAnswer}
            onChange={(e) => setPracticeAnswer(e.target.value)}
            placeholder="Type your response outline or spoken transcript here..."
            className="w-full p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />

          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500">
              Evaluated against production engineering bar for {activeJob.company}.
            </span>
            <button
              onClick={handleSimulateAnswer}
              disabled={!practiceAnswer.trim()}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-xs font-medium text-white transition-colors cursor-pointer"
            >
              Evaluate Answer
            </button>
          </div>

          {feedback && (
            <div className="p-4 rounded-lg bg-indigo-950/60 border border-indigo-500/30 text-xs text-indigo-200 leading-relaxed">
              <span className="font-semibold block mb-1 text-cyan-300">AI Evaluation Feedback:</span>
              <p>{feedback}</p>
            </div>
          )}
        </div>
      )}

      {/* Structured Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Questions & Rubric */}
        <div className="lg:col-span-2 space-y-4">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <HelpCircle className="w-4 h-4 text-cyan-400" />
            <span>Probable Interview Questions & Evaluation Guidance</span>
          </h4>

          {loading ? (
            <div className="p-8 text-center text-slate-500 text-xs font-mono">
              Loading tailored question matrices...
            </div>
          ) : (
            questions.map((q, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono text-indigo-300 bg-indigo-950/80 border border-indigo-500/20">
                    {q.category}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">Q{idx + 1}</span>
                </div>
                <h5 className="text-sm font-semibold text-white tracking-tight leading-snug">
                  {q.question}
                </h5>
                <div className="pt-2 border-t border-slate-800/60 text-xs text-slate-400 leading-relaxed">
                  <span className="text-slate-300 font-medium">Recommended focus: </span>
                  {q.guidance}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right: Skills to Revise & Interview Checklist */}
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80 space-y-4">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Skills to Revise for this Role
            </h4>
            <div className="space-y-2">
              {activeJob.breakdown.skillGaps.concat(activeJob.skills.slice(0, 2)).map((s, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs"
                >
                  <span className="font-mono text-slate-300">{s}</span>
                  <span className="text-[10px] text-amber-400 font-mono">High Frequency</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80 space-y-3 text-xs">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Candidate Rubric Checklist
            </h4>
            <ul className="space-y-2 text-slate-300">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                <span>Prepare 2 project stories highlighting p99 latency improvements.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                <span>Review hybrid dense/sparse search tradeoffs and vector indexing (HNSW).</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                <span>Draft 3 strategic questions regarding team model deployment cadence.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
