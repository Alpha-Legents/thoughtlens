import { useState } from 'react';
import { Play, Square, Eye, Shield, X } from 'lucide-react';

const ControlPanel = ({ sessionId, isPaused, events = [] }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [explanation, setExplanation] = useState(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  const hasCriticalEvents = events.filter(e => e.severity === 'CRITICAL').length > 0;
  const lastEvent = events[events.length - 1];

  const handleAction = async (action) => {
    if (!sessionId) return;

    setIsLoading(true);
    try {
      const response = await fetch(`/api/control/${action}/${sessionId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        console.error(`Failed to ${action} session`);
      }
    } catch (error) {
      console.error(`Error executing ${action}:`, error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClaudeExplanation = async () => {
    if (!sessionId || !hasCriticalEvents) return;

    setLoadingExplanation(true);
    try {
      const body = {
        model: "claude-sonnet-4-20250514",
        messages: [
          {
            role: "user",
            content: `Analyze this security threat in context. Here's the event data:\n\n${JSON.stringify(events.slice(-10), null, 2)}\n\nExplain:\n1. What specific threat was detected\n2. How the threat works\n3. Potential impact\n4. Mitigation steps\n\nKeep the explanation technical but clear.`
          }
        ],
        max_tokens: 500
      };

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': import.meta.env.VITE_ANTHROPIC_API_KEY || '',
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const data = await response.json();
        if (data.content && data.content[0]) {
          setExplanation({
            text: data.content[0].text,
            timestamp: new Date().toISOString()
          });
        }
      } else {
        // Fallback explanation
        setExplanation({
          text: `This appears to be a security threat based on detected deviations.
Please review the threat details in the main stream and consider implementing manual review of:
- File access patterns
- API call destinations
- Content of flagged items

Current severity: ${lastEvent?.severity}`,
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      setExplanation({
        text: `Unable to connect to AI explanation service. Please review the threat details manually.
\nKey findings:\n- Threat detected: ${lastEvent?.reason || 'Unknown'}\n- Severity: ${lastEvent?.severity || 'Unknown'}\n- Action required: Manual review recommended`,
        timestamp: new Date().toISOString()
      });
    } finally {
      setLoadingExplanation(false);
    }
  };

  const getThreatStats = () => {
    const stats = {
      clean: 0,
      info: 0,
      warn: 0,
      critical: 0
    };

    events.forEach(event => {
      if (event.severity) {
        stats[event.severity.toLowerCase()]++;
      }
    });

    return stats;
  };

  const stats = getThreatStats();

  if (!sessionId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="flex flex-col items-center gap-2 text-center">
          <Shield className="w-8 h-8 text-gray-600" />
          <p className="text-sm">No session selected</p>
          <p className="text-xs text-gray-600">Select a session to enable controls</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-purple-950/40 via-gray-900/50 to-black/80 border-l border-purple-500/30 backdrop-blur-xl">
      {/* Header */}
      <div className="p-4 border-b border-purple-500/30 bg-gradient-to-r from-purple-900/40 via-indigo-900/30 to-pink-900/20 backdrop-blur-lg">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Shield className="w-5 h-5 text-cyan-400 animate-pulse drop-shadow-lg" />
            <div className="absolute -top-1 -right-1 w-2 h-2 bg-cyan-400 rounded-full animate-ping"></div>
          </div>
          <h3 className="text-sm font-bold bg-gradient-to-r from-cyan-300 to-purple-300 bg-clip-text text-transparent">
            Control Center
          </h3>
        </div>
        <p className="text-xs text-cyan-400/80 font-mono mt-2 bg-cyan-500/10 px-2 py-1 rounded-full border border-cyan-500/30">
          {sessionId?.slice(-8) || 'NO_SESSION'}
        </p>
      </div>

      {/* Controls */}
      <div className="p-4 space-y-3">
        {/* Main Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => handleAction('resume')}
            disabled={!isPaused || isLoading}
            className={`py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-sm font-bold ${
              isPaused
                ? 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white shadow-lg shadow-green-500/30 hover:shadow-green-500/50 transform hover:scale-105'
                : 'bg-gray-700/50 text-gray-400 cursor-not-allowed border border-gray-600/50'
            }`}
          >
            <Play className="w-4 h-4" />
            Resume
          </button>

          <button
            onClick={() => handleAction('kill')}
            disabled={isLoading}
            className={`py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-sm font-bold ${
              isLoading
                ? 'bg-gray-700/50 text-gray-400 cursor-not-allowed border border-gray-600/50'
                : 'bg-gradient-to-r from-red-500 to-pink-600 hover:from-red-600 hover:to-pink-700 text-white shadow-lg shadow-red-500/30 hover:shadow-red-500/50 transform hover:scale-105'
            }`}
          >
            <Square className="w-4 h-4" />
            Kill
          </button>
        </div>
      </div>

      {/* Threat Analysis */}
      <div className="p-4 space-y-6">
        <div className="grid grid-cols-2 gap-4 text-center bg-gray-800/30 p-4 rounded-xl backdrop-blur-sm border border-gray-700/50">
          <div className="bg-green-900/30 border border-green-500/30 rounded-lg p-3">
            <div className="text-2xl font-bold text-green-400">{stats.clean}</div>
            <div className="text-xs text-green-300/70">Clean</div>
          </div>
          <div className="bg-blue-900/30 border border-blue-500/30 rounded-lg p-3">
            <div className="text-2xl font-bold text-blue-400">{stats.info}</div>
            <div className="text-xs text-blue-300/70">Info</div>
          </div>
          <div className="bg-amber-900/30 border border-amber-500/30 rounded-lg p-3">
            <div className="text-2xl font-bold text-amber-400">{stats.warn}</div>
            <div className="text-xs text-amber-300/70">Warning</div>
          </div>
          <div className={`${stats.critical > 0 ? 'bg-red-900/40 border-red-500/40' : 'bg-red-900/20 border-red-500/30'} border rounded-lg p-3 ${stats.critical > 0 ? 'animate-pulse' : ''}`}>
            <div className={`text-2xl font-bold ${stats.critical > 0 ? 'text-red-400 animate-pulse' : 'text-red-400'}`}>
              {stats.critical}
            </div>
            <div className="text-xs text-red-300/70">Critical</div>
          </div>
        </div>

        {/* Security Progress */}
        <div className="space-y-3 bg-slate-800/30 p-4 rounded-xl backdrop-blur-sm border border-slate-700/50">
          <div className="text-xs font-bold text-cyan-300 flex items-center justify-between">
            <span>Security Status</span>
            <span className="bg-cyan-400/20 px-2 py-1 rounded-full text-cyan-300">{events.length} events</span>
          </div>
          <div className="w-full bg-slate-700/50 rounded-full h-3 overflow-hidden border border-slate-600/50">
            <div
              className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r ${
                events.length > 0
                  ? (hasCriticalEvents ? 'from-red-500 via-pink-500 to-orange-500 animate-pulse' : 'from-green-500 via-emerald-500 to-teal-500')
                  : 'from-gray-600 to-gray-700'
              }`}
              style={{
                width: `${Math.min((events.length / 100) * 100, 100)}%`
              }}
            />
          </div>
          <div className="text-xs text-cyan-400/80 text-center flex items-center justify-center gap-2">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
            {events.length} events processed
          </div>
        </div>
      </div>

      {/* Threat Explanation AI */}
      {hasCriticalEvents && (
        <div className="p-4 border-t border-gray-750">
          <button
            onClick={handleClaudeExplanation}
            disabled={loadingExplanation || !hasCriticalEvents}
            className="w-full py-2 px-3 rounded transition-all flex items-center justify-center gap-2 text-sm font-medium bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50"
          >
            {loadingExplanation ? (
              <>
                <div className="w-3 h-3 border-2 border-white/30 border-l-white rounded-full animate-spin" />
                🧠 Analyzing...
              </>
            ) : (
              <>
                <Eye className="w-3 h-3" />
                🧠 AI Explain Threat
              </>
            )}
          </button>
        </div>
      )}

      {/* Explanation Panel */}
      {explanation && (
        <div className="flex-1 p-4 border-t border-gray-750 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-semibold text-gray-300">AI Analysis</h4>
            <button
              onClick={() => setExplanation(null)}
              className="text-gray-500 hover:text-gray-300"
            >
              <X className="w-3 h-3" />
            </button>
          </div>

          <div className="text-sm text-gray-300 whitespace-pre-wrap bg-gray-800 p-3 rounded">
            {explanation.text}
          </div>

          <div className="text-xs text-gray-500 mt-2">
            Generated: {new Date(explanation.timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}

      {/* Status Messages */}
      <div className="p-3 border-t border-gray-750">
        {lastEvent && (
          <div className="text-xs text-gray-400 text-center">
            Latest: {lastEvent.type.replace('_', ' ')}
          </div>
        )}

        {isLoading && (
          <div className="text-xs text-amber-300 text-center animate-pulse">
            Processing...
          </div>
        )}

        {!isLoading && !lastEvent && (
          <div className="text-xs text-gray-500 text-center">
            Ready
          </div>
        )}
      </div>
    </div>
  );
};

export default ControlPanel;
