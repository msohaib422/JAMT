import React from 'react';
import { Satellite, MapPin, Users, Calendar, BarChart3 } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

export default function MissionOverviewCard() {
  const { state } = useMission();

  const percentage = state.duration > 0 ? Math.round((state.currentDay / state.duration) * 100) : 17;
  const isMars = state.destination === 'Mars';

  return (
    <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/85 backdrop-blur-md p-4 sm:p-5 shadow-xl flex flex-col justify-between relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Satellite className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
        <h2 className="text-white font-bold text-base sm:text-lg tracking-tight">
          Mission Overview
        </h2>
      </div>

      {/* Center Layout: Real 3D Planet Photo on Left/Top + Metadata on Right/Bottom */}
      <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 sm:gap-6 my-2">
        {/* Real High-Resolution Planet Photograph (NASA) */}
        <div className="relative flex-shrink-0 flex items-center justify-center p-1">
          {/* Real High-Res Planet Sphere Container with Atmospheric Outer Glow */}
          <div
            className={`relative w-24 h-24 sm:w-28 sm:h-28 rounded-full overflow-hidden border ${
              isMars
                ? 'border-orange-500/40 shadow-[0_0_28px_rgba(234,88,12,0.5)]'
                : 'border-cyan-400/40 shadow-[0_0_28px_rgba(56,189,248,0.4)]'
            }`}
          >
            <img
              src={
                isMars
                  ? "https://upload.wikimedia.org/wikipedia/commons/0/02/OSIRIS_Mars_true_color.jpg"
                  : "https://images.unsplash.com/photo-1522030299830-16b8d3d049fe?auto=format&fit=crop&w=500&q=85"
              }
              alt={isMars ? "Mars Planet true color photograph" : "Moon photograph"}
              className="w-full h-full object-cover scale-110 transform hover:rotate-6 transition-transform duration-700 ease-out"
              loading="lazy"
            />
            {/* Subtle Inner Rim Spherical Shadow Overlay */}
            <div className="absolute inset-0 rounded-full shadow-[inset_-6px_-6px_14px_rgba(0,0,0,0.8),inset_4px_4px_8px_rgba(255,255,255,0.15)] pointer-events-none" />
          </div>
        </div>

        {/* Metadata Details List */}
        <div className="flex-1 w-full space-y-1 sm:space-y-1.5 text-xs sm:text-sm">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-slate-400" /> Destination:
            </span>
            <span className="text-white font-bold flex items-center gap-1">
              <span>{isMars ? '🔴' : '🌙'}</span> {state.destination}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400">Mission Name:</span>
            <span className="text-white font-bold truncate max-w-[140px] sm:max-w-none text-right">
              {state.missionName}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-slate-400" /> Astronauts:
            </span>
            <span className="text-white font-semibold">👥 {state.astronautCount}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-400" /> Duration:
            </span>
            <span className="text-white font-semibold">📅 {state.duration} Days</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" /> Difficulty:
            </span>
            <span className="text-white font-semibold">📊 {state.difficulty}</span>
          </div>
        </div>
      </div>

      {/* Bottom Progress Bar */}
      <div className="mt-2 pt-2 border-t border-blue-500/10">
        <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden border border-slate-700/40">
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${percentage}%`,
              background: 'linear-gradient(90deg, #F97316 0%, #FB923C 100%)',
              boxShadow: '0 0 8px rgba(249, 115, 22, 0.7)',
            }}
          />
        </div>
        <div className="flex justify-between items-center mt-1 text-[11px] text-slate-400 font-medium">
          <span>Mission Progress</span>
          <span className="text-orange-400 font-bold">{percentage}%</span>
        </div>
      </div>
    </div>
  );
}
