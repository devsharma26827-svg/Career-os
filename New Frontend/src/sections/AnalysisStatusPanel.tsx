import React from 'react';
import { motion } from 'motion/react';
import { Sparkles, CheckCircle2 } from 'lucide-react';

interface AnalysisStatusPanelProps {
  phase: string;
  progress: number;
  fileName?: string;
}

export const AnalysisStatusPanel: React.FC<AnalysisStatusPanelProps> = ({
  phase,
  progress,
  fileName,
}) => {
  return (
    <div className="w-full max-w-md mx-auto mt-6 px-6 py-4 rounded-xl bg-[#080d1a]/80 backdrop-blur-md border border-slate-800/80 shadow-2xl shadow-indigo-950/20 text-center">
      <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
        <span className="flex items-center gap-1.5 text-indigo-300">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-spin" style={{ animationDuration: '6s' }} />
          <span>{phase}</span>
        </span>
        <span className="tabular-nums font-semibold text-slate-200">{Math.round(progress)}%</span>
      </div>

      {/* Thin elegant progress bar */}
      <div className="w-full h-1 bg-slate-800/80 rounded-full overflow-hidden relative">
        <motion.div
          className="h-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-violet-500 rounded-full"
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ ease: 'easeOut', duration: 0.3 }}
        />
      </div>

      {fileName && (
        <div className="mt-2.5 flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span className="truncate max-w-[260px]">{fileName}</span>
        </div>
      )}
    </div>
  );
};
