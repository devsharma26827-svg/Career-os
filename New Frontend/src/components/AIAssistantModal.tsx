import React, { useState } from 'react';
import { aiService, AIResponse } from '../services/aiService';
import { Job, UserResume } from '../types/job';
import { Bot, X, Sparkles, Send, ArrowRight } from 'lucide-react';

interface AIAssistantModalProps {
  currentJob?: Job;
  resume?: UserResume | null;
  onSelectSuggestedAction?: (action: string) => void;
}

export const AIAssistantModal: React.FC<AIAssistantModalProps> = ({
  currentJob,
  resume,
  onSelectSuggestedAction,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([
    {
      role: 'assistant',
      text: resume
        ? `Hello! I've indexed your resume for ${resume.parsedProfile.title}. How can I assist your search today?`
        : `Hello! I am your AI career assistant. Upload your resume or ask me any question about roles, skills, and preparation.`,
    },
  ]);
  const [loading, setLoading] = useState(false);

  const promptSuggestions = [
    currentJob ? `Why is ${currentJob.company} a good match?` : 'How can I optimize my resume for AI roles?',
    'What are the highest demand skills right now?',
    'Give me 3 technical interview prep topics',
    'How should I position my RAG experience?',
  ];

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || query;
    if (!text.trim() || loading) return;

    setHistory((prev) => [...prev, { role: 'user', text }]);
    setQuery('');
    setLoading(true);

    try {
      const response: AIResponse = await aiService.askAssistant(text, { job: currentJob, resume: resume || undefined });
      setHistory((prev) => [...prev, { role: 'assistant', text: response.answer }]);
    } catch {
      setHistory((prev) => [
        ...prev,
        { role: 'assistant', text: 'Apologies, I encountered an issue analyzing your query. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-medium shadow-xl shadow-indigo-950/60 border border-indigo-400/30 transition-all hover:scale-105 active:scale-95 cursor-pointer"
        >
          <Sparkles className="w-4 h-4 text-cyan-300" />
          <span>Ask AI</span>
        </button>
      )}

      {/* Floating Assistant Drawer / Dialog */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-full max-w-sm sm:max-w-md h-[520px] rounded-2xl bg-[#090e1e] border border-indigo-500/30 shadow-2xl flex flex-col overflow-hidden text-slate-100">
          {/* Header */}
          <div className="p-3.5 px-4 bg-[#0a1024] border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-indigo-950 border border-indigo-500/30 flex items-center justify-center text-cyan-300">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-white tracking-tight">CareerOS Assistant</h4>
                <p className="text-[10px] text-indigo-300 font-mono">Grounded on your parsed profile</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Conversation history */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs leading-relaxed">
            {history.map((item, idx) => (
              <div
                key={idx}
                className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] p-3 rounded-xl whitespace-pre-wrap ${
                    item.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-none'
                      : 'bg-slate-900/90 text-slate-200 border border-slate-800 rounded-bl-none'
                  }`}
                >
                  {item.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-indigo-300 flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 animate-spin" />
                  <span className="text-[11px] font-mono">Analyzing with CareerOS context...</span>
                </div>
              </div>
            )}
          </div>

          {/* Suggested Quick Prompts */}
          <div className="p-2 border-t border-slate-800/80 bg-[#070b18] overflow-x-auto whitespace-nowrap space-x-1.5 flex items-center no-scrollbar">
            {promptSuggestions.map((suggestion, i) => (
              <button
                key={i}
                onClick={() => handleSend(suggestion)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-900 hover:bg-indigo-950/60 border border-slate-800 hover:border-indigo-500/30 text-[11px] text-slate-300 hover:text-white transition-colors shrink-0"
              >
                <span>{suggestion}</span>
                <ArrowRight className="w-2.5 h-2.5 text-slate-500" />
              </button>
            ))}
          </div>

          {/* Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="p-3 bg-[#0a1024] border-t border-slate-800 flex items-center gap-2"
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about matches, resume tips, or interviews..."
              className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={!query.trim() || loading}
              className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}
    </>
  );
};
