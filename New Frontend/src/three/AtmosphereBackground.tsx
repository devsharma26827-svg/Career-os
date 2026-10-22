import React, { useMemo } from 'react';

export const AtmosphereBackground: React.FC = () => {
  // Generate random static stars for the quiet background
  const stars = useMemo(() => {
    return Array.from({ length: 45 }).map((_, i) => ({
      id: i,
      x: (i * 23) % 100,
      y: (i * 37) % 100,
      size: (i % 3 === 0) ? 1.5 : 1,
      opacity: 0.15 + ((i % 5) * 0.08),
      pulseDelay: (i % 7) * 0.8,
    }));
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10 bg-[#050914]">
      {/* Subtle radial lights */}
      <div
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] rounded-full opacity-35 blur-[120px]"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(79, 70, 229, 0.18) 0%, rgba(30, 27, 75, 0.05) 50%, transparent 80%)',
        }}
      />
      <div
        className="absolute top-2/3 right-1/4 w-[500px] h-[400px] rounded-full opacity-20 blur-[100px]"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(14, 165, 233, 0.12) 0%, transparent 70%)',
        }}
      />

      {/* Subtle orbital lines */}
      <svg
        className="absolute inset-0 w-full h-full opacity-20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="50%"
          cy="42%"
          r="380"
          fill="none"
          stroke="rgba(99, 102, 241, 0.08)"
          strokeWidth="1"
          strokeDasharray="4 8"
        />
        <circle
          cx="50%"
          cy="42%"
          r="540"
          fill="none"
          stroke="rgba(56, 189, 248, 0.05)"
          strokeWidth="1"
        />
        <circle
          cx="50%"
          cy="42%"
          r="720"
          fill="none"
          stroke="rgba(168, 85, 247, 0.04)"
          strokeWidth="1"
          strokeDasharray="6 12"
        />
      </svg>

      {/* Faint star points */}
      {stars.map((star) => (
        <div
          key={star.id}
          className="absolute rounded-full bg-slate-200"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
            opacity: star.opacity,
            animation: `pulseGlow ${3 + (star.pulseDelay)}s ease-in-out infinite`,
            animationDelay: `${star.pulseDelay}s`,
          }}
        />
      ))}
    </div>
  );
};
