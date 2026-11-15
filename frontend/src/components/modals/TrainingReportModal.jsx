import React, { useState, useEffect } from 'react';
import { X, Trophy, Star, Shield, Target, Calendar, Heart, Brain } from 'lucide-react';
import { useMission } from '../../contexts/MissionContext';
import * as api from '../../services/api';

export default function TrainingReportModal() {
  const { state, closeModal } = useMission();
  const [backendReport, setBackendReport] = useState(null);

  useEffect(() => {
    if (state.missionId) {
      api.getMissionReport(state.missionId)
        .then(res => setBackendReport(res))
        .catch(err => console.warn('Could not fetch backend report:', err));
    }
  }, [state.missionId]);

  const avgResources = Math.round(Object.values(state.resources).reduce((a, b) => a + b, 0) / 5);
  const healthyCount = state.astronauts.filter(a => a.status === 'Healthy').length;
  const emergenciesResolved = state.decisions.filter(d => d.resolved).length;
  const progressPct = Math.round((state.currentDay / state.duration) * 100);

  const displayScore = backendReport?.score != null ? Math.round(backendReport.score) : state.score;

  let grade, gradeEmoji, gradeColor;
  if (displayScore >= 90) { grade = 'Mission Commander'; gradeEmoji = '⭐'; gradeColor = 'text-yellow-400'; }
  else if (displayScore >= 75) { grade = 'Senior Astronaut'; gradeEmoji = '🎖️'; gradeColor = 'text-blue-400'; }
  else if (displayScore >= 60) { grade = 'Junior Astronaut'; gradeEmoji = '🚀'; gradeColor = 'text-green-400'; }
  else if (displayScore >= 40) { grade = 'Trainee'; gradeEmoji = '📚'; gradeColor = 'text-yellow-400'; }
  else { grade = 'Needs Retraining'; gradeEmoji = '🔄'; gradeColor = 'text-red-400'; }

  let scoreColor = displayScore >= 90 ? 'text-yellow-400' : displayScore >= 70 ? 'text-green-400' : displayScore >= 50 ? 'text-yellow-400' : 'text-red-400';

  let feedback = backendReport?.educational_feedback || backendReport?.feedback;
  if (!feedback) {
    if (displayScore >= 80) feedback = "Excellent performance, Commander! You demonstrated exceptional decision-making under pressure. Your resource management was efficient, and your emergency responses aligned with NASA protocols. You've shown the qualities needed for real space missions — calm analysis, decisive action, and crew safety prioritization.";
    else if (displayScore >= 60) feedback = "Good work, astronaut. You showed solid fundamentals in mission management and made mostly sound decisions during emergencies. To improve, focus on faster emergency response times and more efficient resource conservation. Review the NASA ECLSS protocols for deeper understanding of life support optimization.";
    else feedback = "There's room for improvement, trainee. Review the NASA training materials, especially the emergency response protocols and resource management guidelines. Focus on understanding the trade-offs of each decision and prioritize crew safety above all else. Practice makes perfect — try another mission!";
  }

  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4" onClick={closeModal}>
      <div className="bg-[#0B162C]/95 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-4 sm:p-6 w-[95vw] max-w-3xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-yellow-600/30 flex items-center justify-center">
              <Trophy className="w-4 h-4 text-yellow-400" />
            </div>
            <h2 className="font-semibold text-white text-lg">Training Results & Performance</h2>
          </div>
          <button onClick={closeModal} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Score Display */}
        <div className="text-center mb-8 py-6 bg-slate-900/30 rounded-2xl border border-slate-700/20">
          <div className="text-6xl font-bold font-orbitron mb-1">
            <span className={scoreColor}>{state.score}</span>
            <span className="text-2xl text-slate-400">/100</span>
          </div>
          <div className={`text-lg font-semibold ${gradeColor} mt-2`}>
            {gradeEmoji} {grade}
          </div>
          <div className="flex items-center justify-center gap-1 mt-2">
            {[1,2,3,4,5].map(i => (
              <Star key={i} className={`w-5 h-5 ${i <= Math.ceil(state.score/20) ? 'text-yellow-400 fill-yellow-400' : 'text-slate-700'}`} />
            ))}
          </div>
        </div>

        {/* Breakdown Cards */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              <span className="text-sm text-slate-400">Resource Conservation</span>
            </div>
            <div className="text-2xl font-bold text-white">{avgResources}%</div>
            <div className="w-full bg-white/5 rounded-full h-2 mt-2">
              <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full transition-all" style={{ width: `${avgResources}%` }} />
            </div>
          </div>
          <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-4 h-4 text-red-400" />
              <span className="text-sm text-slate-400">Emergency Response</span>
            </div>
            <div className="text-2xl font-bold text-white">{state.decisions.length} actions</div>
            <p className="text-xs text-slate-500 mt-1">{emergenciesResolved} emergencies fully resolved</p>
          </div>
          <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-orange-400" />
              <span className="text-sm text-slate-400">Mission Progress</span>
            </div>
            <div className="text-2xl font-bold text-white">Day {state.currentDay}/{state.duration}</div>
            <div className="w-full bg-white/5 rounded-full h-2 mt-2">
              <div className="bg-gradient-to-r from-orange-500 to-yellow-500 h-2 rounded-full" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
          <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Heart className="w-4 h-4 text-pink-400" />
              <span className="text-sm text-slate-400">Crew Health</span>
            </div>
            <div className="text-2xl font-bold text-white">{healthyCount}/{state.astronauts.length} Healthy</div>
            <p className="text-xs text-slate-500 mt-1">{state.astronauts.length - healthyCount > 0 ? `${state.astronauts.length - healthyCount} requiring attention` : 'All crew in good condition'}</p>
          </div>
        </div>

        {/* Decision History */}
        {state.decisions.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-white mb-3">Decision History</h3>
            <div className="bg-slate-900/30 rounded-xl border border-slate-700/20 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left px-4 py-2.5 text-slate-400 font-medium">Day</th>
                    <th className="text-left px-4 py-2.5 text-slate-400 font-medium">Emergency</th>
                    <th className="text-left px-4 py-2.5 text-slate-400 font-medium">Action</th>
                    <th className="text-left px-4 py-2.5 text-slate-400 font-medium">Impact</th>
                    <th className="text-left px-4 py-2.5 text-slate-400 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {state.decisions.map((d, i) => (
                    <tr key={i} className={i % 2 === 0 ? 'bg-slate-800/20' : ''}>
                      <td className="px-4 py-2 text-slate-300">{d.day}</td>
                      <td className="px-4 py-2 text-slate-300">{d.emergency}</td>
                      <td className="px-4 py-2 text-white font-medium">{d.action}</td>
                      <td className={`px-4 py-2 font-semibold ${d.scoreChange > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {d.scoreChange > 0 ? '+' : ''}{d.scoreChange}
                      </td>
                      <td className="px-4 py-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${d.resolved ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                          {d.resolved ? '✓ Resolved' : 'Partial'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* AI Instructor Feedback */}
        <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-semibold text-white">AI Instructor Feedback</span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">{feedback}</p>
        </div>
      </div>
    </div>
  );
}
