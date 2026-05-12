import { memo } from 'react';
import { Play, Loader, AlertTriangle, CheckCircle, Zap } from 'lucide-react';

const statusIcons = {
  paused: AlertTriangle,
  running: Zap,
  completed: CheckCircle,
  error: AlertTriangle,
  starting: Loader
};

const statusColors = {
  paused: 'text-amber-500',
  running: 'text-green-500',
  completed: 'text-blue-500',
  error: 'text-red-500',
  starting: 'text-gray-500'
};

const SessionStatus = memo(({ status }) => {
  const Icon = statusIcons[status] || Zap;
  const color = statusColors[status] || 'text-gray-500';

  return (
    <Icon className={`w-3 h-3 ${color}`} />
  );
});

SessionStatus.displayName = 'SessionStatus';

const SessionBar = ({
  sessions = [],
  loading = false,
  selectedSession,
  onSelect
}) => {
  const colors = {
    clean: 'bg-gray-800 hover:bg-gray-700',
    warn: 'bg-amber-900/30 hover:bg-amber-800/40',
    critical: 'bg-red-900/30 hover:bg-red-800/40',
  };

  const selectedColor = {
    clean: 'bg-blue-600/20 border-blue-400',
    warn: 'bg-amber-600/20 border-amber-400',
    critical: 'bg-red-600/20 border-red-400',
  };

  const getSessionColor = (session) => {
    const severity = session.lastSeverity || 'clean';
    const isSelected = session.id === selectedSession;

    if (isSelected) {
      return selectedColor[severity] || selectedColor.clean;
    }
    return colors[severity] || colors.clean;
  };

  const formatTimeAgo = (timestamp) => {
    if (!timestamp) return 'Unknown';

    const now = Date.now();
    const then = new Date(timestamp).getTime();
    const diff = Math.floor((now - then) / 1000);

    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    return `${Math.floor(diff / 3600)}h`;
  };

  const getHighlights = (session) => {
    const marks = [];

    if (session.criticalCount > 0) marks.push('🚨');
    if (session.warnCount > 0) marks.push('⚠️');
    if (session.paused) marks.push('⏸️');

    return marks.slice(0, 3).join(' ');
  };

  if (loading) {
    return (
      <div className="p-4 space-y-3">
        <div className="text-sm font-semibold text-gray-200 border-b border-gray-750 pb-2">
          Active Sessions
        </div>
        <div className="flex items-center gap-2 text-gray-400">
          <Loader className="w-4 h-4 animate-spin" />
          Loading...
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center">
        <div className="text-sm font-semibold text-gray-200 border-b border-gray-750 pb-2 mb-3">
          Active Sessions
        </div>
        <div className="flex flex-col items-center gap-3 py-6">
          <Play className="w-8 h-8 text-gray-500" />
          <p className="text-sm text-gray-400">No active sessions</p>
          <p className="text-xs text-gray-500">Connect clients to see sessions here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-slate-900/90 via-slate-800/80 to-gray-900/90 backdrop-blur-xl">
      <div className="p-4 border-b border-cyan-500/20 bg-gradient-to-r from-cyan-900/20 via-blue-900/20 to-purple-900/20 backdrop-blur-md">
        <h3 className="text-sm font-bold text-slate-100 flex items-center justify-between">
          <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            Active Sessions
          </span>
          <span className="text-xs text-cyan-400 font-mono bg-cyan-500/20 px-2 py-1 rounded-full border border-cyan-500/30">
            {sessions.length}
          </span>
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 p-3">
        {sessions.map(session => (
          <div
            key={session.id}
            onClick={() => onSelect && onSelect(session.id)}
            className={`
              p-4 rounded-xl cursor-pointer transition-all duration-500 ease-in-out border backdrop-blur-md
              ${getSessionColor(session)}
              ${session.id === selectedSession
                ? 'bg-gradient-to-r from-cyan-500/30 via-blue-500/20 to-purple-500/30 border-cyan-400/60 ring-2 ring-cyan-400/40 ring-offset-2 ring-offset-slate-900 shadow-lg shadow-cyan-500/30'
                : 'bg-slate-800/40 border-slate-700/40 hover:bg-slate-700/60 hover:border-cyan-500/50 hover:shadow-lg hover:shadow-cyan-500/20'
              }
              group hover:transform hover:scale-[1.02] hover:translate-x-1
            `}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <SessionStatus status={session.status} />
                  <span className="text-sm font-semibold text-slate-200 truncate group-hover:text-slate-50">
                    {session.name || session.id.slice(-8)}
                  </span>
                </div>

                <div className="text-xs text-slate-400 font-mono">
                  {formatTimeAgo(session.created_at)} ago
                </div>
              </div>
            </div>

            {/* Session Stats */}
            <div className="mt-2 flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs">
                {session.criticalCount > 0 && (
                  <span className="text-red-400 font-medium">
                    {session.criticalCount}🚨
                  </span>
                )}

                {session.warnCount > 0 && (
                  <span className="text-amber-400 font-medium">
                    {session.warnCount}⚠️
                  </span>
                )}

                <span className="text-gray-500">
                  {session.eventCount || 0} events
                </span>
              </div>

              {/* High importance badge */}
              {getHighlights(session) && (
                <div className="text-2xs text-gray-500">
                  {getHighlights(session)}
                </div>
              )}
            </div>

            {/* Quick info */}
            <div className="mt-1 text-xs text-gray-500 group-hover:text-gray-400 transition-colors">
              Status: {session.status || 'unknown'}
              {session.paused && ' • Paused'}
            </div>
          </div>
        ))}
      </div>

      {/* Session Actions Footer */}
      <div className="p-4 border-t border-gray-750">
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="text-gray-400">
            <span className="font-semibold">Total:</span> {sessions.length}
          </div>
          <div className="text-gray-400">
            <span className="font-semibold">Active:</span> {
              sessions.filter(s => s.status === 'running').length
            }
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionBar;
