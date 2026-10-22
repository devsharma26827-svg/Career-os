import React, { useRef, useState } from 'react';
import { motion } from 'motion/react';
import { FileText, ShieldCheck, Upload, AlertCircle } from 'lucide-react';

interface ResumeDropZoneProps {
  onFileSelected: (file: File) => void;
  error?: string | null;
  onClearError?: () => void;
}

export const ResumeDropZone: React.FC<ResumeDropZoneProps> = ({
  onFileSelected,
  error,
  onClearError,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragOver) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only deactivate if leaving target area
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragOver(false);
  };

  const validateAndProcessFile = (file: File) => {
    const validExtensions = ['.pdf', '.docx', '.doc'];
    const hasValidExt = validExtensions.some((ext) =>
      file.name.toLowerCase().endsWith(ext)
    );

    if (!hasValidExt) {
      alert('Please upload a PDF or DOCX file.');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('File size exceeds 5MB limit. Please upload a smaller resume.');
      return;
    }

    if (onClearError) onClearError();
    onFileSelected(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndProcessFile(e.target.files[0]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center w-full max-w-xl mx-auto py-4">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        className="hidden"
        onChange={handleFileInputChange}
        aria-label="Upload resume file"
      />

      {/* Center Circular / Oval Portal Drop Zone */}
      <motion.div
        role="button"
        tabIndex={0}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={handleKeyDown}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        whileHover={{ scale: 1.015 }}
        whileTap={{ scale: 0.985 }}
        animate={{
          scale: isDragOver ? 1.03 : 1,
        }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={`relative w-80 h-80 sm:w-96 sm:h-96 rounded-full flex flex-col items-center justify-center cursor-pointer transition-all select-none p-8 text-center outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
          isDragOver
            ? 'shadow-[0_0_80px_rgba(99,102,241,0.45)] ring-2 ring-cyan-400'
            : 'shadow-[0_0_60px_rgba(79,70,229,0.22)]'
        }`}
        style={{
          background: 'radial-gradient(circle at center, #0c1224 0%, #060a16 75%, #050914 100%)',
        }}
      >
        {/* Outer glowing border ring */}
        <div
          className={`absolute inset-0 rounded-full border transition-all duration-300 pointer-events-none ${
            isDragOver
              ? 'border-cyan-400 shadow-[0_0_35px_rgba(56,189,248,0.5)]'
              : 'border-indigo-500/30 hover:border-indigo-400/60'
          }`}
          style={{
            background:
              'radial-gradient(circle at top, rgba(99,102,241,0.15) 0%, transparent 60%)',
          }}
        />

        {/* Subtle breathing ambient aura */}
        <div className="absolute inset-4 rounded-full border border-indigo-500/10 pointer-events-none animate-pulse-glow" />

        {/* Center Document Icon with subtle badge */}
        <div className="relative mb-5 flex items-center justify-center">
          <div className="w-16 h-16 rounded-2xl bg-indigo-950/70 border border-indigo-500/40 flex items-center justify-center text-cyan-400 shadow-inner group-hover:scale-105 transition-transform">
            {isDragOver ? (
              <Upload className="w-8 h-8 animate-bounce text-cyan-300" />
            ) : (
              <FileText className="w-8 h-8 text-indigo-300" />
            )}
          </div>
        </div>

        {/* Instructions */}
        <h3 className="text-xl sm:text-2xl font-semibold tracking-tight text-white mb-1.5">
          {isDragOver ? 'Release to upload resume' : 'Drop your resume here'}
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          or <span className="text-indigo-300 underline underline-offset-4 decoration-indigo-500/50 hover:text-indigo-200">click to browse</span>
        </p>

        {/* Metadata */}
        <div className="text-xs text-slate-500 font-mono tracking-tight flex items-center gap-1.5">
          <span>PDF or DOCX</span>
          <span aria-hidden="true">·</span>
          <span>Max 5MB</span>
        </div>

        {/* Privacy Note */}
        <div className="mt-4 flex items-center gap-1.5 text-xs text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400/90" />
          <span>Your resume stays private</span>
        </div>
      </motion.div>

      {/* Error display if any */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 px-4 py-2.5 rounded-lg bg-rose-950/60 border border-rose-500/40 text-xs text-rose-200 flex items-center gap-2 max-w-sm"
        >
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={onClearError}
            className="text-rose-300 underline hover:text-white"
          >
            Dismiss
          </button>
        </motion.div>
      )}
    </div>
  );
};
