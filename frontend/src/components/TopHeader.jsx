import React from 'react';
import { Moon, User, Menu } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

export default function TopHeader() {
  const { state, openModal, toggleSidebar } = useMission();

  const isMissionComplete = state.isComplete || state.missionComplete;

  return (
    <div className="flex justify-between items-center mb-5 gap-3">
      {/* Left: Mobile Menu Toggle + Status Pill */}
      <div className="flex items-center gap-3">
        {/* Hamburger Menu on Mobile/Tablet */}
        <button
          onClick={toggleSidebar}
          aria-label="Open Navigation"
          className="lg:hidden p-2 rounded-xl bg-slate-800/60 border border-blue-500/20 text-slate-300 hover:text-white hover:bg-slate-750 transition-colors cursor-pointer"
        >
          <Menu size={20} />
        </button>

        {/* Status Pill */}
        {isMissionComplete ? (
          <div className="bg-orange-950/60 border border-orange-500/40 rounded-full px-3 sm:px-3.5 py-1.5 flex items-center gap-2 shadow-lg shadow-orange-950/40 shrink-0">
            <div className="w-2 h-2 rounded-full bg-orange-400 animate-pulse shrink-0" />
            <span className="text-xs sm:text-sm text-orange-400 font-medium whitespace-nowrap">Mission Complete</span>
          </div>
        ) : (
          <div className="bg-[#052818]/70 border border-emerald-500/40 rounded-full px-3 sm:px-3.5 py-1.5 flex items-center gap-2 shadow-lg shadow-emerald-950/30 shrink-0">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            <span className="text-xs sm:text-sm text-emerald-400 font-medium whitespace-nowrap">Training Active</span>
          </div>
        )}
      </div>

      {/* Right: Moon Icon, Welcome Greeting, Circular Avatar */}
      <div className="flex items-center gap-2.5 sm:gap-4">
        <div className="hidden sm:flex items-center gap-2 text-slate-300 text-sm">
          <Moon size={16} className="text-blue-400" />
          <span>Welcome, Trainee Astronaut!</span>
        </div>

        <button 
          onClick={() => openModal('settings')}
          title="Mission Settings & Profile"
          className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center hover:shadow-lg hover:shadow-blue-500/30 transition-all duration-200 cursor-pointer border border-blue-400/30 flex-shrink-0"
        >
          <User size={16} className="text-white" />
        </button>
      </div>
    </div>
  );
}
