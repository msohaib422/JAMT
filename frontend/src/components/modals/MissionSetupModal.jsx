import React, { useState } from 'react';
import { X, Rocket, Users, Calendar, BarChart3 } from 'lucide-react';
import { useMission } from '../../contexts/MissionContext';

export default function MissionSetupModal() {
  const { configureMission, closeModal } = useMission();
  const [config, setConfig] = useState({
    missionName: '',
    destination: 'Mars',
    astronautCount: 3,
    duration: 30,
    difficulty: 'Medium'
  });

  const handleLaunch = () => {
    configureMission({
      ...config,
      missionName: config.missionName || `${config.destination} Expedition 01`
    });
    closeModal();
  };

  const applyPreset = (preset) => {
    if (preset === 'mars') setConfig({ missionName: 'Mars Expedition 01', destination: 'Mars', astronautCount: 3, duration: 30, difficulty: 'Medium' });
    else setConfig({ missionName: 'Lunar Recon Alpha', destination: 'Moon', astronautCount: 2, duration: 15, difficulty: 'Easy' });
  };

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" onClick={closeModal}>
      <div className="bg-[#0B162C]/95 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-4 sm:p-6 w-[95vw] max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600/30 flex items-center justify-center">
              <Rocket className="w-4 h-4 text-blue-400" />
            </div>
            <h2 className="font-semibold text-white text-lg">Mission Configuration</h2>
          </div>
          <button onClick={closeModal} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Quick Presets */}
        <div className="flex gap-2 mb-6">
          <button onClick={() => applyPreset('mars')} className="text-xs bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 rounded-lg px-3 py-1.5 transition-colors">
            🔴 Quick: Mars 30-Day
          </button>
          <button onClick={() => applyPreset('moon')} className="text-xs bg-slate-500/10 border border-slate-500/30 text-slate-400 hover:bg-slate-500/20 rounded-lg px-3 py-1.5 transition-colors">
            🌙 Quick: Moon 15-Day
          </button>
        </div>

        <div className="space-y-5">
          {/* Mission Name */}
          <div>
            <label className="text-sm text-slate-400 mb-1.5 block">Mission Name</label>
            <input
              type="text"
              value={config.missionName}
              onChange={e => setConfig(p => ({ ...p, missionName: e.target.value }))}
              placeholder={`e.g., ${config.destination} Expedition 01`}
              className="bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 w-full text-white placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500/50 transition-colors"
            />
          </div>

          {/* Destination */}
          <div>
            <label className="text-sm text-slate-400 mb-1.5 block">Destination</label>
            <div className="grid grid-cols-2 gap-2">
              {['Mars', 'Moon'].map(dest => (
                <button
                  key={dest}
                  onClick={() => setConfig(p => ({ ...p, destination: dest }))}
                  className={`py-3 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2 ${config.destination === dest
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600/50'
                  }`}
                >
                  {dest === 'Mars' ? '🔴' : '🌙'} {dest}
                </button>
              ))}
            </div>
          </div>

          {/* Astronaut Count */}
          <div>
            <label className="text-sm text-slate-400 mb-1.5 block flex items-center gap-1">
              <Users className="w-3.5 h-3.5" /> Astronaut Count: <span className="text-white font-semibold">{config.astronautCount}</span>
            </label>
            <input
              type="range"
              min="1"
              max="6"
              value={config.astronautCount}
              onChange={e => setConfig(p => ({ ...p, astronautCount: parseInt(e.target.value) }))}
              className="w-full accent-blue-500"
            />
            <div className="flex justify-between text-xs text-slate-600 mt-1">
              {[1,2,3,4,5,6].map(n => <span key={n}>{n}</span>)}
            </div>
          </div>

          {/* Duration */}
          <div>
            <label className="text-sm text-slate-400 mb-1.5 block flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Mission Duration
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[15, 30, 60].map(d => (
                <button
                  key={d}
                  onClick={() => setConfig(p => ({ ...p, duration: d }))}
                  className={`py-2.5 rounded-xl font-medium text-sm transition-all ${config.duration === d
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600/50'
                  }`}
                >
                  {d} Days
                </button>
              ))}
            </div>
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-sm text-slate-400 mb-1.5 block flex items-center gap-1">
              <BarChart3 className="w-3.5 h-3.5" /> Difficulty
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { level: 'Easy', color: 'green' },
                { level: 'Medium', color: 'yellow' },
                { level: 'Hard', color: 'red' }
              ].map(({ level, color }) => (
                <button
                  key={level}
                  onClick={() => setConfig(p => ({ ...p, difficulty: level }))}
                  className={`py-2.5 rounded-xl font-medium text-sm transition-all ${config.difficulty === level
                    ? `bg-${color === 'green' ? 'green' : color === 'yellow' ? 'yellow' : 'red'}-600 text-white shadow-lg`
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600/50'
                  }`}
                  style={config.difficulty === level ? {
                    background: color === 'green' ? '#16A34A' : color === 'yellow' ? '#CA8A04' : '#DC2626'
                  } : {}}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Launch Button */}
        <button
          onClick={handleLaunch}
          className="w-full mt-6 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-xl py-3.5 font-semibold text-base transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 flex items-center justify-center gap-2"
        >
          Launch Mission 🚀
        </button>
      </div>
    </div>
  );
}
