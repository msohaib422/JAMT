import React from 'react';
import { MissionProvider, useMission } from './contexts/MissionContext';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import HeroBanner from './components/HeroBanner';
import ScoreCard from './components/ScoreCard';
import ResourceGauges from './components/ResourceGauges';
import AstronautHealthCard from './components/AstronautHealthCard';
import MissionOverviewCard from './components/MissionOverviewCard';
import MissionEventsCard from './components/MissionEventsCard';
import AIMissionControlChat from './components/AIMissionControlChat';
import SimulationControls from './components/SimulationControls';
import LandingPage from './components/LandingPage';
import MissionSetupModal from './components/modals/MissionSetupModal';
import MissionHistoryModal from './components/modals/MissionHistoryModal';
import TrainingReportModal from './components/modals/TrainingReportModal';
import EmergencyModal from './components/modals/EmergencyModal';
import HealthDetailModal from './components/modals/HealthDetailModal';
import LearnMoreModal from './components/modals/LearnMoreModal';

function Dashboard() {
  const { state, closeModal } = useMission();

  return (
    <div className="min-h-screen bg-[#050B18] text-white overflow-x-hidden relative">
      {/* Cosmic Starfield Background */}
      <div className="starfield" />

      {/* Overflow-contained ambient planetary photography container */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        {/* Top Center Horizon Photography Layer */}
        <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-[1200px] h-[380px] overflow-hidden opacity-30 mix-blend-screen">
          <img
            src="https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1800&q=85"
            alt="Glowing planetary atmosphere horizon"
            className="w-full h-full object-cover object-top filter brightness-125 contrast-110"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#050B18]/40 to-[#050B18]" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#050B18] via-transparent to-[#050B18]" />
        </div>

        {/* Bottom Right Curved Planetary Horizon Photography Layer */}
        <div className="absolute -bottom-20 -right-20 w-[520px] h-[520px] rounded-full overflow-hidden opacity-45 mix-blend-screen blur-[0.5px]">
          <img
            src="https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=800&q=85"
            alt="Earth curve horizon from orbit"
            className="w-full h-full object-cover filter brightness-110 contrast-125"
          />
          <div className="absolute inset-0 bg-gradient-to-tl from-transparent via-[#050B18]/40 to-[#050B18]" />
        </div>
      </div>

      {/* Landing Page Overlay if selected */}
      {state.currentView === 'landing' && <LandingPage />}

      {/* Responsive Collapsible Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <main className="lg:ml-64 relative z-10 transition-all duration-300 min-h-screen flex flex-col justify-between overflow-x-hidden">
        <div className="p-3 sm:p-5 md:p-6 max-w-[1750px] mx-auto w-full overflow-x-hidden">
          {/* Top Header */}
          <TopHeader />

          {/* Main Dashboard Grid: Left Content Column + Right AI Mission Control Panel */}
          <div className="flex flex-col xl:flex-row gap-5 md:gap-6 mt-2">
            {/* Left/Center Content Column */}
            <div className="flex-1 min-w-0 space-y-5 md:space-y-6">
              {/* Row 1: Hero Banner (3 cols) + Score Card (1 col) */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 md:gap-6 items-stretch">
                <div className="lg:col-span-3">
                  <HeroBanner />
                </div>
                <div className="lg:col-span-1">
                  <ScoreCard />
                </div>
              </div>

              {/* Row 2: Mission Resources + Astronaut Health */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 md:gap-6 items-stretch">
                <ResourceGauges />
                <AstronautHealthCard />
              </div>

              {/* Row 3: Mission Overview + Mission Events */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 md:gap-6 items-stretch">
                <MissionOverviewCard />
                <MissionEventsCard />
              </div>

              {/* Row 4: Simulation Controls & Quick Actions */}
              <SimulationControls />
            </div>

            {/* Right Column: AI Mission Control Chat Panel */}
            <div className="w-full xl:w-[380px] 2xl:w-[410px] flex-shrink-0">
              <AIMissionControlChat />
            </div>
          </div>
        </div>

        {/* Footer info for complete layout */}
        <footer className="py-4 text-center text-xs text-slate-500 border-t border-blue-500/10 mt-8">
          JAMT (Junior Astronaut Mission Trainer) • Dream • Build • Explore • by Regular_Boyz
        </footer>
      </main>

      {/* Modals */}
      {state.activeModal === 'settings' && <MissionSetupModal />}
      {state.activeModal === 'history' && <MissionHistoryModal />}
      {state.activeModal === 'report' && <TrainingReportModal />}
      {state.activeModal === 'emergency' && <EmergencyModal />}
      {state.activeModal === 'health' && <HealthDetailModal />}
      {state.activeModal === 'learnMore' && <LearnMoreModal />}
      {state.activeModal === 'ai' && (
        <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" onClick={closeModal}>
          <div className="w-[95vw] max-w-xl h-[85vh] relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={closeModal}
              className="absolute top-4 right-4 z-20 text-slate-400 hover:text-white bg-slate-800/80 rounded-full w-7 h-7 flex items-center justify-center cursor-pointer border border-blue-500/20"
            >
              ✕
            </button>
            <AIMissionControlChat />
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <MissionProvider>
      <Dashboard />
    </MissionProvider>
  );
}
