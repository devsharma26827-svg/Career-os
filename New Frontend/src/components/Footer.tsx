import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-800/80 bg-[#050914] py-8 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-300">CareerOS</span>
          <span aria-hidden="true">·</span>
          <span>Intelligent Career Search Engine</span>
        </div>

        <div className="flex items-center gap-2 text-slate-400">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Client-encrypted profile parsing · Resumes stay private</span>
        </div>

        <div className="text-slate-500">
          © {new Date().getFullYear()} CareerOS. All rights reserved.
        </div>
      </div>
    </footer>
  );
};
