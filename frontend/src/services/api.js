// The backend base URL is injected at build time through the VITE_API_BASE_URL
// environment variable (see jamt/.env.example). Local development keeps working
// without any configuration because it falls back to the existing local backend.
// The trailing slash is stripped so every request below stays well-formed.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export async function listMissions() {
  const res = await fetch(`${API_BASE}/api/missions`);
  return res.json();
}

export async function getMission(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}`);
  return res.json();
}

export async function createMission(payload) {
  const res = await fetch(`${API_BASE}/api/missions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function startMission(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/start`, {
    method: 'POST',
  });
  return res.json();
}

export async function advanceMission(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/simulate`, {
    method: 'POST',
  });
  return res.json();
}

export async function triggerEmergency(missionId, type) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/emergency`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type }),
  });
  return res.json();
}

export async function executeAction(missionId, action) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  return res.json();
}

export async function resolveEmergency(missionId, emergencyId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/emergencies/${emergencyId}/resolve`, {
    method: 'POST',
  });
  return res.json();
}

export async function getMissionStatus(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/status`);
  return res.json();
}

export async function getMissionResources(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/resources`);
  return res.json();
}

export async function getMissionAstronauts(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/astronauts`);
  return res.json();
}

export async function getMissionHistory(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/history`);
  return res.json();
}

export async function getMissionReport(missionId) {
  const res = await fetch(`${API_BASE}/api/missions/${missionId}/report`);
  return res.json();
}

export async function agentChat(missionId, message) {
  const res = await fetch(`${API_BASE}/api/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mission_id: missionId, message }),
  });
  return res.json();
}

/**
 * Maps backend mission, astronauts, and history data into the exact React state format
 * expected by all dashboard components without modifying any UI design.
 */
export function mapBackendMissionToState(backendMission, astronauts, historyEvents) {
  // Translate status
  let missionStatus = 'On Track';
  if (backendMission.status === 'failed') {
    missionStatus = 'Critical Alert';
  } else if (
    (backendMission.oxygen != null && backendMission.oxygen < 40) ||
    (backendMission.water != null && backendMission.water < 40) ||
    (backendMission.energy != null && backendMission.energy < 40)
  ) {
    missionStatus = 'Warning';
  } else if (backendMission.emergencies && backendMission.emergencies.length > 0) {
    missionStatus = 'Critical Alert';
  }

  // Active emergency
  let activeEmergency = null;
  let emergencyResolved = false;
  if (backendMission.emergencies && backendMission.emergencies.length > 0) {
    const active = backendMission.emergencies[0];
    const typeStr = active.type || active.emergency_type || '';
    if (typeStr.includes('oxygen')) activeEmergency = 'oxygen_leak';
    else if (typeStr.includes('power')) activeEmergency = 'power_failure';
    else if (typeStr.includes('radiation') || typeStr.includes('solar')) activeEmergency = 'solar_storm';
    else activeEmergency = typeStr;
  } else if (backendMission.resolved_emergencies && backendMission.resolved_emergencies.length > 0) {
    emergencyResolved = true;
  }

  // Astronauts
  const mappedAstronauts = (astronauts || []).map((a, i) => {
    let statusLabel = 'Healthy';
    if (a.health < 40 || a.health_status === 'critical') statusLabel = 'Critical';
    else if (a.health < 80 || a.health_status === 'warning' || a.health_status === 'stable') statusLabel = 'Watch Out';
    return {
      id: a.id || i + 1,
      name: a.name || `Astronaut ${i + 1}`,
      status: statusLabel,
      heartRate: a.heart_rate || (i === 2 ? 95 : 72),
      o2sat: a.oxygen_saturation || 98,
      temp: a.body_temperature || 36.5,
      health: a.health
    };
  });

  // Calculate score (0-100)
  const resources = {
    oxygen: Math.round(backendMission.oxygen ?? 100),
    water: Math.round(backendMission.water ?? 100),
    food: Math.round(backendMission.food ?? 100),
    energy: Math.round(backendMission.energy ?? 100),
    fuel: Math.round(backendMission.fuel ?? 100),
  };
  const avgRes = (resources.oxygen + resources.water + resources.food + resources.energy + resources.fuel) / 5;
  const score = Math.round(Math.min(100, Math.max(0, 0.6 * avgRes + 0.4 * (backendMission.astronaut_health ?? 100))));

  // Map history events to frontend events
  const events = (historyEvents || []).map((e) => {
    let type = 'info';
    if (e.type === 'action_executed' || e.event_type === 'action_executed') type = 'success';
    else if (e.type?.includes('emergency') || e.event_type?.includes('emergency')) type = 'critical';
    else if (e.type === 'mission_completed' || e.event_type === 'mission_completed') type = 'success';
    return {
      id: e.id,
      type,
      message: e.message,
      day: e.mission_day || backendMission.current_day || 1,
      time: e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '12:00',
      active: false
    };
  });

  return {
    missionId: backendMission.id,
    missionName: backendMission.name,
    destination: backendMission.destination ? backendMission.destination.charAt(0).toUpperCase() + backendMission.destination.slice(1) : 'Mars',
    astronautCount: backendMission.astronaut_count,
    duration: backendMission.duration,
    difficulty: backendMission.difficulty ? backendMission.difficulty.charAt(0).toUpperCase() + backendMission.difficulty.slice(1) : 'Medium',
    currentDay: backendMission.current_day || 1,
    progress: Math.round(backendMission.progress || 0),
    score,
    missionStatus,
    isActive: backendMission.status === 'active',
    isComplete: backendMission.status === 'completed' || backendMission.status === 'failed',
    resources,
    astronauts: mappedAstronauts.length > 0 ? mappedAstronauts : [
      { id: 1, name: 'Alex Carter', status: 'Healthy', heartRate: 72, o2sat: 98, temp: 36.6 },
      { id: 2, name: 'Sarah Mitchell', status: 'Healthy', heartRate: 68, o2sat: 99, temp: 36.5 },
      { id: 3, name: 'David Kim', status: 'Watch Out', heartRate: 95, o2sat: 95, temp: 37.1 }
    ],
    activeEmergency,
    emergencyResolved,
    events: events.length > 0 ? events.reverse().slice(0, 6) : [
      { id: 1, type: 'info', message: 'Mission running nominal.', day: backendMission.current_day || 1, time: '12:00' }
    ]
  };
}
