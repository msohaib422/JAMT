import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import * as api from '../services/api';

const MissionContext = createContext(null);

const DIFFICULTY_MULTIPLIERS = { Easy: 0.7, Medium: 1.0, Hard: 1.4 };

const RESOURCE_DRAIN = {
  oxygen: 2, water: 2, food: 2, energy: 3, fuel: 1
};

const EMERGENCY_TYPES = {
  oxygen_leak: {
    id: 'oxygen_leak',
    backendType: 'oxygen_leakage',
    name: 'Oxygen Leakage Detected!',
    severity: 'Critical',
    description: 'A micro-fracture in the habitat hull is causing rapid oxygen depressurization.',
    effects: { oxygenDrainMultiplier: 4, affectedAstronaut: 2, heartRateIncrease: 20 },
    actions: [
      {
        id: 'activate_backup_o2',
        backendAction: 'repair',
        label: 'Activate Backup Oxygen',
        description: 'Immediately activate the secondary O₂ tank to stabilize cabin pressure.',
        effects: { oxygen: 16, energy: -5 },
        scoreChange: 10,
        resolves: true,
        feedback: "Excellent decision, Commander! Activating the backup secondary oxygen reserve immediately stabilized habitat pressure and brought oxygen levels back to 88%. The emergency alert has been resolved, and crew vitals are stabilizing. According to NASA ECLSS protocols, secondary pressurization is the golden rule during critical pressure drops."
      },
      {
        id: 'investigate_isolate',
        backendAction: 'repair',
        label: 'Investigate & Isolate Leakage',
        description: 'Send crew to locate and seal the micro-fracture using emergency hull repair patches.',
        effects: { energy: -3 },
        scoreChange: 15,
        resolves: true,
        feedback: "Outstanding decision! Isolating and repairing the leak source is the definitive fix. On the ISS, the crew uses ultrasonic leak detectors and emergency hull repair kits for exactly this scenario. The micro-fracture has been sealed, stopping all abnormal oxygen loss. This cost 3% energy for the repair tools but permanently resolved the emergency. Real astronauts on the ISS have performed similar repairs during the 2018 Soyuz MS-09 incident."
      },
      {
        id: 'reduce_consumption',
        backendAction: 'wait',
        label: 'Reduce Crew O₂ Consumption',
        description: 'Order crew to minimize physical activity and reduce oxygen consumption rate.',
        effects: {},
        scoreChange: 5,
        resolves: false,
        feedback: "A cautious approach, Commander. Reducing crew activity lowers oxygen consumption by ~30%, but doesn't fix the underlying leak. This is a valid temporary measure but should be combined with repair actions. NASA guidelines note that prolonged inactivity in microgravity leads to muscle atrophy and cardiovascular deconditioning — so this can't be sustained long-term."
      }
    ]
  },
  power_failure: {
    id: 'power_failure',
    backendType: 'power_failure',
    name: 'Power System Failure!',
    severity: 'Critical',
    description: 'Primary solar array has suffered a critical malfunction. Energy reserves dropping rapidly.',
    effects: { energyDrainMultiplier: 3.3, affectedAstronaut: 0, heartRateIncrease: 10 },
    actions: [
      {
        id: 'backup_fuel_cells',
        backendAction: 'repair',
        label: 'Switch to Backup Fuel Cells',
        description: 'Activate hydrogen fuel cell backup power system to restore energy generation.',
        effects: { energy: 30, fuel: -8 },
        scoreChange: 12,
        resolves: true,
        feedback: "Excellent decision! The backup fuel cells are now online and providing stable power. This is exactly how the Apollo 13 crew survived — by carefully managing backup power systems. The fuel cells consumed 8% of fuel reserves but restored energy to operational levels. NASA's PMAD (Power Management and Distribution) system on the ISS performs similar automatic switchovers during solar array anomalies."
      },
      {
        id: 'shed_loads',
        backendAction: 'repair',
        label: 'Shed Non-Essential Loads',
        description: 'Shut down non-critical systems (lighting, experiments, secondary heating) to conserve energy.',
        effects: { energy: 8 },
        scoreChange: 8,
        resolves: false,
        feedback: "Smart conservation strategy, Commander. By shedding non-essential loads, you've reduced power draw by approximately 40%. However, the primary array still needs repair. NASA ISS procedures prioritize load shedding in this order: experiments → secondary lighting → non-critical thermal control. Life support systems always remain powered. This buys time but isn't a permanent solution."
      }
    ]
  },
  solar_storm: {
    id: 'solar_storm',
    backendType: 'solar_radiation_storm',
    name: 'Solar Radiation Storm!',
    severity: 'Critical',
    description: 'A massive Solar Particle Event (SPE) detected. Lethal radiation levels approaching the habitat.',
    effects: { affectedAstronaut: 1, heartRateIncrease: 25 },
    actions: [
      {
        id: 'storm_shelter',
        backendAction: 'rest',
        label: 'Move Crew to Storm Shelter',
        description: 'Immediately evacuate all crew to the shielded storm shelter with polyethylene radiation barriers.',
        effects: {},
        scoreChange: 15,
        resolves: true,
        feedback: "Perfect response, Commander! Moving the crew to the storm shelter within 30 minutes is exactly what NASA's radiation safety protocols require. The polyethylene-based shelter provides >20 g/cm² areal density shielding, reducing radiation exposure by over 90%. During the August 1972 SPE (between Apollo 16 and 17), radiation levels would have been lethal to unshielded astronauts. Your crew is safe!"
      },
      {
        id: 'magnetic_shielding',
        backendAction: 'rest',
        label: 'Divert Power to Shielding',
        description: 'Activate magnetic deflection and water-wall shielding systems around crew quarters.',
        effects: { energy: -10 },
        scoreChange: 10,
        resolves: true,
        feedback: "Good thinking! The water-wall radiation barrier uses existing water supplies to create a shielding layer. This is a real concept being developed by NASA — water is an effective radiation absorber. Combined with the magnetic deflection system, this reduced crew exposure by approximately 75%. The energy cost of 10% is significant but justified for crew safety. NASA's Human Research Program considers this approach promising for Mars transit vehicles."
      }
    ]
  }
};

function createInitialState() {
  return {
    missionId: null,
    // Mission config
    missionName: 'Mars Expedition 01',
    destination: 'Mars',
    astronautCount: 3,
    duration: 30,
    difficulty: 'Medium',
    
    // Mission progress
    currentDay: 5,
    score: 78,
    missionStatus: 'On Track', // 'On Track', 'Warning', 'Critical Alert'
    isActive: true,
    isComplete: false,
    
    // Resources (percentages)
    resources: {
      oxygen: 72,
      water: 85,
      food: 78,
      energy: 65,
      fuel: 80
    },
    
    // Astronauts
    astronauts: [
      { id: 1, name: 'Alex Carter', status: 'Healthy', heartRate: 72, o2sat: 98, temp: 36.6 },
      { id: 2, name: 'Sarah Mitchell', status: 'Healthy', heartRate: 68, o2sat: 99, temp: 36.5 },
      { id: 3, name: 'David Kim', status: 'Watch Out', heartRate: 95, o2sat: 95, temp: 37.1 }
    ],
    
    // Active emergency
    activeEmergency: 'oxygen_leak',
    activeEmergencyId: null,
    emergencyResolved: false,
    
    // Events log
    events: [
      { id: 1, type: 'critical', message: 'Oxygen Leakage Detected!', day: 5, time: '14:32', active: true },
      { id: 2, type: 'info', message: 'Simulation running normally...', day: 5, time: '13:50' },
      { id: 3, type: 'success', message: 'Solar panels operating efficiently.', day: 5, time: '12:20' },
      { id: 4, type: 'success', message: 'Daily health check completed.', day: 5, time: '08:00' },
      { id: 5, type: 'info', message: 'Communication link with Earth stable.', day: 4, time: '22:15' },
      { id: 6, type: 'success', message: 'Water recycling system optimal.', day: 4, time: '16:00' },
    ],
    
    // History for charts
    resourceHistory: [
      { day: 1, oxygen: 100, water: 100, food: 100, energy: 100, fuel: 100 },
      { day: 2, oxygen: 96, water: 97, food: 97, energy: 94, fuel: 99 },
      { day: 3, oxygen: 90, water: 94, food: 94, energy: 88, fuel: 97 },
      { day: 4, oxygen: 82, water: 90, food: 88, energy: 78, fuel: 95 },
      { day: 5, oxygen: 72, water: 85, food: 78, energy: 65, fuel: 80 },
    ],
    healthHistory: [
      { day: 1, alex: 70, sarah: 66, david: 72 },
      { day: 2, alex: 71, sarah: 67, david: 78 },
      { day: 3, alex: 70, sarah: 68, david: 82 },
      { day: 4, alex: 72, sarah: 67, david: 88 },
      { day: 5, alex: 72, sarah: 68, david: 95 },
    ],
    
    // Decision history
    decisions: [],
    
    // AI chat messages
    chatMessages: [
      {
        id: 1,
        role: 'user',
        content: 'Our oxygen levels are dropping. What should we do?',
        timestamp: 'Day 5 • 14:33'
      },
      {
        id: 2,
        role: 'assistant',
        content: 'Commander, oxygen is at 72% and decreasing faster than normal due to the detected leakage. I recommend activating the backup oxygen system immediately. This should stabilize levels while we investigate the source of the leak.',
        timestamp: 'Day 5 • 14:33',
        tools: ['get_mission_status', 'calculate_resource_consumption', 'search_nasa_knowledge'],
        recommendedAction: {
          label: 'Activate Backup Oxygen',
          actionId: 'activate_backup_o2',
          emergencyId: 'oxygen_leak'
        },
        nasaCitation: {
          title: 'NASA ECLSS Oxygen Management Protocol',
          source: 'NASA ECLSS Life Support Systems Document, ISS-ECLSS-DOC-0042',
          content: 'The Secondary O₂ Tank Pressurization & Leak Isolation Protocol requires: (1) Immediate activation of backup O₂ reserves, (2) Isolation of the leaking segment, (3) EVA inspection if internal diagnostics are inconclusive.'
        }
      }
    ],

    // View state
    currentView: 'dashboard', // 'dashboard', 'landing'
    activeModal: null, // 'settings', 'history', 'report', 'health', 'emergency', 'learnMore'
    isSidebarOpen: false,
    backendOnline: false,
  };
}

function missionReducer(state, action) {
  switch (action.type) {
    case 'ADVANCE_DAY': {
      if (state.currentDay >= state.duration || state.isComplete) return state;

      const newDay = state.currentDay + 1;
      const mult = DIFFICULTY_MULTIPLIERS[state.difficulty] || 1;
      const crewMult = state.astronautCount / 3;

      let newResources = { ...state.resources };
      
      // Base drain
      newResources.oxygen = Math.max(0, newResources.oxygen - RESOURCE_DRAIN.oxygen * mult * crewMult);
      newResources.water = Math.max(0, newResources.water - RESOURCE_DRAIN.water * mult * crewMult);
      newResources.food = Math.max(0, newResources.food - RESOURCE_DRAIN.food * mult * crewMult);
      newResources.energy = Math.max(0, newResources.energy - RESOURCE_DRAIN.energy * mult);
      newResources.fuel = Math.max(0, newResources.fuel - RESOURCE_DRAIN.fuel * mult);
      
      // Emergency effects
      if (state.activeEmergency && !state.emergencyResolved) {
        const emergency = EMERGENCY_TYPES[state.activeEmergency];
        if (emergency) {
          if (emergency.effects.oxygenDrainMultiplier) {
            newResources.oxygen = Math.max(0, newResources.oxygen - (RESOURCE_DRAIN.oxygen * emergency.effects.oxygenDrainMultiplier * mult));
          }
          if (emergency.effects.energyDrainMultiplier) {
            newResources.energy = Math.max(0, newResources.energy - (RESOURCE_DRAIN.energy * emergency.effects.energyDrainMultiplier * mult));
          }
        }
      }

      // Round resources
      Object.keys(newResources).forEach(k => {
        newResources[k] = Math.round(newResources[k] * 10) / 10;
      });

      // Update astronauts
      let newAstronauts = state.astronauts.map((a, i) => {
        let hr = a.heartRate + (Math.random() * 4 - 2);
        let o2s = a.o2sat;
        let temp = a.temp;
        let status = 'Healthy';

        if (state.activeEmergency && !state.emergencyResolved) {
          const emergency = EMERGENCY_TYPES[state.activeEmergency];
          if (emergency && i === emergency.effects.affectedAstronaut) {
            hr += emergency.effects.heartRateIncrease * 0.3;
            o2s = Math.max(88, o2s - 1);
            temp = Math.min(38.5, temp + 0.2);
          }
        }

        if (newResources.oxygen < 30) { hr += 10; o2s = Math.max(85, o2s - 2); }
        
        hr = Math.round(Math.max(55, Math.min(140, hr)));
        o2s = Math.round(Math.max(85, Math.min(100, o2s)));
        temp = Math.round(Math.max(36, Math.min(39, temp)) * 10) / 10;

        if (hr > 100 || o2s < 93 || temp > 37.5) status = 'Watch Out';
        if (hr > 120 || o2s < 90 || temp > 38.0) status = 'Critical';

        return { ...a, heartRate: hr, o2sat: o2s, temp, status };
      });

      // Determine mission status
      let missionStatus = 'On Track';
      const anyLow = Object.values(newResources).some(v => v < 30);
      const anyCrit = Object.values(newResources).some(v => v < 15);
      const anyCrewCrit = newAstronauts.some(a => a.status === 'Critical');
      if (anyCrit || anyCrewCrit) missionStatus = 'Critical Alert';
      else if (anyLow || (state.activeEmergency && !state.emergencyResolved)) missionStatus = 'Warning';

      // Score adjustment
      let scoreDelta = 0;
      if (missionStatus === 'On Track') scoreDelta = 1;
      else if (missionStatus === 'Warning') scoreDelta = -1;
      else scoreDelta = -3;

      const newScore = Math.max(0, Math.min(100, state.score + scoreDelta));

      // Events
      const newEvents = [
        { id: Date.now(), type: 'info', message: `Day ${newDay} simulation advanced.`, day: newDay, time: '00:00' },
        ...state.events
      ];

      // History
      const newResourceHistory = [...state.resourceHistory, { day: newDay, ...newResources }];
      const newHealthHistory = [...state.healthHistory, {
        day: newDay,
        alex: newAstronauts[0]?.heartRate || 70,
        sarah: newAstronauts[1]?.heartRate || 68,
        david: newAstronauts[2]?.heartRate || 75
      }];

      // Mission complete?
      const isComplete = newDay >= state.duration;

      return {
        ...state,
        currentDay: newDay,
        resources: newResources,
        astronauts: newAstronauts,
        score: newScore,
        missionStatus,
        events: newEvents,
        resourceHistory: newResourceHistory,
        healthHistory: newHealthHistory,
        isComplete,
        isActive: !isComplete
      };
    }

    case 'TRIGGER_EMERGENCY': {
      let emergencyId = action.payload;
      const emergencyIds = ['oxygen_leak', 'power_failure', 'solar_storm'];
      if (!emergencyId || emergencyId === 'cycle') {
        const currentIndex = emergencyIds.indexOf(state.activeEmergency);
        emergencyId = emergencyIds[(currentIndex + 1) % emergencyIds.length];
      }
      if (!EMERGENCY_TYPES[emergencyId]) return state;

      const emergency = EMERGENCY_TYPES[emergencyId];

      const newEvents = [
        { id: Date.now(), type: 'critical', message: emergency.name, day: state.currentDay, time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }), active: true },
        ...state.events.map(e => ({ ...e, active: false }))
      ];

      // Add AI message about new emergency
      const newMessages = [
        ...state.chatMessages,
        {
          id: Date.now(),
          role: 'assistant',
          content: `⚠️ EMERGENCY ALERT: ${emergency.name} ${emergency.description} I'm analyzing the situation and preparing recommendations...`,
          timestamp: `Day ${state.currentDay} • ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })}`,
          tools: ['detect_emergency', 'get_mission_status', 'search_nasa_knowledge'],
          recommendedAction: {
            label: emergency.actions[0].label,
            actionId: emergency.actions[0].id,
            emergencyId: emergencyId
          },
          nasaCitation: emergencyId === 'oxygen_leak' 
            ? { title: 'NASA ECLSS Oxygen Management Protocol', source: 'NASA ECLSS Life Support Systems Document', content: 'Secondary O₂ Tank Pressurization & Leak Isolation Protocol: Immediately activate backup O₂ reserves and isolate the leaking segment.' }
            : emergencyId === 'power_failure'
            ? { title: 'Solar Array Power Fault Recovery', source: 'NASA Power Systems Engineering, ISS-PWR-SYS-2021', content: 'Backup power: fuel cells provide 45-90 minutes of backup. Emergency power conservation involves shedding non-essential loads.' }
            : { title: 'Space Radiation Shielding Strategies', source: 'NASA Human Research Program, HRP-47072', content: 'During major SPE, crews must reach the storm shelter within 30 minutes. Polyethylene-based shelters reduce radiation by over 90%.' }
        }
      ];

      return {
        ...state,
        activeEmergency: emergencyId,
        emergencyResolved: false,
        missionStatus: 'Critical Alert',
        events: newEvents,
        chatMessages: newMessages
      };
    }

    case 'EXECUTE_ACTION': {
      const { emergencyId, actionId } = action.payload;
      const emergency = EMERGENCY_TYPES[emergencyId];
      if (!emergency) return state;
      
      const emergencyAction = emergency.actions.find(a => a.id === actionId);
      if (!emergencyAction) return state;

      // Apply resource effects
      let newResources = { ...state.resources };
      if (emergencyAction.effects) {
        Object.entries(emergencyAction.effects).forEach(([key, val]) => {
          if (newResources[key] !== undefined) {
            newResources[key] = Math.max(0, Math.min(100, newResources[key] + val));
            newResources[key] = Math.round(newResources[key] * 10) / 10;
          }
        });
      }

      const newScore = Math.max(0, Math.min(100, state.score + emergencyAction.scoreChange));
      const resolved = emergencyAction.resolves;

      // Update astronauts if resolved
      let newAstronauts = state.astronauts;
      if (resolved) {
        newAstronauts = state.astronauts.map(a => {
          if (a.status === 'Watch Out' || a.status === 'Critical') {
            return { ...a, heartRate: Math.max(65, a.heartRate - 15), status: 'Healthy', o2sat: Math.min(99, a.o2sat + 3), temp: Math.max(36.5, a.temp - 0.4) };
          }
          return a;
        });
      }

      let missionStatus = state.missionStatus;
      if (resolved) {
        const anyLow = Object.values(newResources).some(v => v < 30);
        missionStatus = anyLow ? 'Warning' : 'On Track';
      }

      const newEvents = [
        { id: Date.now(), type: 'success', message: `Action taken: ${emergencyAction.label}`, day: state.currentDay, time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) },
        ...(resolved ? [{ id: Date.now() + 1, type: 'success', message: `Emergency resolved: ${emergency.name}`, day: state.currentDay, time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) }] : []),
        ...state.events.map(e => e.type === 'critical' && e.active ? { ...e, active: false } : e)
      ];

      // Add decision to history
      const newDecision = {
        id: Date.now(),
        day: state.currentDay,
        emergency: emergency.name,
        action: emergencyAction.label,
        scoreChange: emergencyAction.scoreChange,
        resolved,
        timestamp: new Date().toISOString()
      };

      // AI educational feedback
      const feedbackMessage = {
        id: Date.now() + 2,
        role: 'assistant',
        content: emergencyAction.feedback,
        timestamp: `Day ${state.currentDay} • ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })}`,
        tools: ['evaluate_decision', 'calculate_resource_impact', 'search_nasa_knowledge'],
        isEducational: true
      };

      return {
        ...state,
        resources: newResources,
        score: newScore,
        missionStatus,
        astronauts: newAstronauts,
        emergencyResolved: resolved ? true : state.emergencyResolved,
        activeEmergency: resolved ? null : state.activeEmergency,
        events: newEvents,
        decisions: [...state.decisions, newDecision],
        chatMessages: [...state.chatMessages, feedbackMessage]
      };
    }

    case 'SEND_CHAT': {
      const userMsg = action.payload;
      const timestamp = `Day ${state.currentDay} • ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })}`;
      
      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: userMsg,
        timestamp
      };

      return {
        ...state,
        chatMessages: [...state.chatMessages, userMessage],
        _pendingAI: true
      };
    }

    case 'AI_RESPOND': {
      const { content, tools, recommendedAction, nasaCitation } = action.payload;
      const timestamp = `Day ${state.currentDay} • ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })}`;

      const aiMessage = {
        id: Date.now(),
        role: 'assistant',
        content,
        timestamp,
        tools: tools || [],
        recommendedAction: recommendedAction || null,
        nasaCitation: nasaCitation || null
      };

      return {
        ...state,
        chatMessages: [...state.chatMessages, aiMessage],
        _pendingAI: false
      };
    }

    case 'SET_VIEW':
      return { ...state, currentView: action.payload };

    case 'OPEN_MODAL':
      return { ...state, activeModal: action.payload };

    case 'CLOSE_MODAL':
      return { ...state, activeModal: null };

    case 'CONFIGURE_MISSION': {
      const config = action.payload;
      const freshState = createInitialState();
      const astronauts = [];
      const names = ['Alex Carter', 'Sarah Mitchell', 'David Kim', 'Elena Rodriguez', 'James Chen', 'Priya Patel'];
      for (let i = 0; i < config.astronautCount; i++) {
        astronauts.push({
          id: i + 1,
          name: names[i] || `Astronaut ${i + 1}`,
          status: 'Healthy',
          heartRate: 65 + Math.floor(Math.random() * 10),
          o2sat: 98 + Math.floor(Math.random() * 2),
          temp: 36.4 + Math.round(Math.random() * 0.3 * 10) / 10
        });
      }

      return {
        ...freshState,
        missionName: config.missionName || `${config.destination} Expedition 01`,
        destination: config.destination,
        astronautCount: config.astronautCount,
        duration: config.duration,
        difficulty: config.difficulty,
        astronauts,
        currentDay: 1,
        score: 50,
        missionStatus: 'On Track',
        activeEmergency: null,
        emergencyResolved: false,
        events: [
          { id: Date.now(), type: 'success', message: 'Mission initialized. All systems nominal.', day: 1, time: '00:00' }
        ],
        resourceHistory: [{ day: 1, oxygen: 100, water: 100, food: 100, energy: 100, fuel: 100 }],
        healthHistory: [{ day: 1, ...Object.fromEntries(astronauts.map(a => [a.name.split(' ')[0].toLowerCase(), a.heartRate])) }],
        chatMessages: [
          {
            id: Date.now(),
            role: 'assistant',
            content: `Welcome aboard, Commander! Your ${config.destination} mission "${config.missionName || config.destination + ' Expedition 01'}" is now active. You have ${config.astronautCount} crew member(s) for a ${config.duration}-day mission on ${config.difficulty} difficulty. All systems are nominal — let's begin!`,
            timestamp: 'Day 1 • 00:00',
            tools: ['initialize_mission', 'verify_systems'],
          }
        ],
        decisions: [],
        currentView: 'dashboard',
        activeModal: null
      };
    }

    case 'SYNC_BACKEND_MISSION': {
      const bData = action.payload;
      return {
        ...state,
        missionId: bData.missionId,
        missionName: bData.missionName || state.missionName,
        destination: bData.destination || state.destination,
        astronautCount: bData.astronautCount || state.astronautCount,
        duration: bData.duration || state.duration,
        difficulty: bData.difficulty || state.difficulty,
        currentDay: bData.currentDay || state.currentDay,
        progress: bData.progress != null ? bData.progress : state.progress,
        score: bData.score != null ? bData.score : state.score,
        missionStatus: bData.missionStatus || state.missionStatus,
        isActive: bData.isActive !== undefined ? bData.isActive : state.isActive,
        isComplete: bData.isComplete !== undefined ? bData.isComplete : state.isComplete,
        resources: bData.resources || state.resources,
        astronauts: bData.astronauts || state.astronauts,
        activeEmergency: bData.activeEmergency !== undefined ? bData.activeEmergency : state.activeEmergency,
        emergencyResolved: bData.emergencyResolved !== undefined ? bData.emergencyResolved : state.emergencyResolved,
        events: bData.events && bData.events.length > 0 ? bData.events : state.events,
        backendOnline: true,
      };
    }

    case 'SET_EMERGENCY_ID':
      return { ...state, activeEmergencyId: action.payload };

    case 'TOGGLE_SIDEBAR':
      return { ...state, isSidebarOpen: !state.isSidebarOpen };

    case 'SET_SIDEBAR':
      return { ...state, isSidebarOpen: action.payload };

    default:
      return state;
  }
}

export function MissionProvider({ children }) {
  const [state, dispatch] = useReducer(missionReducer, null, createInitialState);

  const syncMissionFromBackend = useCallback(async (mId) => {
    try {
      const [m, a, h] = await Promise.all([
        api.getMission(mId),
        api.getMissionAstronauts(mId),
        api.getMissionHistory(mId),
      ]);
      const mapped = api.mapBackendMissionToState(m, a, h);
      dispatch({ type: 'SYNC_BACKEND_MISSION', payload: mapped });
      return mapped;
    } catch (err) {
      console.warn('Backend sync failed, maintaining current state:', err);
      return null;
    }
  }, []);

  // On mount: Check for active mission or initialize default mission on backend
  useEffect(() => {
    let isMounted = true;
    async function initBackend() {
      try {
        const missions = await api.listMissions();
        let target = missions.find(m => m.status === 'active') || missions[0];
        if (!target) {
          const created = await api.createMission({
            name: 'Mars Expedition 01',
            destination: 'mars',
            astronaut_count: 3,
            duration: 30,
            difficulty: 'medium'
          });
          target = await api.startMission(created.id);
        }
        if (isMounted && target) {
          await syncMissionFromBackend(target.id);
        }
      } catch (err) {
        console.warn('Backend connection warning on init (running in resilient mode):', err);
      }
    }
    initBackend();
    return () => { isMounted = false; };
  }, [syncMissionFromBackend]);

  const advanceDay = useCallback(async () => {
    dispatch({ type: 'ADVANCE_DAY' });
    if (state.missionId) {
      try {
        await api.advanceMission(state.missionId);
        await syncMissionFromBackend(state.missionId);
      } catch (err) {
        console.warn('advanceDay API error:', err);
      }
    }
  }, [state.missionId, syncMissionFromBackend]);

  const triggerEmergency = useCallback(async (id) => {
    dispatch({ type: 'TRIGGER_EMERGENCY', payload: id });
    if (state.missionId) {
      try {
        const emType = EMERGENCY_TYPES[id]?.backendType || id;
        const res = await api.triggerEmergency(state.missionId, emType);
        if (res && res.id) {
          dispatch({ type: 'SET_EMERGENCY_ID', payload: res.id });
        }
        await syncMissionFromBackend(state.missionId);
      } catch (err) {
        console.warn('triggerEmergency API error:', err);
      }
    }
  }, [state.missionId, syncMissionFromBackend]);

  const executeAction = useCallback(async (emergencyId, actionId) => {
    dispatch({ type: 'EXECUTE_ACTION', payload: { emergencyId, actionId } });
    if (state.missionId) {
      try {
        const actObj = EMERGENCY_TYPES[emergencyId]?.actions?.find(a => a.id === actionId);
        const backendAction = actObj?.backendAction || 'repair';
        await api.executeAction(state.missionId, backendAction);
        if (state.activeEmergencyId && actObj?.resolves) {
          try {
            await api.resolveEmergency(state.missionId, state.activeEmergencyId);
          } catch (rErr) {
            console.warn('resolveEmergency error:', rErr);
          }
        }
        await syncMissionFromBackend(state.missionId);
      } catch (err) {
        console.warn('executeAction API error:', err);
      }
    }
  }, [state.missionId, state.activeEmergencyId, syncMissionFromBackend]);

  const configureMission = useCallback(async (config) => {
    dispatch({ type: 'CONFIGURE_MISSION', payload: config });
    try {
      const created = await api.createMission({
        name: config.missionName || `${config.destination} Expedition 01`,
        destination: (config.destination || 'mars').toLowerCase(),
        astronaut_count: config.astronautCount || 3,
        duration: config.duration || 30,
        difficulty: (config.difficulty || 'medium').toLowerCase(),
      });
      const started = await api.startMission(created.id);
      await syncMissionFromBackend(started.id);
    } catch (err) {
      console.warn('configureMission API error:', err);
    }
  }, [syncMissionFromBackend]);

  const sendChat = useCallback((msg) => dispatch({ type: 'SEND_CHAT', payload: msg }), []);
  const aiRespond = useCallback((payload) => dispatch({ type: 'AI_RESPOND', payload }), []);
  const setView = useCallback((view) => dispatch({ type: 'SET_VIEW', payload: view }), []);
  const openModal = useCallback((modal) => dispatch({ type: 'OPEN_MODAL', payload: modal }), []);
  const closeModal = useCallback(() => dispatch({ type: 'CLOSE_MODAL' }), []);
  const toggleSidebar = useCallback(() => dispatch({ type: 'TOGGLE_SIDEBAR' }), []);
  const setSidebarOpen = useCallback((open) => dispatch({ type: 'SET_SIDEBAR', payload: open }), []);

  const value = {
    state,
    advanceDay,
    triggerEmergency,
    executeAction,
    sendChat,
    aiRespond,
    setView,
    openModal,
    closeModal,
    configureMission,
    toggleSidebar,
    setSidebarOpen,
    syncMissionFromBackend,
    EMERGENCY_TYPES
  };

  return (
    <MissionContext.Provider value={value}>
      {children}
    </MissionContext.Provider>
  );
}

export function useMission() {
  const context = useContext(MissionContext);
  if (!context) throw new Error('useMission must be used within MissionProvider');
  return context;
}

export { EMERGENCY_TYPES };
