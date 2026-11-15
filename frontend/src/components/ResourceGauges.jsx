import React from 'react';
import { BarChart3, Target, Droplets, Apple, Zap, Fuel } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

const resources = [
  { key: 'oxygen', label: 'Oxygen', color: '#00D2FF', glow: 'rgba(0,210,255,0.4)', Icon: Target },
  { key: 'water', label: 'Water', color: '#38BDF8', glow: 'rgba(56,189,248,0.4)', Icon: Droplets },
  { key: 'food', label: 'Food', color: '#10B981', glow: 'rgba(16,185,129,0.4)', Icon: Apple },
  { key: 'energy', label: 'Energy', color: '#FF7A00', glow: 'rgba(255,122,0,0.4)', Icon: Zap },
  { key: 'fuel', label: 'Fuel', color: '#00F0FF', glow: 'rgba(0,240,255,0.4)', Icon: Fuel },
];

function RadialGauge({ value, color, Icon, label, isLastOnMobile }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius; // ≈ 263.89
  const offset = circumference * (1 - Math.min(100, Math.max(0, value)) / 100);

  return (
    <div className={`flex flex-col items-center shrink-0 p-1 ${isLastOnMobile ? 'col-span-2 sm:col-span-1' : ''}`}>
      <div className="relative w-20 h-20 md:w-24 md:h-24 shrink-0">
        <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
          <defs>
            <filter id={`filter-${label}`} x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="2.5" floodColor={color} floodOpacity="0.6" />
            </filter>
          </defs>

          {/* Background Track Circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth="7"
          />

          {/* Glowing Animated Progress Arc */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            filter={`url(#filter-${label})`}
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center Content: Icon + Percentage */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4 mb-0.5" style={{ color }} />
          <span className="text-xs sm:text-sm font-extrabold text-white tracking-tight">
            {value}%
          </span>
        </div>
      </div>

      {/* Label Under Gauge */}
      <span className="text-[11px] sm:text-xs font-medium text-slate-400 mt-1.5 whitespace-nowrap">
        {label}
      </span>
    </div>
  );
}

export default function ResourceGauges() {
  const { state } = useMission();

  return (
    <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/85 backdrop-blur-md p-4 sm:p-5 shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
        <h2 className="text-white font-bold text-base sm:text-lg tracking-tight">
          Mission Resources
        </h2>
      </div>

      {/* Responsive layout: 2-cols on mobile (<640px), 3-cols/5-cols on tablet, 5-cols in 1 row on desktop */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 xl:grid-cols-5 gap-3 sm:gap-4 justify-items-center items-center">
        {resources.map((res, index) => (
          <RadialGauge
            key={res.key}
            value={state.resources?.[res.key] ?? state[res.key] ?? 0}
            color={res.color}
            Icon={res.Icon}
            label={res.label}
            isLastOnMobile={index === 4}
          />
        ))}
      </div>
    </div>
  );
}
