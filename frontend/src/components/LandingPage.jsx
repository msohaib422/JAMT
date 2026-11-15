import React from 'react';
import { Rocket, Target, Brain, Trophy, ArrowRight, Star, Sparkles } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';

export default function LandingPage() {
  const { setView, openModal } = useMission();

  return (
    <div className="fixed inset-0 z-50 bg-[#050B18] overflow-y-auto">
      <div className="starfield" />
      
      <div className="relative z-10 max-w-5xl mx-auto px-6 py-16">
        {/* Hero Section */}
        <div className="text-center mb-20">
          {/* Glowing Rocket Emblem */}
          <div className="relative inline-block mb-8">
            <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-3xl scale-150" />
            <svg viewBox="0 0 120 120" className="w-28 h-28 mx-auto relative z-10" fill="none">
              <circle cx="60" cy="60" r="50" stroke="url(#orbitGrad)" strokeWidth="1.5" strokeDasharray="6 4" opacity="0.6">
                <animateTransform attributeName="transform" type="rotate" from="0 60 60" to="360 60 60" dur="20s" repeatCount="indefinite"/>
              </circle>
              <circle cx="60" cy="60" r="35" stroke="url(#orbitGrad)" strokeWidth="1" strokeDasharray="4 6" opacity="0.4">
                <animateTransform attributeName="transform" type="rotate" from="360 60 60" to="0 60 60" dur="15s" repeatCount="indefinite"/>
              </circle>
              <g transform="translate(42,25)">
                <path d="M18 0 C18 0 30 12 30 30 L30 45 C30 48 27 50 24 48 L18 44 L12 48 C9 50 6 48 6 45 L6 30 C6 12 18 0 18 0Z" fill="url(#rocketGrad)" stroke="#60A5FA" strokeWidth="1"/>
                <ellipse cx="18" cy="22" rx="5" ry="6" fill="#0EA5E9" opacity="0.8"/>
                <ellipse cx="18" cy="22" rx="3" ry="4" fill="#7DD3FC" opacity="0.6"/>
                <path d="M12 44 L18 55 L24 44" fill="#F97316" opacity="0.9"/>
                <path d="M14 44 L18 52 L22 44" fill="#FCD34D" opacity="0.7"/>
              </g>
              <circle cx="95" cy="25" r="4" fill="#60A5FA" opacity="0.7">
                <animate attributeName="opacity" values="0.3;0.8;0.3" dur="3s" repeatCount="indefinite"/>
              </circle>
              <circle cx="25" cy="85" r="3" fill="#34D399" opacity="0.5">
                <animate attributeName="opacity" values="0.2;0.6;0.2" dur="4s" repeatCount="indefinite"/>
              </circle>
              <defs>
                <linearGradient id="orbitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3B82F6"/>
                  <stop offset="100%" stopColor="#06B6D4"/>
                </linearGradient>
                <linearGradient id="rocketGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#93C5FD"/>
                  <stop offset="100%" stopColor="#3B82F6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>

          <h1 className="font-orbitron text-5xl md:text-7xl font-bold text-white text-glow mb-3">
            JAMT
          </h1>
          <p className="text-xl md:text-2xl text-blue-400 font-medium mb-2">
            Junior Astronaut Mission Trainer
          </p>
          <p className="text-lg text-slate-400 mb-4 flex items-center justify-center gap-2">
            <Star className="w-4 h-4 text-yellow-400" />
            Dream • Build • Explore
            <Star className="w-4 h-4 text-yellow-400" />
          </p>
          <p className="text-slate-300 max-w-xl mx-auto text-lg mb-8">
            Train like a real astronaut. Make critical decisions. Save your crew.
            Experience NASA-backed mission scenarios in an immersive space command simulator.
          </p>

          <button
            onClick={() => setView('dashboard')}
            className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-lg font-semibold px-8 py-4 rounded-2xl shadow-xl shadow-blue-500/30 inline-flex items-center gap-3 transition-all hover:scale-105 hover:shadow-blue-500/40"
          >
            Start Training
            <ArrowRight className="w-5 h-5" />
          </button>

          <button
            onClick={() => openModal('settings')}
            className="block mx-auto mt-4 text-slate-400 hover:text-blue-400 text-sm transition-colors"
          >
            or configure a custom mission →
          </button>
        </div>

        {/* How It Works */}
        <div className="mb-20">
          <h2 className="text-2xl md:text-3xl font-bold text-white text-center mb-3">
            How JAMT Works
          </h2>
          <p className="text-slate-400 text-center mb-10 max-w-lg mx-auto">
            Four steps to become a certified space commander
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Rocket, title: 'Configure Mission', desc: 'Choose your destination, crew size, and difficulty level for a customized training experience.', color: 'text-blue-400', step: '01' },
              { icon: Target, title: 'Face Emergencies', desc: 'Handle critical situations like oxygen leaks, power failures, and solar radiation storms.', color: 'text-red-400', step: '02' },
              { icon: Brain, title: 'Get AI Guidance', desc: 'Our AI advisor provides NASA-backed recommendations with real scientific citations.', color: 'text-purple-400', step: '03' },
              { icon: Trophy, title: 'Earn Your Rank', desc: 'Score points for smart decisions and climb from Trainee to Mission Commander.', color: 'text-yellow-400', step: '04' }
            ].map(({ icon: Icon, title, desc, color, step }) => (
              <div key={step} className="glass-card p-6 text-center hover:border-blue-500/40 transition-all group">
                <div className="text-xs font-mono text-slate-600 mb-3">STEP {step}</div>
                <div className={`w-14 h-14 rounded-2xl bg-slate-800/50 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform ${color}`}>
                  <Icon className="w-7 h-7" />
                </div>
                <h3 className="font-semibold text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="glass-card p-8 mb-16">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-400 font-orbitron mb-1">3</div>
              <div className="text-sm text-slate-400">Emergency Scenarios</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-400 font-orbitron mb-1">7+</div>
              <div className="text-sm text-slate-400">NASA Research Sources</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-400 font-orbitron mb-1">100%</div>
              <div className="text-sm text-slate-400">Client-Side Simulation</div>
            </div>
          </div>
        </div>

        {/* Team */}
        <div className="text-center pb-8">
          <div className="flex items-center justify-center gap-2 text-slate-400 mb-2">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span className="text-sm">Built with 💙 by</span>
            <Sparkles className="w-4 h-4 text-blue-400" />
          </div>
          <p className="font-semibold text-white text-lg">Regular_Boyz</p>
          <p className="text-slate-500 text-sm mt-1">
            <Star className="w-3 h-3 inline text-yellow-500" /> Dream • Build • Explore <Star className="w-3 h-3 inline text-yellow-500" />
          </p>
        </div>
      </div>
    </div>
  );
}
