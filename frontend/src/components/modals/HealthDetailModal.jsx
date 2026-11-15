import React from 'react';
import { X, Heart, Thermometer, Wind, Activity } from 'lucide-react';
import { useMission } from '../../contexts/MissionContext';

const ASTRONAUT_PHOTOS = {
  'Alex Carter': 'https://images.unsplash.com/photo-1541873676-a18131494184?auto=format&fit=crop&w=200&q=80',
  'Sarah Mitchell': 'https://images.unsplash.com/photo-1581822261290-991b38693d1b?auto=format&fit=crop&w=200&q=80',
  'David Kim': 'https://images.unsplash.com/photo-1614728263952-84ea256f9679?auto=format&fit=crop&w=200&q=80',
};

function ECGWaveform({ color = '#22D3EE', width = 200 }) {
  const points = "0,20 5,20 10,20 15,18 18,22 20,20 25,20 28,15 30,8 32,30 34,5 36,25 38,20 40,18 42,22 45,20 50,20 55,20 60,20 65,18 68,22 70,20 75,20 78,15 80,8 82,30 84,5 86,25 88,20 90,18 92,22 95,20 100,20";
  return (
    <div className="overflow-hidden" style={{ width }}>
      <svg viewBox="0 0 100 35" className="w-[200%] h-10 ecg-animate" preserveAspectRatio="none">
        <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

export default function HealthDetailModal() {
  const { state, closeModal } = useMission();

  const getStatusStyle = (status) => {
    switch (status) {
      case 'Healthy': return { dot: 'bg-green-400', text: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30' };
      case 'Watch Out': return { dot: 'bg-amber-400', text: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30' };
      case 'Critical': return { dot: 'bg-red-400', text: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' };
      default: return { dot: 'bg-slate-400', text: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-500/30' };
    }
  };

  const getValueColor = (value, thresholds) => {
    if (value <= thresholds[0]) return 'text-green-400';
    if (value <= thresholds[1]) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" onClick={closeModal}>
      <div className="bg-[#0B162C]/95 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-4 sm:p-6 w-[95vw] max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-600/30 flex items-center justify-center">
              <Heart className="w-4 h-4 text-red-400" />
            </div>
            <h2 className="font-semibold text-white text-lg">Astronaut Health Details</h2>
          </div>
          <button onClick={closeModal} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {state.astronauts.map((astronaut) => {
            const style = getStatusStyle(astronaut.status);
            const ecgColor = astronaut.status === 'Healthy' ? '#22D3EE' : astronaut.status === 'Watch Out' ? '#FBBF24' : '#F87171';
            
            return (
              <div key={astronaut.id} className="glass-card p-4">
                {/* Name & Status */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full overflow-hidden border border-cyan-400/50 shadow-md bg-[#0A162D] shrink-0">
                      <img
                        src={ASTRONAUT_PHOTOS[astronaut.name] || 'https://images.unsplash.com/photo-1541873676-a18131494184?auto=format&fit=crop&w=200&q=80'}
                        alt={astronaut.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{astronaut.name}</h3>
                      <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${style.dot}`} />
                        <span className={`text-xs font-medium ${style.text}`}>{astronaut.status}</span>
                      </div>
                    </div>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-medium border ${style.bg}`}>
                    <span className={style.text}>{astronaut.status}</span>
                  </div>
                </div>

                {/* Vitals Grid */}
                <div className="grid grid-cols-3 gap-4 mb-3">
                  <div className="bg-slate-800/30 rounded-xl p-3">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Activity className="w-3.5 h-3.5 text-red-400" />
                      <span className="text-xs text-slate-400">Heart Rate</span>
                    </div>
                    <div className={`text-xl font-bold ${getValueColor(astronaut.heartRate, [80, 100])}`}>
                      {astronaut.heartRate}
                      <span className="text-xs font-normal text-slate-500 ml-1">bpm</span>
                    </div>
                  </div>
                  <div className="bg-slate-800/30 rounded-xl p-3">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Wind className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="text-xs text-slate-400">O₂ Saturation</span>
                    </div>
                    <div className={`text-xl font-bold ${astronaut.o2sat >= 95 ? 'text-green-400' : astronaut.o2sat >= 90 ? 'text-amber-400' : 'text-red-400'}`}>
                      {astronaut.o2sat}
                      <span className="text-xs font-normal text-slate-500 ml-1">%</span>
                    </div>
                  </div>
                  <div className="bg-slate-800/30 rounded-xl p-3">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Thermometer className="w-3.5 h-3.5 text-orange-400" />
                      <span className="text-xs text-slate-400">Temperature</span>
                    </div>
                    <div className={`text-xl font-bold ${astronaut.temp <= 37 ? 'text-green-400' : astronaut.temp <= 37.5 ? 'text-amber-400' : 'text-red-400'}`}>
                      {astronaut.temp}
                      <span className="text-xs font-normal text-slate-500 ml-1">°C</span>
                    </div>
                  </div>
                </div>

                {/* ECG Waveform */}
                <div className="bg-slate-900/30 rounded-lg p-2 flex items-center justify-center">
                  <ECGWaveform color={ecgColor} width={300} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
