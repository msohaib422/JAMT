import React, { useState } from 'react';
import { X, AlertTriangle, Zap, Wind } from 'lucide-react';
import { useMission, EMERGENCY_TYPES } from '../../contexts/MissionContext';

export default function EmergencyModal() {
  const { state, triggerEmergency, executeAction, closeModal } = useMission();
  const hasActiveEmergency = state.activeEmergency && !state.emergencyResolved;
  const [viewMode, setViewMode] = useState(hasActiveEmergency ? 'actions' : 'scenarios');

  const emergencyOptions = [
    { id: 'oxygen_leak', icon: AlertTriangle, color: 'red', iconColor: 'text-red-400', borderColor: 'hover:border-red-500/50', bgColor: 'bg-red-500/5' },
    { id: 'power_failure', icon: Zap, color: 'orange', iconColor: 'text-orange-400', borderColor: 'hover:border-orange-500/50', bgColor: 'bg-orange-500/5' },
    { id: 'solar_storm', icon: Wind, color: 'purple', iconColor: 'text-purple-400', borderColor: 'hover:border-purple-500/50', bgColor: 'bg-purple-500/5' }
  ];

  const handleTrigger = (id) => {
    triggerEmergency(id);
    closeModal();
  };

  const handleAction = (actionId) => {
    executeAction(state.activeEmergency, actionId);
    closeModal();
  };

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" onClick={closeModal}>
      <div className="bg-[#0B162C]/95 backdrop-blur-xl border border-blue-500/25 rounded-2xl p-4 sm:p-6 w-[95vw] max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-blue-500/15">
          <div className="flex items-center gap-2.5">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${hasActiveEmergency ? 'bg-red-600/30 text-red-400 animate-pulse' : 'bg-amber-600/30 text-amber-400'}`}>
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-bold text-white text-base sm:text-lg">
                {viewMode === 'actions' && hasActiveEmergency
                  ? EMERGENCY_TYPES[state.activeEmergency]?.name
                  : 'Emergency Scenarios'}
              </h2>
              <p className="text-xs text-slate-400">
                {hasActiveEmergency && viewMode === 'actions' ? 'Active Crisis Response' : 'Select a crisis simulation to trigger'}
              </p>
            </div>
          </div>
          <button onClick={closeModal} className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800/60 transition-colors cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* View Switcher if emergency is active */}
        {hasActiveEmergency && (
          <div className="flex flex-col sm:flex-row gap-2 mb-4 p-1 bg-slate-800/40 rounded-xl border border-blue-500/15">
            <button
              onClick={() => setViewMode('actions')}
              className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'actions'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Resolve Current Crisis
            </button>
            <button
              onClick={() => setViewMode('scenarios')}
              className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'scenarios'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Trigger Other Scenarios
            </button>
          </div>
        )}

        {viewMode === 'scenarios' || !hasActiveEmergency ? (
          <div>
            <p className="text-xs sm:text-sm text-slate-300 mb-3 font-medium">
              Choose an emergency scenario to initiate on the habitat:
            </p>

            <div className="space-y-3">
              {emergencyOptions.map(({ id, icon: Icon, iconColor, borderColor, bgColor }) => {
                const emergency = EMERGENCY_TYPES[id];
                const isCurrentlyActive = state.activeEmergency === id && !state.emergencyResolved;

                return (
                  <div
                    key={id}
                    className={`${bgColor} border ${isCurrentlyActive ? 'border-red-500 shadow-md' : 'border-slate-700/50'} ${borderColor} rounded-xl p-3.5 sm:p-4 cursor-pointer transition-all group hover:bg-slate-800/40`}
                    onClick={() => handleTrigger(id)}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-xl bg-slate-800/80 flex items-center justify-center flex-shrink-0 shadow-inner">
                          <Icon className={`w-5 h-5 ${iconColor}`} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-white text-sm sm:text-base group-hover:text-blue-300 transition-colors">
                              {emergency.name}
                            </h3>
                            {isCurrentlyActive && (
                              <span className="text-[10px] font-semibold bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded-full">
                                Currently Active
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                            {emergency.description}
                          </p>
                        </div>
                      </div>

                      <button className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shrink-0 transition-all shadow-md mt-1 self-start sm:self-auto">
                        Trigger →
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div>
            {/* Active Emergency Description Banner */}
            <div className="bg-red-950/50 border border-red-500/40 rounded-xl p-3.5 sm:p-4 mb-4 shadow-[0_0_15px_rgba(239,68,68,0.15)]">
              <p className="text-xs sm:text-sm text-red-200 leading-relaxed font-medium">
                {EMERGENCY_TYPES[state.activeEmergency]?.description}
              </p>
            </div>

            <h3 className="text-xs sm:text-sm font-bold text-white uppercase tracking-wider mb-2.5">
              Available Response Actions:
            </h3>

            <div className="space-y-3">
              {EMERGENCY_TYPES[state.activeEmergency]?.actions.map((action) => (
                <div
                  key={action.id}
                  className="bg-slate-800/40 border border-slate-700/50 hover:border-blue-400/60 rounded-xl p-3.5 sm:p-4 cursor-pointer transition-all group hover:bg-slate-800/70"
                  onClick={() => handleAction(action.id)}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex-1">
                      <h4 className="font-bold text-white text-sm sm:text-base group-hover:text-cyan-300 transition-colors">
                        {action.label}
                      </h4>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                        {action.description}
                      </p>
                      <div className="flex flex-wrap gap-1.5 sm:gap-2 mt-2">
                        {Object.entries(action.effects || {}).map(([key, val]) => (
                          <span
                            key={key}
                            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                              val > 0
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : 'bg-red-500/20 text-red-400 border border-red-500/30'
                            }`}
                          >
                            {val > 0 ? '+' : ''}{val}% {key.charAt(0).toUpperCase() + key.slice(1)}
                          </span>
                        ))}
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/20 text-cyan-300 border border-blue-500/30">
                          +{action.scoreChange} pts
                        </span>
                        {action.resolves && (
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            ✓ Resolves Crisis
                          </span>
                        )}
                      </div>
                    </div>

                    <button className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-xl px-4 py-2 text-xs sm:text-sm font-semibold transition-all shrink-0 self-start sm:self-center shadow-md cursor-pointer">
                      Execute Action ›
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
