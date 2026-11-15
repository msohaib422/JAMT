import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useMission, EMERGENCY_TYPES } from '../contexts/MissionContext';

const DOT_COLORS = {
  critical: 'bg-red-400',
  success: 'bg-emerald-400',
  info: 'bg-blue-400',
  warning: 'bg-amber-400',
};

export default function MissionEventsCard() {
  const { state, openModal } = useMission();

  const hasActiveEmergency = state.activeEmergency && !state.emergencyResolved;
  const emergencyData = hasActiveEmergency ? EMERGENCY_TYPES[state.activeEmergency] : null;

  // Filter events to exclude active emergency if displayed in banner, take top 3
  const timelineEvents = (state.events || []).filter(e => !e.active).slice(0, 3);

  return (
    <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/85 backdrop-blur-md p-4 sm:p-5 shadow-xl flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-red-500" />
          <h2 className="text-white font-bold text-base sm:text-lg tracking-tight">
            Mission Events
          </h2>
        </div>
        <button
          onClick={() => openModal('history')}
          className="text-blue-400 hover:text-blue-300 text-xs sm:text-sm font-medium transition-colors cursor-pointer flex items-center gap-1"
        >
          View All <span className="text-base leading-none">→</span>
        </button>
      </div>

      <div className="space-y-2.5">
        {/* Active Emergency Alert Banner */}
        {hasActiveEmergency && emergencyData && (
          <button
            onClick={() => openModal('emergency')}
            className="w-full text-left bg-red-950/60 border border-red-500/50 rounded-xl p-2.5 sm:p-3 flex items-center justify-between gap-3 cursor-pointer hover:bg-red-950/80 transition-all duration-200 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.2)]"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-red-500/20 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-4 h-4 text-red-400" />
              </div>
              <div className="min-w-0">
                <p className="text-red-200 font-bold text-xs sm:text-sm truncate">
                  {emergencyData.name}
                </p>
                <p className="text-[11px] text-red-400/80">
                  Day {state.currentDay} • 14:32
                </p>
              </div>
            </div>

            <span className="bg-red-500/25 border border-red-500/40 text-red-300 rounded-full px-2.5 py-0.5 text-[11px] sm:text-xs font-semibold whitespace-nowrap shrink-0">
              Critical
            </span>
          </button>
        )}

        {/* Timeline Items Below Alert */}
        <div className="space-y-1.5 pt-0.5">
          {timelineEvents.length > 0 ? (
            timelineEvents.map((event) => (
              <div key={event.id} className="flex items-center justify-between text-xs py-1 px-1 gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${DOT_COLORS[event.type] || 'bg-blue-400'}`} />
                  <span className="text-slate-200 text-xs truncate">
                    {event.message}
                  </span>
                </div>
                <span className="text-slate-500 text-[11px] flex-shrink-0 ml-2 whitespace-nowrap">
                  Day {event.day} • {event.time}
                </span>
              </div>
            ))
          ) : (
            <div className="text-xs text-slate-500 py-2 text-center">
              All events logged nominal.
            </div>
          )}
        </div>
      </div>

      <div className="mt-2 text-right">
        <span className="text-[11px] text-slate-500">
          Telemetry stream active
        </span>
      </div>
    </div>
  );
}
