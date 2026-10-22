import React from 'react';
import { UploadCloud, Cpu, Target } from 'lucide-react';

export const HowItWorksSection: React.FC = () => {
  const steps = [
    {
      num: '01',
      title: 'Upload Profile',
      desc: 'Drop your PDF or DOCX resume. Your data is analyzed locally and stays completely private.',
      icon: <UploadCloud className="w-5 h-5 text-indigo-400" />,
    },
    {
      num: '02',
      title: 'AI Synthesis',
      desc: 'Our neural engine extracts core competencies, verifies system depth, and maps your trajectory.',
      icon: <Cpu className="w-5 h-5 text-cyan-400" />,
    },
    {
      num: '03',
      title: 'Precision Matching',
      desc: 'Receive calibrated opportunities with transparent match percentages, skill gap audits, and interview roadmaps.',
      icon: <Target className="w-5 h-5 text-violet-400" />,
    },
  ];

  return (
    <section className="w-full max-w-5xl mx-auto px-4 py-16 border-t border-slate-800/80">
      <div className="text-center mb-12">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white mb-2">
          How It Works
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto">
          A streamlined three-step workflow designed to surface roles where your experience commands high leverage.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {steps.map((step) => (
          <div
            key={step.num}
            className="p-6 rounded-xl bg-[#080d1c] border border-slate-800/80 hover:border-indigo-500/30 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-xs text-indigo-400 font-semibold">
                  {step.num}
                </span>
                <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                  {step.icon}
                </div>
              </div>
              <h3 className="text-base font-semibold text-white tracking-tight mb-2">
                {step.title}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {step.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
