import React from 'react';
import { Heart, Activity } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

const statusConfig = {
  Healthy: {
    dot: 'bg-emerald-400',
    text: 'text-emerald-400',
    ecgStroke: '#00F0FF',
    glow: 'rgba(0, 240, 255, 0.4)',
  },
  'Watch Out': {
    dot: 'bg-amber-400',
    text: 'text-amber-400',
    ecgStroke: '#FBBF24',
    glow: 'rgba(251, 191, 36, 0.4)',
  },
  Critical: {
    dot: 'bg-red-400',
    text: 'text-red-400',
    ecgStroke: '#F87171',
    glow: 'rgba(248, 113, 113, 0.4)',
  },
};

const ASTRONAUT_PHOTOS = {
  'Alex Carter': 'https://images.unsplash.com/photo-1541873676-a18131494184?auto=format&fit=crop&w=200&q=80',
  'Sarah Mitchell': 'https://images.unsplash.com/photo-1581822261290-991b38693d1b?auto=format&fit=crop&w=200&q=80',
  'David Kim': 'https://images.unsplash.com/photo-1614728263952-84ea256f9679?auto=format&fit=crop&w=200&q=80',
};

// Real Astronaut Portrait Avatar
function AstronautAvatar({ name, idx }) {
  const photoUrl =
    ASTRONAUT_PHOTOS[name] ||
    [
      'https://images.unsplash.com/photo-1541873676-a18131494184?auto=format&fit=crop&w=200&q=80',
      'https://images.unsplash.com/photo-1581822261290-991b38693d1b?auto=format&fit=crop&w=200&q=80',
      'https://images.unsplash.com/photo-1614728263952-84ea256f9679?auto=format&fit=crop&w=200&q=80',
    ][idx % 3];

  return (
    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full overflow-hidden border border-cyan-400/50 shadow-[0_0_10px_rgba(56,189,248,0.35)] shrink-0 bg-[#0A162D] relative group">
      <img
        src={photoUrl}
        alt={name}
        className="w-full h-full object-cover object-center group-hover:scale-110 transition-transform duration-300"
        loading="lazy"
      />
    </div>
  );
}

// Medical ECG Waveform SVG
function EcgWaveform({ status }) {
  const cfg = statusConfig[status] || statusConfig.Healthy;
  const points = "0,16 10,16 15,16 18,12 21,20 24,16 28,16 32,2 35,28 38,10 41,19 44,16 48,16 52,14 56,16 62,16 70,16 74,16 77,12 80,20 83,16 87,16 91,2 94,28 97,10 100,19 103,16 107,16 111,14 115,16 120,16";

  return (
    <div className="w-14 sm:w-20 md:w-24 h-7 flex items-center overflow-hidden shrink-0">
      <svg
        viewBox="0 0 120 30"
        className="w-full h-full"
        preserveAspectRatio="none"
      >
        <polyline
          points={points}
          fill="none"
          stroke={cfg.ecgStroke}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: `drop-shadow(0 0 4px ${cfg.glow})` }}
        />
      </svg>
    </div>
  );
}

function AstronautRow({ astronaut, idx, isLast }) {
  const cfg = statusConfig[astronaut.status] || statusConfig.Healthy;

  return (
    <div
      className={`flex flex-col sm:flex-row items-start sm:items-center justify-between gap-y-2 gap-x-2 py-2 sm:py-2.5 ${
        !isLast ? 'border-b border-blue-500/10' : ''
      }`}
    >
      {/* Left: Real Astronaut Avatar Photo + Full Name */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
        <AstronautAvatar name={astronaut.name} idx={idx} />
        <span className="font-semibold text-white text-xs sm:text-sm whitespace-nowrap">
          {astronaut.name}
        </span>
      </div>

      {/* Right Biometrics & ECG: Status Dot + BPM + Waveform */}
      <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-3 w-full sm:w-auto">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
          <span className={`text-[11px] sm:text-sm font-medium ${cfg.text} whitespace-nowrap`}>
            {astronaut.status}
          </span>
        </div>

        <div className="flex items-center gap-1 text-slate-300 text-[11px] sm:text-sm font-medium shrink-0 whitespace-nowrap">
          <Activity className="w-3.5 h-3.5 text-slate-400" />
          <span>{astronaut.heartRate} bpm</span>
        </div>

        <EcgWaveform status={astronaut.status} />
      </div>
    </div>
  );
}

export default function AstronautHealthCard() {
  const { state } = useMission();
  const astronauts = state.astronauts || [];

  return (
    <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/85 backdrop-blur-md p-4 sm:p-5 shadow-xl flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2 sm:mb-3">
        <Heart className="w-4 h-4 sm:w-5 sm:h-5 text-red-500" />
        <h2 className="text-white font-bold text-base sm:text-lg tracking-tight">
          Astronaut Health
        </h2>
      </div>

      {/* Rows */}
      <div className="space-y-0.5">
        {astronauts.slice(0, 3).map((astro, idx) => (
          <AstronautRow
            key={astro.id || astro.name}
            astronaut={astro}
            idx={idx}
            isLast={idx === Math.min(astronauts.length, 3) - 1}
          />
        ))}
      </div>
    </div>
  );
}
