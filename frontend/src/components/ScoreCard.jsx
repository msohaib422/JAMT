import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

export default function ScoreCard() {
  const { state } = useMission();

  // Determine status styling
  const getStatusConfig = () => {
    switch (state.missionStatus) {
      case 'Warning':
        return {
          dotColor: 'bg-amber-400',
          textColor: 'text-amber-400',
          glow: 'shadow-[0_0_10px_rgba(251,191,36,0.6)]',
          pulse: false,
          label: 'Warning',
        };
      case 'Critical Alert':
        return {
          dotColor: 'bg-red-500',
          textColor: 'text-red-400',
          glow: 'shadow-[0_0_12px_rgba(239,68,68,0.8)]',
          pulse: true,
          label: 'Critical Alert',
        };
      default:
        return {
          dotColor: 'bg-emerald-400',
          textColor: 'text-emerald-400',
          glow: 'shadow-[0_0_10px_rgba(52,211,153,0.7)]',
          pulse: false,
          label: 'On Track',
        };
    }
  };

  const status = getStatusConfig();

  return (
    <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/85 backdrop-blur-md p-4 sm:p-5 flex flex-col justify-between shadow-xl min-h-[190px] sm:min-h-[210px]">
      {/* TOP: Score Header + Value + Sparkline */}
      <div>
        {/* Label and Trend Row */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs sm:text-sm font-medium text-slate-400">Current Score</span>
          <div className="flex items-center gap-1.5 text-emerald-400">
            <ArrowUpRight className="w-4 h-4" />
            {/* Mini Sparkline SVG */}
            <svg
              width="50"
              height="20"
              viewBox="0 0 50 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="overflow-visible"
            >
              <defs>
                <linearGradient id="sparklineGlow" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#10B981" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#34D399" />
                </linearGradient>
              </defs>
              <polyline
                points="2,16 12,14 20,15 30,9 38,11 48,3"
                stroke="url(#sparklineGlow)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
              <circle cx="48" cy="3" r="2.5" fill="#34D399" />
            </svg>
          </div>
        </div>

        {/* 3D Gold Trophy + Score Row */}
        <div className="flex items-center gap-3">
          {/* Rich 3D Gold Trophy SVG */}
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center flex-shrink-0 shadow-inner">
            <svg width="28" height="28" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="goldCup" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#FEF08A" />
                  <stop offset="40%" stopColor="#F59E0B" />
                  <stop offset="100%" stopColor="#B45309" />
                </linearGradient>
                <linearGradient id="goldBase" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#D97706" />
                  <stop offset="50%" stopColor="#FDE047" />
                  <stop offset="100%" stopColor="#92400E" />
                </linearGradient>
              </defs>
              {/* Handles */}
              <path d="M 12 14 C 6 14 6 22 12 24" stroke="url(#goldCup)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
              <path d="M 28 14 C 34 14 34 22 28 24" stroke="url(#goldCup)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
              {/* Cup Body */}
              <path d="M 11 10 L 29 10 L 27 22 C 27 27 23 29 20 29 C 17 29 13 27 13 22 Z" fill="url(#goldCup)" />
              {/* Cup Rim */}
              <ellipse cx="20" cy="10" rx="9" ry="2" fill="#FEF08A" />
              {/* Star on Cup */}
              <polygon points="20,15 21.2,18.5 24.8,18.5 21.9,20.6 23,24 20,22 17,24 18.1,20.6 15.2,18.5 18.8,18.5" fill="#FEF08A" opacity="0.9" />
              {/* Stem */}
              <rect x="18.5" y="29" width="3" height="4" fill="url(#goldBase)" />
              {/* Base */}
              <path d="M 14 33 L 26 33 L 28 36 L 12 36 Z" fill="url(#goldBase)" />
            </svg>
          </div>

          {/* Single-Line Score: 78 / 100 */}
          <div className="whitespace-nowrap flex items-baseline">
            <span className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white tracking-tight">
              {state.score}
            </span>
            <span className="text-lg sm:text-xl lg:text-2xl font-semibold text-slate-400 mx-1 sm:mx-1.5">/</span>
            <span className="text-lg sm:text-xl lg:text-2xl font-semibold text-slate-400">100</span>
          </div>
        </div>
      </div>

      {/* Subtle Divider */}
      <div className="border-t border-blue-500/15 my-3" />

      {/* BOTTOM: Mission Status */}
      <div>
        <p className="text-xs text-slate-400 mb-1.5 font-medium">Mission Status</p>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            {status.pulse && (
              <span className={`absolute inline-flex h-full w-full rounded-full ${status.dotColor} opacity-75 animate-ping`} />
            )}
            <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${status.dotColor} ${status.glow}`} />
          </span>
          <span className={`text-sm font-semibold tracking-wide ${status.textColor}`}>
            {status.label}
          </span>
        </div>
      </div>
    </div>
  );
}
