import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

const CANDIDATE_SKILLS = [
  { name: 'Python', delay: 400, pos: 'top-8 left-8 sm:left-14' },
  { name: 'Machine Learning', delay: 1000, pos: 'top-16 right-6 sm:right-16' },
  { name: 'RAG Pipelines', delay: 1600, pos: 'bottom-24 left-4 sm:left-10' },
  { name: 'Vector DBs', delay: 2200, pos: 'bottom-20 right-6 sm:right-14' },
  { name: 'System Design', delay: 2800, pos: 'top-1/2 left-2 sm:left-6' },
  { name: 'PyTorch', delay: 3400, pos: 'top-1/2 right-2 sm:right-8' },
  { name: 'AI Engineer', delay: 4000, pos: 'bottom-10 left-1/3' },
];

export const SkillOrbitOverlay: React.FC = () => {
  const [visibleSkills, setVisibleSkills] = useState<string[]>([]);

  useEffect(() => {
    const timers: NodeJS.Timeout[] = [];
    CANDIDATE_SKILLS.forEach((skill) => {
      const t = setTimeout(() => {
        setVisibleSkills((prev) => [...prev, skill.name]);
      }, skill.delay);
      timers.push(t);
    });

    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      <AnimatePresence>
        {CANDIDATE_SKILLS.map((skill) => {
          if (!visibleSkills.includes(skill.name)) return null;

          return (
            <motion.div
              key={skill.name}
              initial={{ opacity: 0, scale: 0.8, y: 10 }}
              animate={{
                opacity: 1,
                scale: 1,
                y: [0, -6, 0],
              }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{
                duration: 0.6,
                y: {
                  repeat: Infinity,
                  duration: 3.5,
                  ease: 'easeInOut',
                },
              }}
              className={`absolute ${skill.pos} px-3 py-1 rounded-md bg-[#0a0f1d]/85 backdrop-blur-md border border-indigo-500/30 text-xs font-medium text-indigo-200 shadow-lg shadow-indigo-950/40 flex items-center gap-1.5`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>{skill.name}</span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};
