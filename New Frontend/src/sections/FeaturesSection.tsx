import React from 'react';
import { Sparkles, Compass, MessageSquareCode, Layers } from 'lucide-react';

export const FeaturesSection: React.FC = () => {
  const features = [
    {
      title: 'Contextual Resume Parsing',
      desc: 'Goes beyond simple keyword matching to evaluate architectural depth, project scale, and engineering ownership.',
      icon: <Sparkles className="w-5 h-5 text-cyan-400" />,
    },
    {
      title: 'Deterministic Match Scoring',
      desc: 'Transparently breaks down every match into strong overlaps, addressable skill gaps, and salary calibration.',
      icon: <Compass className="w-5 h-5 text-indigo-400" />,
    },
    {
      title: 'AI Career Copilot',
      desc: 'Generate role-tailored bullet points, custom cover letters, and targeted technical interview question sets on demand.',
      icon: <MessageSquareCode className="w-5 h-5 text-emerald-400" />,
    },
    {
      title: 'End-to-End Application Tracking',
      desc: 'Keep saved and active opportunities organized in an intuitive Kanban pipeline from initial match to final offer.',
      icon: <Layers className="w-5 h-5 text-violet-400" />,
    },
  ];

  return (
    <section className="w-full max-w-5xl mx-auto px-4 py-16 border-t border-slate-800/80">
      <div className="text-center mb-12">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white mb-2">
          Engineered for Career Precision
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto">
          Built for software engineers, ML researchers, and systems architects seeking high-affinity roles.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {features.map((feat) => (
          <div
            key={feat.title}
            className="p-6 rounded-xl bg-[#080d1c] border border-slate-800/80 hover:border-indigo-500/30 transition-all flex items-start gap-4"
          >
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 shrink-0">
              {feat.icon}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white tracking-tight mb-1">
                {feat.title}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {feat.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
