import React from 'react';
import { Home, Bot, Clock, BookOpen, Settings, X, Rocket } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

export default function Sidebar() {
  const { state, setView, openModal, setSidebarOpen } = useMission();

  const navItems = [
    { label: 'Mission Control', icon: Home, action: () => { setView('dashboard'); setSidebarOpen(false); }, isView: true, viewKey: 'dashboard' },
    { label: 'AI Assistant', icon: Bot, action: () => { openModal('ai'); setSidebarOpen(false); } },
    { label: 'Mission History', icon: Clock, action: () => { openModal('history'); setSidebarOpen(false); } },
    { label: 'Learn More', icon: BookOpen, action: () => { openModal('learnMore'); setSidebarOpen(false); } },
    { label: 'Settings', icon: Settings, action: () => { openModal('settings'); setSidebarOpen(false); } },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {state.isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 w-64 bg-[#060D1F] border-r border-blue-500/15 flex flex-col justify-between overflow-y-auto p-4 z-50 transition-transform duration-300 ease-in-out ${
          state.isSidebarOpen ? 'translate-x-0 shadow-2xl shadow-blue-500/20' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* TOP BRAND */}
        <div>
          {/* Close button on mobile */}
          <div className="flex justify-end lg:hidden mb-1">
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800/50"
            >
              <X size={18} />
            </button>
          </div>

          <div className="flex flex-col items-center mb-6 pt-1">
            {/* Glowing Rocket-Orbit SVG Emblem */}
            <div className="relative mb-2.5">
              <div className="absolute inset-0 bg-cyan-500/20 rounded-full blur-xl scale-125" />
              <svg width="68" height="68" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg" className="relative z-10">
                <defs>
                  <filter id="rocketGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                  <linearGradient id="rocketBodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#7DD3FC" />
                    <stop offset="50%" stopColor="#0EA5E9" />
                    <stop offset="100%" stopColor="#0284C7" />
                  </linearGradient>
                </defs>
                {/* Outer Orbit Rings */}
                <ellipse cx="36" cy="36" rx="31" ry="12" stroke="#22d3ee" strokeWidth="1.5" opacity="0.6" transform="rotate(-22 36 36)" />
                <ellipse cx="36" cy="36" rx="31" ry="12" stroke="#38bdf8" strokeWidth="0.75" opacity="0.3" transform="rotate(25 36 36)" />
                {/* Orbiting particles */}
                <circle cx="61" cy="26" r="2.2" fill="#38bdf8" opacity="0.9" />
                <circle cx="12" cy="45" r="1.8" fill="#22d3ee" opacity="0.7" />
                
                {/* Sleek Rocket */}
                <g filter="url(#rocketGlow)">
                  {/* Rocket Fuselage */}
                  <path d="M36 12 C36 12 41 24 41 36 L39 46 L33 46 L31 36 C31 24 36 12 36 12 Z" fill="url(#rocketBodyGrad)" />
                  {/* Nose Cone Tip */}
                  <path d="M36 12 L38 20 L34 20 Z" fill="#E0F2FE" />
                  {/* Cockpit Visor */}
                  <circle cx="36" cy="27" r="3" fill="#0369A1" stroke="#38BDF8" strokeWidth="0.8" />
                  {/* Left & Right Fins */}
                  <path d="M31 38 L25 44 L32 44 Z" fill="#0284C7" />
                  <path d="M41 38 L47 44 L40 44 Z" fill="#0284C7" />
                  {/* Engine Exhaust Flame */}
                  <path d="M34 46 L36 56 L38 46 Z" fill="#F97316" opacity="0.9" />
                  <path d="M35 46 L36 52 L37 46 Z" fill="#FDE047" />
                </g>
              </svg>
            </div>

            <h1 className="text-2xl font-bold font-orbitron text-white text-glow tracking-wider">
              JAMT
            </h1>
            <p className="text-[11px] text-cyan-400 mt-0.5 tracking-wide text-center font-medium">
              Junior Astronaut Mission Trainer
            </p>
          </div>

          {/* NAV MENU */}
          <nav className="flex flex-col gap-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = item.isView && state.currentView === item.viewKey;

              return (
                <button
                  key={item.label}
                  onClick={item.action}
                  className={`flex items-center gap-3 px-4 py-2.5 rounded-full text-sm font-medium transition-all duration-200 w-full text-left cursor-pointer ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon size={18} className={isActive ? 'text-white' : 'text-slate-400'} />
                  <span>{item.label}</span>
                </button>
              );
            })}

            <button
              onClick={() => { setView('landing'); setSidebarOpen(false); }}
              className="flex items-center gap-2.5 px-4 py-2 rounded-full text-xs font-medium text-cyan-400/80 hover:text-cyan-300 hover:bg-cyan-500/10 border border-cyan-500/20 mt-3 transition-all cursor-pointer"
            >
              <Rocket size={14} />
              <span>Welcome / Landing Page</span>
            </button>
          </nav>
        </div>

        {/* BOTTOM ARTWORK CARD */}
        <div className="mt-4">
          <div className="relative rounded-2xl overflow-hidden h-36 mb-2.5 border border-blue-500/25 bg-[#060D1E] shadow-lg group">
            {/* Real Photorealistic Astronaut on Lunar Horizon Photo */}
            <img
              src="https://images.unsplash.com/photo-1541873676-a18131494184?auto=format&fit=crop&w=600&q=85"
              alt="Astronaut in spacesuit looking at Earth horizon"
              className="w-full h-full object-cover object-center transform group-hover:scale-105 transition-transform duration-700 ease-out"
              loading="lazy"
            />

            {/* Seamless Dark Bottom & Ambient Glow Gradient Overlays */}
            <div className="absolute inset-0 bg-gradient-to-t from-[#060D1F] via-[#060D1F]/40 to-transparent pointer-events-none" />
            <div className="absolute inset-0 bg-gradient-to-b from-blue-900/20 via-transparent to-[#060D1F]/90 pointer-events-none" />
          </div>

          <p className="text-xs font-bold text-white text-center tracking-wider uppercase">
            Dream • Build • Explore
          </p>
          <p className="text-[11px] text-slate-400 text-center mt-0.5">
            👥 by <span className="text-cyan-400 font-medium">Regular_Boyz</span>
          </p>
        </div>
      </aside>
    </>
  );
}
