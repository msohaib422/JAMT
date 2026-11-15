import React from 'react';
import { useMission } from '../contexts/MissionContext';

export default function HeroBanner() {
  const { state } = useMission();
  const isMoon = state.destination === 'Moon';
  const progress = state.duration > 0 ? (state.currentDay / state.duration) * 100 : 0;

  // Real cinematic space photographs
  const marsPhoto = "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?auto=format&fit=crop&w=1400&q=85";
  const moonPhoto = "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1400&q=85";

  return (
    <div className="relative overflow-hidden min-h-[190px] sm:min-h-[210px] rounded-2xl border border-blue-500/25 bg-[#0B162C] shadow-xl flex flex-col justify-between">
      {/* Real Photorealistic Space Habitat / Planetary Landscape Photo */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <img
          src={isMoon ? moonPhoto : marsPhoto}
          alt={`${state.destination} Base Landscape`}
          className="absolute right-0 top-0 w-full sm:w-[75%] lg:w-[65%] h-full object-cover object-center transform scale-105 opacity-90"
          loading="lazy"
        />

        {/* Cinematic Gradient Blending Mask: Seamlessly blends the right photo into the dark navy left card */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#0B162C] via-[#0B162C]/85 to-transparent sm:via-[#0B162C]/75" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0B162C] via-transparent to-transparent opacity-60" />
      </div>

      {/* Text Overlay (Z-10) */}
      <div className="relative z-10 p-4 sm:p-6 md:p-8 flex flex-col justify-between h-full">
        <div>
          <h2 className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white tracking-tight drop-shadow-md">
            {state.destination} Training Mission
          </h2>
          <p className="text-slate-300/90 text-xs sm:text-base mt-1 font-medium drop-shadow">
            Learn. Decide. Survive.
          </p>
        </div>

        <div className="mt-3 sm:mt-6">
          <span className="inline-flex items-center bg-[#F97316]/25 border border-[#F97316]/60 text-[#FB923C] rounded-full px-3 sm:px-3.5 py-1 text-xs sm:text-sm font-semibold tracking-wide shadow-md backdrop-blur-sm whitespace-nowrap">
            Day {state.currentDay} / {state.duration}
          </span>
        </div>
      </div>

      {/* Bottom Glowing Progress Line */}
      <div className="relative z-10 w-full h-1 bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-r-full transition-all duration-500 ease-out"
          style={{
            width: `${Math.min(progress, 100)}%`,
            background: 'linear-gradient(90deg, #F97316 0%, #38BDF8 100%)',
            boxShadow: '0 0 10px rgba(249, 115, 22, 0.7)',
          }}
        />
      </div>
    </div>
  );
}
