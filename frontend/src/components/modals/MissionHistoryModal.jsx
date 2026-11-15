import React, { useState, useEffect } from 'react';
import { X, Clock, TrendingDown } from 'lucide-react';
import { useMission } from '../../contexts/MissionContext';
import * as api from '../../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Legend } from 'recharts';

const tooltipStyle = {
  contentStyle: { background: '#0B162C', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '12px', color: '#e2e8f0', fontSize: '12px' },
  itemStyle: { color: '#e2e8f0' },
  labelStyle: { color: '#94a3b8' }
};

export default function MissionHistoryModal() {
  const { state, closeModal } = useMission();
  const [tab, setTab] = useState('resources');
  const [backendHistory, setBackendHistory] = useState(null);

  useEffect(() => {
    if (state.missionId) {
      api.getMissionHistory(state.missionId)
        .then(res => setBackendHistory(res))
        .catch(err => console.warn('Could not fetch history:', err));
    }
  }, [state.missionId]);

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" onClick={closeModal}>
      <div className="bg-[#0B162C]/95 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-4 sm:p-6 w-[95vw] max-w-4xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600/30 flex items-center justify-center">
              <Clock className="w-4 h-4 text-blue-400" />
            </div>
            <h2 className="font-semibold text-white text-lg">Mission History & Analytics</h2>
          </div>
          <button onClick={closeModal} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-800/50 rounded-xl p-1 mb-6">
          {['resources', 'health', 'actions'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${tab === t ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
            >
              {t === 'resources' ? '📊 Resources' : t === 'health' ? '❤️ Health' : '📋 Action Log'}
            </button>
          ))}
        </div>

        {/* Resources Tab */}
        {tab === 'resources' && (
          <div>
            <p className="text-sm text-slate-400 mb-4">Resource consumption over time (Day 1 → Day {state.currentDay})</p>
            <div className="bg-slate-900/30 rounded-xl p-4 border border-slate-700/30">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={state.resourceHistory}>
                  <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
                  <XAxis dataKey="day" stroke="#475569" tick={{ fill: '#64748b', fontSize: 12 }} label={{ value: 'Day', position: 'insideBottom', offset: -5, fill: '#64748b' }} />
                  <YAxis domain={[0, 100]} stroke="#475569" tick={{ fill: '#64748b', fontSize: 12 }} label={{ value: '%', position: 'insideLeft', fill: '#64748b' }} />
                  <Tooltip {...tooltipStyle} />
                  <Legend wrapperStyle={{ color: '#94a3b8', fontSize: '12px' }} />
                  <Area type="monotone" dataKey="oxygen" stroke="#06B6D4" fill="#06B6D4" fillOpacity={0.1} strokeWidth={2} dot={false} name="Oxygen" />
                  <Area type="monotone" dataKey="water" stroke="#38BDF8" fill="#38BDF8" fillOpacity={0.1} strokeWidth={2} dot={false} name="Water" />
                  <Area type="monotone" dataKey="food" stroke="#22C55E" fill="#22C55E" fillOpacity={0.1} strokeWidth={2} dot={false} name="Food" />
                  <Area type="monotone" dataKey="energy" stroke="#F97316" fill="#F97316" fillOpacity={0.1} strokeWidth={2} dot={false} name="Energy" />
                  <Area type="monotone" dataKey="fuel" stroke="#10B981" fill="#10B981" fillOpacity={0.1} strokeWidth={2} dot={false} name="Fuel" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Health Tab */}
        {tab === 'health' && (
          <div>
            <p className="text-sm text-slate-400 mb-4">Astronaut heart rate trends (BPM)</p>
            <div className="bg-slate-900/30 rounded-xl p-4 border border-slate-700/30">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={state.healthHistory}>
                  <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
                  <XAxis dataKey="day" stroke="#475569" tick={{ fill: '#64748b', fontSize: 12 }} />
                  <YAxis domain={[50, 130]} stroke="#475569" tick={{ fill: '#64748b', fontSize: 12 }} label={{ value: 'BPM', position: 'insideLeft', fill: '#64748b' }} />
                  <Tooltip {...tooltipStyle} />
                  <Legend wrapperStyle={{ color: '#94a3b8', fontSize: '12px' }} />
                  <Line type="monotone" dataKey="alex" stroke="#06B6D4" strokeWidth={2} dot={{ r: 3 }} name="Alex Carter" />
                  <Line type="monotone" dataKey="sarah" stroke="#A78BFA" strokeWidth={2} dot={{ r: 3 }} name="Sarah Mitchell" />
                  <Line type="monotone" dataKey="david" stroke="#F59E0B" strokeWidth={2} dot={{ r: 3 }} name="David Kim" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Actions Tab */}
        {tab === 'actions' && (
          <div className="space-y-3">
            <p className="text-sm text-slate-400 mb-2">Decision and event history</p>
            
            {state.decisions.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-white mb-2">Decisions Made</h3>
                {state.decisions.map((d, i) => (
                  <div key={i} className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-3 mb-2 flex items-center justify-between">
                    <div>
                      <p className="text-sm text-white font-medium">Day {d.day}: {d.action}</p>
                      <p className="text-xs text-slate-400">{d.emergency}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-sm font-semibold ${d.scoreChange > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {d.scoreChange > 0 ? '+' : ''}{d.scoreChange} pts
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${d.resolved ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                        {d.resolved ? 'Resolved' : 'Partial'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <h3 className="text-sm font-medium text-white mb-2">Event Log</h3>
            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {(backendHistory && backendHistory.length > 0 ? backendHistory.slice().reverse() : state.events).map((e, i) => (
                <div key={e.id || i} className="flex items-start gap-3 py-2 px-3 bg-slate-800/20 rounded-lg">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    (e.type || e.event_type)?.includes('emergency') || e.type === 'critical' ? 'bg-red-400' : (e.type || e.event_type)?.includes('action') || e.type === 'success' ? 'bg-green-400' : 'bg-blue-400'
                  }`} />
                  <div>
                    <p className="text-sm text-slate-300">{e.message}</p>
                    <p className="text-xs text-slate-500">Day {e.mission_day || e.day || 1} • {e.time || (e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '12:00')}</p>
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
