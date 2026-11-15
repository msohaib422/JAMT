import React, { useState } from 'react';
import { X, BookOpen, ChevronDown, ChevronUp, Atom, Droplets, Sun, Cpu, Wheat, Globe, Moon } from 'lucide-react';
import { useMission } from '../../contexts/MissionContext';
import { nasaKnowledge } from '../../data/nasaKnowledge';

export default function LearnMoreModal() {
  const { closeModal } = useMission();
  const [expanded, setExpanded] = useState({});

  const toggle = (key) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  const iconMap = {
    oxygen_management: Atom,
    water_recovery: Droplets,
    radiation_shielding: Sun,
    power_systems: Cpu,
    food_systems: Wheat,
    mars_habitat: Globe,
    moon_habitat: Moon
  };

  const colorMap = {
    oxygen_management: 'text-cyan-400',
    water_recovery: 'text-blue-400',
    radiation_shielding: 'text-yellow-400',
    power_systems: 'text-orange-400',
    food_systems: 'text-green-400',
    mars_habitat: 'text-red-400',
    moon_habitat: 'text-slate-300'
  };

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" onClick={closeModal}>
      <div className="bg-[#0B162C]/95 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-4 sm:p-6 w-[95vw] max-w-3xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600/30 flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-blue-400" />
            </div>
            <h2 className="font-semibold text-white text-lg">NASA Knowledge Base</h2>
          </div>
          <button onClick={closeModal} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-slate-400 mb-6">
          Explore real NASA research and protocols used by the AI Mission Control assistant. 
          This curated knowledge base powers the scientific citations in your training missions.
        </p>

        <div className="space-y-3">
          {Object.entries(nasaKnowledge).map(([key, entry]) => {
            const Icon = iconMap[key] || BookOpen;
            const color = colorMap[key] || 'text-blue-400';

            return (
              <div key={key} className="bg-slate-800/30 border border-slate-700/30 rounded-xl overflow-hidden">
                <button
                  onClick={() => toggle(key)}
                  className="w-full flex items-center gap-3 p-4 hover:bg-slate-700/20 transition-colors text-left"
                >
                  <div className={`w-9 h-9 rounded-lg bg-slate-800/80 flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-4.5 h-4.5 ${color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white text-sm truncate">{entry.title}</h3>
                    <p className="text-xs text-slate-500 truncate">{entry.source}</p>
                  </div>
                  {expanded[key] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </button>
                {expanded[key] && (
                  <div className="px-4 pb-4 pt-1 border-t border-slate-700/30">
                    <p className="text-sm text-slate-300 leading-relaxed">{entry.content}</p>
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {entry.keywords.map(kw => (
                        <span key={kw} className="text-xs bg-blue-500/10 text-blue-400 rounded-full px-2 py-0.5">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
