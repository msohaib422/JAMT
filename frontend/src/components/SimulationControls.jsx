import React from 'react';
import { Gamepad2, Play, Zap, Clock, Package, Heart, MessageSquare } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

export default function SimulationControls() {
  const { state, advanceDay, openModal } = useMission();

  const handleAskAI = () => {
    // If AI chat input is on screen (desktop/laptop), focus it; otherwise open the modal
    const inputEl = document.getElementById('ai-mission-input');
    if (inputEl && window.innerWidth >= 1280) {
      inputEl.focus();
      inputEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // add a brief highlight glow
      inputEl.classList.add('ring-2', 'ring-cyan-400');
      setTimeout(() => inputEl.classList.remove('ring-2', 'ring-cyan-400'), 1500);
    } else {
      openModal('ai');
    }
  };

  const darkBtnClass =
    'w-full bg-[#0E1A33]/80 hover:bg-[#142344] text-slate-200 border border-blue-500/20 hover:border-blue-400/40 px-2.5 sm:px-3 py-2.5 rounded-xl text-xs sm:text-sm font-medium flex items-center justify-center gap-1.5 sm:gap-2 transition-all duration-200 cursor-pointer shadow-sm whitespace-nowrap';

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
      {/* Left Card: Simulation Controls */}
      <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/85 backdrop-blur-md p-4 sm:p-5 shadow-xl flex flex-col justify-between">
        <div className="flex items-center gap-2 mb-3">
          <Gamepad2 className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
          <h3 className="text-white font-bold text-sm sm:text-base tracking-tight">
            Simulation Controls
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-2.5 w-full">
          {/* Advance Day (Solid Glowing Blue) */}
          <button
            onClick={advanceDay}
            disabled={state.isComplete}
            title="Advance mission simulation by 1 day"
            className={`w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold px-2.5 sm:px-3 py-2.5 rounded-xl text-xs sm:text-sm flex items-center justify-center gap-1.5 transition-all shadow-lg shadow-blue-500/30 cursor-pointer whitespace-nowrap ${
              state.isComplete ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <Play className="w-3.5 h-3.5 fill-white shrink-0" />
            <span>Advance Day</span>
          </button>

          {/* Trigger Emergency */}
          <button
            onClick={() => openModal('emergency')}
            title="Trigger or manage mission emergencies"
            className={darkBtnClass}
          >
            <Zap className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="truncate">Emergency</span>
          </button>

          {/* View Report */}
          <button
            onClick={() => openModal('report')}
            title="View comprehensive mission performance report"
            className={darkBtnClass}
          >
            <Clock className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            <span className="truncate">View Report</span>
          </button>
        </div>
      </div>

      {/* Right Card: Quick Actions */}
      <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/85 backdrop-blur-md p-4 sm:p-5 shadow-xl flex flex-col justify-between">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
          <h3 className="text-white font-bold text-sm sm:text-base tracking-tight">
            Quick Actions
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-2.5 w-full">
          {/* Check Resources */}
          <button
            onClick={() => openModal('history')}
            title="Check detailed resource consumption and analytics"
            className={darkBtnClass}
          >
            <Package className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="truncate">Resources</span>
          </button>

          {/* View Health */}
          <button
            onClick={() => openModal('health')}
            title="View detailed astronaut vitals and biometrics"
            className={darkBtnClass}
          >
            <Heart className="w-3.5 h-3.5 text-red-400 shrink-0" />
            <span className="truncate">View Health</span>
          </button>

          {/* Ask AI */}
          <button
            onClick={handleAskAI}
            title="Ask AI Mission Control for analysis and assistance"
            className={darkBtnClass}
          >
            <MessageSquare className="w-3.5 h-3.5 text-purple-400 shrink-0" />
            <span className="truncate">Ask AI</span>
          </button>
        </div>
      </div>
    </div>
  );
}
