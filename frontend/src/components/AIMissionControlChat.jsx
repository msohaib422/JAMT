import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, ChevronDown, ChevronUp, CheckCircle2, BookOpen, Sparkles, Loader2 } from 'lucide-react';
import { useMission } from '../contexts/MissionContext';
import { searchNASAKnowledge } from '../data/nasaKnowledge';
import * as api from '../services/api';

function generateAIResponse(userMessage, state) {
  const msg = userMessage.toLowerCase();
  const { resources, currentDay, duration, astronauts, activeEmergency, emergencyResolved } = state;
  const daysLeft = duration - currentDay;

  let content = '';
  let tools = ['get_mission_status', 'calculate_resource_consumption'];
  let recommendedAction = null;
  let nasaCitation = null;

  const nasaResults = searchNASAKnowledge(msg);

  if (msg.includes('oxygen') || msg.includes('o2') || msg.includes('air') || msg.includes('breath')) {
    const daysOfO2 = Math.round(resources.oxygen / 2);
    content = `Commander, oxygen is at ${resources.oxygen}% and decreasing faster than normal due to the detected leakage. I recommend activating the backup oxygen system immediately. This should stabilize levels while we investigate the source of the leak.`;
    tools.push('search_nasa_knowledge');
    if (activeEmergency === 'oxygen_leak' && !emergencyResolved) {
      recommendedAction = { label: 'Activate Backup Oxygen', actionId: 'activate_backup_o2', emergencyId: 'oxygen_leak' };
    }
    if (nasaResults.length > 0) {
      nasaCitation = {
        title: nasaResults[0].title,
        source: nasaResults[0].source,
        content: nasaResults[0].content.substring(0, 200) + '...'
      };
    }
  } else if (msg.includes('water') || msg.includes('hydrat')) {
    const daysOfWater = Math.round(resources.water / 2);
    content = `Water reserves are currently at ${resources.water}%. With ${state.astronautCount} crew members consuming ~2.5L/day each, you have roughly ${daysOfWater} days of water remaining. All ECLSS filtration units are operating nominal.`;
    tools.push('search_nasa_knowledge');
    if (nasaResults.length > 0) nasaCitation = { title: nasaResults[0].title, source: nasaResults[0].source, content: nasaResults[0].content.substring(0, 200) + '...' };
  } else if (msg.includes('energy') || msg.includes('power') || msg.includes('electric') || msg.includes('solar')) {
    content = `Energy reserves are at ${resources.energy}%. Main solar array efficiency on ${state.destination} is steady. ${resources.energy < 30 ? 'CRITICAL: Load shedding advised immediately!' : 'Energy levels are sufficient for current life support operations.'}`;
    tools.push('search_nasa_knowledge');
    if (activeEmergency === 'power_failure' && !emergencyResolved) {
      recommendedAction = { label: 'Switch to Backup Fuel Cells', actionId: 'backup_fuel_cells', emergencyId: 'power_failure' };
    }
    if (nasaResults.length > 0) nasaCitation = { title: nasaResults[0].title, source: nasaResults[0].source, content: nasaResults[0].content.substring(0, 200) + '...' };
  } else if (msg.includes('health') || msg.includes('crew') || msg.includes('astronaut') || msg.includes('david')) {
    const healthSummary = astronauts.map(a => `${a.name}: ${a.status} (${a.heartRate} bpm)`).join('; ');
    content = `Crew health telemetry: ${healthSummary}. ${astronauts.some(a => a.status !== 'Healthy') ? 'David Kim has elevated heart rate due to environmental stress. Stabilizing cabin pressure will normalize his vitals.' : 'All crew members are in good physical condition.'}`;
  } else if (msg.includes('radiation') || msg.includes('storm')) {
    content = `Solar telemetry indicates normal cosmic background levels. Polyethylene storm shelters are prepped if a Solar Particle Event is detected.`;
    tools.push('search_nasa_knowledge');
    if (activeEmergency === 'solar_storm' && !emergencyResolved) {
      content = `⚠️ CRITICAL: Solar radiation storm incoming! Direct all crew to storm shelter immediately!`;
      recommendedAction = { label: 'Move Crew to Storm Shelter', actionId: 'storm_shelter', emergencyId: 'solar_storm' };
    }
    if (nasaResults.length > 0) nasaCitation = { title: nasaResults[0].title, source: nasaResults[0].source, content: nasaResults[0].content.substring(0, 200) + '...' };
  } else {
    content = `Commander, I have run diagnostics across all habitat systems. Oxygen: ${resources.oxygen}%, Water: ${resources.water}%, Energy: ${resources.energy}%. Mission status is ${state.missionStatus}. How can I assist your command decisions?`;
    tools.push('search_nasa_knowledge');
    if (nasaResults.length > 0) nasaCitation = { title: nasaResults[0].title, source: nasaResults[0].source, content: nasaResults[0].content.substring(0, 200) + '...' };
  }

  return { content, tools, recommendedAction, nasaCitation };
}

export default function AIMissionControlChat() {
  const { state, sendChat, aiRespond, executeAction } = useMission();
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingSteps, setProcessingSteps] = useState([]);
  const [expandedCitations, setExpandedCitations] = useState({});
  const chatEndRef = useRef(null);
  const prevPendingRef = useRef(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.chatMessages, processingSteps]);

  useEffect(() => {
    if (state._pendingAI && !prevPendingRef.current) {
      setIsProcessing(true);
      const steps = [
        'get_mission_status',
        'calculate_resource_consumption',
        'search_nasa_knowledge'
      ];

      setProcessingSteps([steps[0]]);
      const t1 = setTimeout(() => setProcessingSteps([steps[0], steps[1]]), 400);
      const t2 = setTimeout(() => setProcessingSteps([steps[0], steps[1], steps[2]]), 700);
      const t3 = setTimeout(async () => {
        const lastUserMsg = [...state.chatMessages].reverse().find(m => m.role === 'user');
        if (lastUserMsg) {
          let responsePayload = null;
          try {
            const chatRes = await api.agentChat(state.missionId, lastUserMsg.content);
            if (chatRes && chatRes.response) {
              const tools = (chatRes.tools_used || []).map(t => (typeof t === 'string' ? t : (t.tool || t.label || 'nasa_tool')));
              let nasaCitation = null;
              if (chatRes.sources && chatRes.sources.length > 0) {
                nasaCitation = {
                  title: chatRes.sources[0].title || 'NASA Research Publication',
                  source: chatRes.sources[0].link || `NTRS ID: ${chatRes.sources[0].ntrs_id || '20210024855'}`,
                  content: chatRes.sources[0].excerpt || chatRes.sources[0].content || 'Official NASA Technical Reports Server documented findings.'
                };
              }
              let recommendedAction = null;
              if (chatRes.suggested_actions && chatRes.suggested_actions.length > 0) {
                const act = chatRes.suggested_actions[0];
                recommendedAction = {
                  label: act.label || act.action || 'Execute Action',
                  actionId: act.action || 'repair',
                  emergencyId: state.activeEmergency || 'oxygen_leak'
                };
              } else if (state.activeEmergency && !state.emergencyResolved) {
                recommendedAction = {
                  label: 'Activate Backup Oxygen',
                  actionId: 'activate_backup_o2',
                  emergencyId: 'oxygen_leak'
                };
              }
              responsePayload = {
                content: chatRes.response,
                tools: tools.length > 0 ? tools : ['get_mission_status', 'calculate_resource_consumption', 'search_nasa_knowledge'],
                recommendedAction,
                nasaCitation
              };
            }
          } catch (err) {
            console.warn('Backend AI chat error, using local RAG:', err);
          }

          if (!responsePayload) {
            responsePayload = generateAIResponse(lastUserMsg.content, state);
          }
          aiRespond(responsePayload);
        }
        setIsProcessing(false);
        setProcessingSteps([]);
      }, 1000);

      return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
    }
    prevPendingRef.current = state._pendingAI;
  }, [state._pendingAI]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    sendChat(trimmed);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleCitation = (msgId) => {
    setExpandedCitations(prev => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="rounded-2xl border border-blue-500/25 bg-[#0B162C]/90 backdrop-blur-md shadow-2xl flex flex-col h-full min-h-[580px] lg:min-h-[640px] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-blue-500/15 bg-[#071329]/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600/25 border border-blue-500/30 flex items-center justify-center shadow-inner">
            <Bot className="w-4 h-4 text-cyan-400" />
          </div>
          <span className="font-bold text-white text-sm sm:text-base tracking-tight">
            AI Mission Control
          </span>
        </div>
        <div className="bg-[#052818]/80 border border-emerald-500/40 rounded-full px-2.5 py-0.5 flex items-center gap-1.5 shadow-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-emerald-400 text-xs font-semibold">Online</span>
        </div>
      </div>

      {/* Chat Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {state.chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} gap-2.5`}
          >
            {/* Robot Avatar on left for assistant */}
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-[#0A1A38] border border-cyan-500/40 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md">
                <Bot className="w-4 h-4 text-cyan-400" />
              </div>
            )}

            {/* Message Bubble Container */}
            <div
              className={`max-w-[88%] ${
                msg.role === 'user'
                  ? 'bg-blue-600/30 border border-blue-500/40 text-white rounded-2xl rounded-tr-sm p-3.5 shadow-md'
                  : `bg-[#0D1B36]/90 border border-blue-500/25 rounded-2xl rounded-tl-sm p-3.5 shadow-md ${
                      msg.isEducational ? 'border-l-4 border-l-amber-400' : ''
                    }`
              }`}
            >
              {msg.isEducational && (
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-xs font-bold text-amber-400">Educational Feedback</span>
                </div>
              )}

              <p className="text-xs sm:text-sm text-slate-100 leading-relaxed whitespace-pre-line">
                {msg.content}
              </p>

              <p className="text-[10px] text-slate-400/80 mt-1.5 font-medium">
                {msg.timestamp}
              </p>

              {/* Tool Execution Badges */}
              {msg.tools && msg.tools.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2.5 pt-2 border-t border-blue-500/10">
                  {msg.tools.map((tool, i) => (
                    <span
                      key={i}
                      className="bg-[#08152B] border border-blue-500/20 text-cyan-300 rounded-lg px-2 py-0.5 text-[11px] font-mono flex items-center gap-1 shadow-sm"
                    >
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      {tool}
                    </span>
                  ))}
                </div>
              )}

              {/* Interactive Recommended Action Box */}
              {msg.recommendedAction && (
                <div className="bg-[#07152E] border border-blue-500/30 rounded-xl p-3 mt-3 shadow-inner">
                  <div className="flex items-center gap-1.5 mb-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wide">
                      Recommended Action
                    </span>
                  </div>

                  <button
                    onClick={() => executeAction(msg.recommendedAction.emergencyId, msg.recommendedAction.actionId)}
                    className="w-full bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white rounded-xl py-2.5 px-4 font-semibold text-xs sm:text-sm flex items-center justify-between transition-all shadow-lg shadow-blue-500/30 cursor-pointer hover:scale-[1.01]"
                  >
                    <span>{msg.recommendedAction.label}</span>
                    <span className="text-base font-bold">›</span>
                  </button>
                </div>
              )}

              {/* Expandable NASA RAG Citation */}
              {msg.nasaCitation && (
                <div className="mt-2.5">
                  <button
                    onClick={() => toggleCitation(msg.id)}
                    className="flex items-center gap-1 text-cyan-400 text-xs font-medium hover:text-cyan-300 transition-colors cursor-pointer"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Based on NASA Research</span>
                    {expandedCitations[msg.id] ? (
                      <ChevronUp className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                  </button>

                  {expandedCitations[msg.id] && (
                    <div className="bg-[#050E21] border border-blue-500/20 rounded-xl p-3 mt-2 text-xs space-y-1">
                      <p className="font-bold text-cyan-300">{msg.nasaCitation.title}</p>
                      <p className="italic text-slate-400 text-[11px]">{msg.nasaCitation.source}</p>
                      <p className="text-slate-300 leading-relaxed text-[11px] mt-1">
                        {msg.nasaCitation.content}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Dynamic Tool Execution Processing Trace */}
        {isProcessing && (
          <div className="flex justify-start gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#0A1A38] border border-cyan-500/40 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-cyan-400 animate-pulse" />
            </div>
            <div className="bg-[#0D1B36] border border-blue-500/25 rounded-2xl p-3 space-y-1.5 shadow-md">
              {processingSteps.map((step, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-cyan-300 font-mono">
                  <Loader2 className="w-3 h-3 text-cyan-400 animate-spin" />
                  <span>🔄 Calling {step}()...</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Bottom Chat Input Bar */}
      <div className="p-3 sm:p-4 border-t border-blue-500/15 bg-[#071329]/80">
        <div className="flex items-center gap-2">
          <input
            id="ai-mission-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your mission..."
            className="bg-[#0A162D] border border-blue-500/25 rounded-xl px-3.5 py-2.5 flex-1 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400/60 transition-colors"
          />
          <button
            onClick={handleSend}
            aria-label="Send Message"
            className="w-10 h-10 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 flex items-center justify-center text-white shadow-lg shadow-blue-500/30 transition-all cursor-pointer flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
