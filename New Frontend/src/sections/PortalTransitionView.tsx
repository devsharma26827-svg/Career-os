import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { GlobeAndPortalCanvas } from '../three/GlobeAndPortalCanvas';
import { Job } from '../types/job';
import { Sparkles, ArrowRight, MapPin, Building2, Check } from 'lucide-react';

interface PortalTransitionViewProps {
  jobs: Job[];
  onComplete: () => void;
}

export const PortalTransitionView: React.FC<PortalTransitionViewProps> = ({
  jobs,
  onComplete,
}) => {
  const [emergedCount, setEmergedCount] = useState(0);

  useEffect(() => {
    // Progressively reveal emerging job cards from the portal center
    const t1 = setTimeout(() => setEmergedCount(1), 500);
    const t2 = setTimeout(() => setEmergedCount(2), 1100);
    const t3 = setTimeout(() => setEmergedCount(3), 1700);
    const t4 = setTimeout(() => setEmergedCount(4), 2300);

    // Auto complete to full results after cards settle
    const autoFinish = setTimeout(() => {
      onComplete();
    }, 4200);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      clearTimeout(autoFinish);
    };
  }, [onComplete]);

  const emergingJobs = jobs.slice(0, 4);

  return (
    <div className="relative w-full min-h-[580px] flex flex-col items-center justify-center overflow-hidden py-10">
      {/* 3D Portal Canvas in Background */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
        <div className="w-[420px] h-[420px] sm:w-[500px] sm:h-[500px]">
          <GlobeAndPortalCanvas mode="portal" />
        </div>
      </div>

      {/* Floating Status Notification */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 mb-8 px-5 py-2 rounded-full bg-[#0a0f1d]/90 backdrop-blur-md border border-cyan-500/30 text-xs font-mono text-cyan-200 shadow-xl shadow-cyan-950/40 flex items-center gap-2"
      >
        <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-spin" style={{ animationDuration: '4s' }} />
        <span>Synthesizing matches across global talent network...</span>
      </motion.div>

      {/* Emerging Job Cards Container */}
      <div className="relative z-10 w-full max-w-4xl px-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {emergingJobs.map((job, index) => {
          if (index >= emergedCount) return null;

          // Compute directional offset based on card index
          const initialX = index % 2 === 0 ? -120 : 120;
          const initialY = index < 2 ? -80 : 80;
          const initialRotate = index % 2 === 0 ? -6 : 6;

          return (
            <motion.div
              key={job.id}
              initial={{
                opacity: 0,
                scale: 0.35,
                x: initialX,
                y: initialY,
                rotate: initialRotate,
              }}
              animate={{
                opacity: 1,
                scale: 1,
                x: 0,
                y: 0,
                rotate: 0,
              }}
              transition={{
                type: 'spring',
                stiffness: 220,
                damping: 24,
                mass: 0.8,
              }}
              className="p-4 sm:p-5 rounded-xl bg-[#090e1c]/90 backdrop-blur-md border border-indigo-500/30 shadow-2xl shadow-indigo-950/50 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-indigo-950/80 border border-indigo-500/30 flex items-center justify-center font-bold text-xs text-cyan-300">
                      {job.logo}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white tracking-tight line-clamp-1">
                        {job.title}
                      </h4>
                      <p className="text-xs text-slate-400 flex items-center gap-1">
                        <Building2 className="w-3 h-3 text-slate-500" />
                        <span>{job.company}</span>
                        <span aria-hidden="true">·</span>
                        <MapPin className="w-3 h-3 text-slate-500" />
                        <span>{job.location}</span>
                      </p>
                    </div>
                  </div>

                  <span className="shrink-0 px-2 py-0.5 rounded text-xs font-mono font-semibold text-emerald-300 bg-emerald-950/60 border border-emerald-500/30">
                    {job.matchScore}% Match
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5 mt-3">
                  {job.skills.slice(0, 3).map((s) => (
                    <span
                      key={s}
                      className="text-[11px] text-slate-400 font-mono px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="font-mono text-slate-300">{job.salaryRange}</span>
                <span className="text-cyan-400 flex items-center gap-1 font-medium">
                  <Check className="w-3.5 h-3.5" /> Matched
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Manual Skip / Continue button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="relative z-10 mt-8"
      >
        <button
          onClick={onComplete}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors shadow-lg shadow-indigo-600/30"
        >
          <span>Explore All Opportunities</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </motion.div>
    </div>
  );
};
