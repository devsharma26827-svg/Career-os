import React, { useState } from 'react';
import { ActiveTab } from '../types/job';
import { User } from '../types/backend';
import { Menu, X, Sparkles, FileText, Bookmark, CheckCircle2, GraduationCap, BarChart3, Search, User as UserIcon, LogOut } from 'lucide-react';

interface NavbarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  savedCount: number;
  applicationsCount: number;
  onUploadClick: () => void;
  user?: User | null;
  onOpenAuth?: () => void;
  onLogout?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  savedCount,
  applicationsCount,
  onUploadClick,
  user,
  onOpenAuth,
  onLogout,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems: Array<{ id: ActiveTab; label: string; icon: React.ReactNode; badge?: number }> = [
    { id: 'search', label: 'Search', icon: <Search className="w-3.5 h-3.5" /> },
    { id: 'applications', label: 'Applications', icon: <CheckCircle2 className="w-3.5 h-3.5" />, badge: applicationsCount },
    { id: 'saved', label: 'Saved', icon: <Bookmark className="w-3.5 h-3.5" />, badge: savedCount },
    { id: 'resume', label: 'Resume', icon: <FileText className="w-3.5 h-3.5" /> },
    { id: 'interview', label: 'Interview Prep', icon: <GraduationCap className="w-3.5 h-3.5" /> },
    { id: 'insights', label: 'Insights', icon: <BarChart3 className="w-3.5 h-3.5" /> },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-[#050914]/85 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Zone 1: Single text element wordmark */}
        <button
          onClick={() => {
            onTabChange('search');
            setMobileMenuOpen(false);
          }}
          className="text-lg font-bold tracking-tight text-white hover:text-indigo-200 transition-colors flex items-center gap-2 cursor-pointer"
        >
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span>CareerOS</span>
        </button>

        {/* Zone 2: 4-6 clean text navigation links */}
        <nav className="hidden md:flex items-center gap-1 text-xs font-medium text-slate-400">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
                  isActive
                    ? 'text-white bg-slate-900 border border-slate-800'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                }`}
              >
                {item.label}
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="ml-0.5 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Zone 3: Primary Action & Auth */}
        <div className="flex items-center gap-3">
          {user ? (
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-xs font-mono text-slate-300 px-2 py-1 rounded bg-slate-900 border border-slate-800 flex items-center gap-1.5">
                <UserIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span className="max-w-[120px] truncate">{user.full_name || user.email.split('@')[0]}</span>
              </span>
              <button
                onClick={onLogout}
                title="Log Out"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-900 transition-colors cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-900/90 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors cursor-pointer"
            >
              <UserIcon className="w-3.5 h-3.5 text-slate-400" />
              <span>Sign In</span>
            </button>
          )}

          <button
            onClick={() => {
              onTabChange('search');
              onUploadClick();
              setMobileMenuOpen(false);
            }}
            className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors shadow-sm cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
            <span>Upload Resume</span>
          </button>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-900 focus:outline-none"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-800 bg-[#070b18] px-4 py-3 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                onTabChange(item.id);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium ${
                activeTab === item.id
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:bg-slate-900 text-slate-300'
              }`}
            >
              <div className="flex items-center gap-2">
                {item.icon}
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-slate-900 text-slate-300">
                  {item.badge}
                </span>
              )}
            </button>
          ))}
          <div className="pt-2 flex flex-col gap-2">
            {user ? (
              <button
                onClick={() => {
                  onLogout?.();
                  setMobileMenuOpen(false);
                }}
                className="w-full py-2 rounded-lg bg-slate-900 border border-slate-800 text-rose-300 text-xs font-medium flex items-center justify-center gap-2"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log Out ({user.full_name || user.email})</span>
              </button>
            ) : (
              <button
                onClick={() => {
                  onOpenAuth?.();
                  setMobileMenuOpen(false);
                }}
                className="w-full py-2 rounded-lg bg-slate-900 border border-slate-800 text-white text-xs font-medium flex items-center justify-center gap-2"
              >
                <UserIcon className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )}

            <button
              onClick={() => {
                onTabChange('search');
                onUploadClick();
                setMobileMenuOpen(false);
              }}
              className="w-full py-2.5 rounded-lg bg-indigo-600 text-white text-xs font-medium flex items-center justify-center gap-2"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
              <span>Upload New Resume</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
