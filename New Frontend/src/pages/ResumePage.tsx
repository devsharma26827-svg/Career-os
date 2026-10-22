import React, { useRef } from 'react';
import { UserResume } from '../types/job';
import { FileText, RefreshCw, Upload, CheckCircle2, Briefcase, GraduationCap, Target } from 'lucide-react';

interface ResumePageProps {
  resume: UserResume | null;
  onReplaceResume: (file: File) => void;
  onReanalyze: () => void;
}

export const ResumePage: React.FC<ResumePageProps> = ({
  resume,
  onReplaceResume,
  onReanalyze,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onReplaceResume(e.target.files[0]);
    }
  };

  if (!resume) {
    return (
      <div className="w-full max-w-4xl mx-auto px-4 py-8">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc"
          className="hidden"
          onChange={handleFileChange}
        />
        <div className="p-12 text-center rounded-2xl bg-[#080d1c] border border-slate-800 space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-indigo-950/70 border border-indigo-500/30 flex items-center justify-center text-cyan-300 mx-auto">
            <FileText className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white mb-1">No Resume Uploaded Yet</h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
              Upload your verified PDF or DOCX resume to extract technical competencies, role alignments, and enable authentic job matching.
            </p>
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors cursor-pointer shadow-lg"
          >
            <Upload className="w-4 h-4" />
            <span>Upload Resume Document</span>
          </button>
        </div>
      </div>
    );
  }

  const { parsedProfile } = resume;

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1">
            Resume Profile
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            Structured representation extracted by the CareerOS neural analysis engine.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Replace File</span>
          </button>
          <button
            onClick={onReanalyze}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Re-analyze</span>
          </button>
        </div>
      </div>

      {/* File Metadata Overview Card */}
      <div className="p-5 rounded-xl bg-[#080d1a] border border-slate-800/80 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-indigo-950/80 border border-indigo-500/30 flex items-center justify-center text-cyan-300 shrink-0">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-tight">
              {resume.fileName}
            </h3>
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mt-0.5">
              <span>{resume.fileSize}</span>
              <span aria-hidden="true">·</span>
              <span>Uploaded {resume.uploadedAt}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
          <CheckCircle2 className="w-4 h-4" />
          <span>Active Index · 100% Vectorized</span>
        </div>
      </div>

      {/* Candidate Profile Details */}
      <div className="space-y-6">
        {/* Summary Card */}
        <div className="p-6 rounded-xl bg-[#080d1a] border border-slate-800/80">
          <div className="mb-4">
            <h3 className="text-lg font-bold text-white tracking-tight">
              {parsedProfile.fullName}
            </h3>
            <p className="text-xs text-indigo-300 font-mono">
              {parsedProfile.title} · {parsedProfile.yearsOfExperience} Years Experience
            </p>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            {parsedProfile.summary}
          </p>
        </div>

        {/* Skills & Domains */}
        <div className="p-6 rounded-xl bg-[#080d1a] border border-slate-800/80">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Extracted Skills & Core Competencies
          </h4>
          <div className="flex flex-wrap gap-2 mb-6">
            {parsedProfile.skills.map((skill) => (
              <span
                key={skill}
                className="px-2.5 py-1 rounded-md text-xs font-mono bg-slate-900 text-indigo-200 border border-slate-800"
              >
                {skill}
              </span>
            ))}
          </div>

          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Target Focus Domains
          </h4>
          <div className="flex flex-wrap gap-2">
            {parsedProfile.coreDomains.map((dom) => (
              <span
                key={dom}
                className="px-2.5 py-1 rounded-md text-xs font-sans bg-indigo-950/40 text-cyan-300 border border-indigo-500/20"
              >
                {dom}
              </span>
            ))}
          </div>
        </div>

        {/* Work History */}
        <div className="p-6 rounded-xl bg-[#080d1a] border border-slate-800/80">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
            <Briefcase className="w-4 h-4 text-indigo-400" />
            <span>Employment Experience</span>
          </h4>
          <div className="space-y-6">
            {parsedProfile.experience.map((exp, idx) => (
              <div key={idx} className="pb-4 border-b border-slate-800/60 last:border-0 last:pb-0">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <h5 className="text-sm font-semibold text-white">
                      {exp.role}
                    </h5>
                    <p className="text-xs text-slate-400">{exp.company}</p>
                  </div>
                  <span className="text-xs font-mono text-slate-500">{exp.period}</span>
                </div>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {exp.highlights.map((h, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="w-1 h-1 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Education & Targets */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-xl bg-[#080d1a] border border-slate-800/80">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <GraduationCap className="w-4 h-4 text-cyan-400" />
              <span>Education</span>
            </h4>
            {parsedProfile.education.map((edu, idx) => (
              <div key={idx}>
                <h5 className="text-sm font-semibold text-white">{edu.degree}</h5>
                <p className="text-xs text-slate-400">{edu.institution} · {edu.year}</p>
              </div>
            ))}
          </div>

          <div className="p-6 rounded-xl bg-[#080d1a] border border-slate-800/80">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Target className="w-4 h-4 text-emerald-400" />
              <span>Target Role Matches</span>
            </h4>
            <div className="space-y-1 text-xs text-slate-300">
              {parsedProfile.targetRoles.map((role) => (
                <div key={role} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-emerald-400" />
                  <span>{role}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
