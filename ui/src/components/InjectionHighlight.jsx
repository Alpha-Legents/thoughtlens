import { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Info, AlertCircle, Eye } from 'lucide-react';

const confidenceColors = (confidence) => {
  if (confidence >= 0.9) return {
    bg: 'bg-red-900/30',
    text: 'text-red-300',
    border: 'border-red-400',
    icon: <AlertCircle className="w-4 h-4" />
  };

  if (confidence >= 0.7) return {
    bg: 'bg-orange-900/30',
    text: 'text-orange-300',
    border: 'border-orange-400',
    icon: <AlertTriangle className="w-4 h-4" />
  };

  if (confidence >= 0.5) return {
    bg: 'bg-amber-900/30',
    text: 'text-amber-300',
    border: 'border-amber-400',
    icon: <AlertTriangle className="w-4 h-4" />
  };

  return {
    bg: 'bg-blue-900/30',
    text: 'text-blue-300',
    border: 'border-blue-400',
    icon: <Info className="w-4 h-4" />
  };
};

const InjectionHighlight = ({ threat, events, onThreatClick }) => {
  const [selectedThreat, setSelectedThreat] = useState(null);
  const [highlightedText, setHighlightedText] = useState('');
  const [animationStage, setAnimationStage] = useState(0);

  useEffect(() => {
    if (threat) {
      setSelectedThreat(threat);
      processThreatText(threat);
      animateHighlight();
    }
  }, [threat]);

  const animateHighlight = () => {
    let stage = 0;

    const animate = () => {
      stage = (stage + 1) % 3;
      setAnimationStage(stage);

      if (stage > 0) {
        setTimeout(animate, 200);
      }
    };

    setTimeout(animate, 100);
  };

  const processThreatText = (threatEvent) => {
    if (!threatEvent?.content) {
      setHighlightedText('No threat content available');
      return;
    }

    const text = threatEvent.content;
    const start = threatEvent.start || 0;
    const end = threatEvent.end || text.length;
    const confidence = threatEvent.confidence || 0;

    // Extract the problematic portion
    const beforeText = text.slice(0, Math.max(0, start));
    const highlighted = text.slice(start, end);
    const afterText = text.slice(end);

    const colorConfig = confidenceColors(confidence);

    setHighlightedText(
      <div className="font-mono text-sm">
        <span className="text-gray-400">{beforeText}</span>
        <span
          className={`px-1 rounded transition-all duration-600 ${colorConfig.bg} ${colorConfig.text} font-bold animate-fade-in`}
          style={{
            animationDelay: `${animationStage * 200}ms`
          }}
        >
          {highlighted}
        </span>
        <span className="text-gray-400">{afterText}</span>
      </div>
    );
  };

  const recentThreats = events.filter(e =>
    ['SCAN_THREAT', 'DEVIATION_THREAT'].includes(e.type)
  ).slice(-5);

  if (!selectedThreat && recentThreats.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="flex flex-col items-center gap-2">
          <Shield className="w-8 h-8 text-gray-600" />
          <p className="text-sm">No threats detected</p>
          <p className="text-xs text-gray-600">Events are clean</p>
        </div>
      </div>
    );
  }

  const activeThreat = selectedThreat || recentThreats[0];
  const colorConfig = confidenceColors(activeThreat?.confidence || 0);

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-red-950/40 via-purple-950/30 to-black/70 border-b border-red-500/30 backdrop-blur-xl">
      {/* Header */}
      <div className="p-4 border-b border-red-500/30 bg-gradient-to-r from-red-900/40 via-purple-900/30 to-pink-900/20 backdrop-blur-lg">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Eye className="w-5 h-5 text-red-400 drop-shadow-lg animate-pulse" />
            <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-400 rounded-full animate-ping"></div>
          </div>
          <h3 className="text-sm font-bold bg-gradient-to-r from-red-300 to-purple-300 bg-clip-text text-transparent">
            Threat Analysis
          </h3>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Current Threat Highlight */}
        <div className={`p-5 rounded-xl border ${colorConfig.border} ${colorConfig.bg} backdrop-blur-md shadow-lg transition-all duration-600 ${
          activeThreat?.severity === 'CRITICAL' ? 'animate-pulse shadow-red-500/40' : ''
        }`}>
          <div className="flex items-center gap-3 mb-3">
            <div className="p-1.5 rounded-full bg-red-500/20">
              {colorConfig.icon}
            </div>
            <span className={`text-sm font-bold ${colorConfig.text}`}>
              ⚠️ {activeThreat?.type?.replace('_', ' ').toUpperCase()} Detected
            </span>
          </div>

          <div className="text-xs text-gray-300 mb-3 bg-slate-800/30 p-3 rounded-lg border border-slate-700/50">
            <span className="font-bold text-cyan-300">Reason:</span> {activeThreat?.reason || 'Potential security threat'}
          </div>

          {activeThreat?.confidence && (
            <div className="text-xs text-gray-300 mb-4">
              <span className="font-bold text-red-400">Confidence:</span>
              <span className="bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent font-bold text-sm ml-1">
                {Math.round(activeThreat.confidence * 100)}%
              </span>
            </div>
          )}

          <div className="space-y-3">
            <div className="text-xs font-bold text-cyan-300 flex items-center gap-2">
              <div className="w-1 h-4 bg-cyan-400 rounded-full"></div>
              Problematic Text:
            </div>
            <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700/50 backdrop-blur-sm shadow-inner">
              <div className="font-mono text-sm leading-relaxed bg-gray-900/30 p-2 rounded-lg">
                {highlightedText}
              </div>
            </div>
          </div>

          {activeThreat?.position && (
            <div className="text-2xs text-red-400 mt-3 bg-red-900/30 px-2 py-1 rounded border border-red-500/30">
              📍 Position: {activeThreat.position}
            </div>
          )}
        </div>

        {/* Recent Threats List */}
        {recentThreats.length > 1 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-300 mb-2">Recent Threats</h4>
            <div className="space-y-2">
              {recentThreats.map((threat, index) => (
                <div
                  key={`${threat.timestamp}-${index}`}
                  onClick={() => {
                    setSelectedThreat(threat);
                    processThreatText(threat);
                    if (onThreatClick) onThreatClick(threat);
                  }}
                  className={`p-3 rounded border cursor-pointer transition-all duration-200 ${
                    threat.id === activeThreat?.id
                      ? 'border-blue-400 bg-blue-900/20'
                      : 'border-gray-700 bg-gray-800 hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-300">
                      {threat.type?.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-gray-500">
                      {Math.round(threat.confidence * 100)}%
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1 line-clamp-2">
                    {threat.reason}
                  </div>
                  <time className="text-2xs text-gray-500">
                    {new Date(threat.timestamp).toLocaleTimeString()}
                  </time>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Static analysis badges for empty state */}
      {recentThreats.length === 0 && (
        <div className="p-4 bg-gray-850">
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Static Analysis Options</div>
            <div className="grid grid-cols-2 gap-2 text-2xs">
              <button className="bg-gray-700 text-gray-300 px-2 py-1 rounded cursor-not-allowed">
                Unicode Scan
              </button>
              <button className="bg-gray-700 text-gray-300 px-2 py-1 rounded cursor-not-allowed">
                EXIF Scan
              </button>
              <button className="bg-gray-700 text-gray-300 px-2 py-1 rounded cursor-not-allowed">
                B64 Scan
              </button>
              <button className="bg-gray-700 text-gray-300 px-2 py-1 rounded cursor-not-allowed">
                Emoji Scan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InjectionHighlight;
