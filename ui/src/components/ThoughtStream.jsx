import { useEffect, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

const iconMap = {
  FILE_READ: '📄',
  FILE_WRITE: '✏️',
  API_CALL: '🌐',
  SHELL_CMD: '💻',
  TOOL_CALL: '🔧',
  REASONING: '💭',
  TEXT_CHUNK: '📝',
  SCAN_THREAT: '⚠️',
  DEVIATION_THREAT: '🚨',
  PAUSED: '⏸',
  LT_REVIEW: '🔍',
  KILLED: '☠️',
  COMPLETE: '✅',
  ERROR: '💥'
};

const severityColors = {
  CLEAN: 'text-gray-400',
  INFO: 'text-blue-400',
  WARN: 'text-amber-400',
  CRITICAL: 'text-red-400 animate-pulse'
};

const getSeverityBg = (severity) => {
  switch (severity) {
    case 'CLEAN': return 'bg-gray-800';
    case 'INFO': return 'bg-blue-900/30 border-l-4 border-blue-400';
    case 'WARN': return 'bg-amber-900/30 border-l-4 border-amber-400';
    case 'CRITICAL': return 'bg-red-900/30 border-l-4 border-red-400 animate-pulse';
    default: return 'bg-gray-800';
  }
};

const ThoughtStream = ({ events, isPaused, selectedSession }) => {
  const parentRef = useRef(null);
  const autoScrollRef = useRef(true);
  const lastEventCount = useRef(0);

  const virtualizer = useVirtualizer({
    count: events.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
    overscan: 10,
  });

  useEffect(() => {
    if (events.length > lastEventCount.current && autoScrollRef.current) {
      virtualizer.scrollToIndex(events.length - 1);
    }
    lastEventCount.current = events.length;
  }, [events, virtualizer]);

  useEffect(() => {
    const scrollElement = parentRef.current;

    const checkScroll = () => {
      if (!scrollElement) return;

      const { scrollTop, scrollHeight, clientHeight } = scrollElement;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 50;
      autoScrollRef.current = isAtBottom;
    };

    if (scrollElement) {
      scrollElement.addEventListener('scroll', checkScroll);
      return () => scrollElement.removeEventListener('scroll', checkScroll);
    }
  }, []);

  if (!selectedSession) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="text-gray-400 mb-2">🔍</div>
          <div className="text-gray-300">
            Select a session to view thought stream
          </div>
        </div>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="text-gray-400 mb-2">⏳</div>
          <div className="text-gray-300">
            Waiting for events...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-gradient-to-br from-slate-950/90 via-gray-900/80 to-black/70 border-r border-cyan-500/20 backdrop-blur-xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-cyan-500/20 bg-gradient-to-r from-cyan-900/30 via-blue-900/25 to-purple-900/20 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className={`w-3 h-3 rounded-full ${
              isPaused ? 'bg-amber-400' : 'bg-cyan-400'
            } animate-pulse shadow-lg shadow-cyan-400/50`} />
            <div className={`absolute inset-0 w-3 h-3 rounded-full ${
              isPaused ? 'bg-amber-400' : 'bg-cyan-400'
            } animate-ping opacity-75`} />
          </div>
          <span className="text-sm font-bold bg-gradient-to-r from-cyan-300 to-blue-300 bg-clip-text text-transparent tracking-wider">
            {isPaused ? '⚠️ PAUSED' : '🔴 LIVE'} • {events.length.toLocaleString()} events
          </span>
        </div>
        <div className={`text-xs font-bold px-3 py-1.5 rounded-full flex items-center gap-2 ${
          severityColors[events[events.length - 1]?.severity || 'CLEAN']
        }`}>
          <span className={`w-2 h-2 rounded-full ${
            events[events.length - 1]?.severity === 'CRITICAL' ? 'bg-red-400 animate-pulse' :
            events[events.length - 1]?.severity === 'WARN' ? 'bg-amber-400 animate-pulse' :
            'bg-cyan-400'
          }`}></span>
          {events[events.length - 1]?.severity || 'CLEAN'}
        </div>
      </div>

      {/* Virtualized event list */}
      <div
        ref={parentRef}
        className="flex-1 overflow-y-auto"
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualizer.getVirtualItems().map((virtualItem) => {
            const event = events[virtualItem.index];
            const isLast = virtualItem.index === events.length - 1;

            return (
              <div
                key={event.id || virtualItem.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualItem.size}px`,
                  transform: `translateY(${virtualItem.start}px)`,
                }}
                className={`px-4 py-3 transition-all duration-300 ${
                  isLast && !isPaused ? 'fade-in' : ''
                } ${getSeverityBg(event.severity)}`}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <div className="flex-shrink-0 text-xl">
                    {iconMap[event.type] || '📄'}
                  </div>

                  {/* Event details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm font-medium ${
                        severityColors[event.severity] || 'text-gray-400'
                      }`}>
                        {event.type.replace('_', ' ').toLowerCase()}
                      </span>
                      <time className="text-xs text-gray-500 ml-2">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </time>
                    </div>

                    {(event.message || event.reason) && (
                      <p className="text-sm text-gray-300 mb-1 line-clamp-2">
                        {event.message || event.reason}
                      </p>
                    )}

                    {event.file_path && (
                      <p className="text-xs text-gray-400 font-mono bg-gray-800 px-2 py-1 rounded mt-1">
                        → {event.file_path}
                      </p>
                    )}

                    {event.api_url && (
                      <p className="text-xs text-gray-400 font-mono bg-gray-800 px-2 py-1 rounded mt-1">
                        → {event.api_url}
                      </p>
                    )}

                    {event.shell_cmd && (
                      <p className="text-xs text-gray-400 font-mono bg-gray-800 px-2 py-1 rounded mt-1">
                        → {event.shell_cmd}
                      </p>
                    )}

                    {/* Deviation confidence */}
                    {event.confidence !== undefined && (
                      <div className="flex items-center gap-1 mt-1">
                        <div className="w-20 h-1 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-red-500 transition-all duration-300"
                            style={{ width: `${Math.min(event.confidence * 100, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400">
                          {Math.round(event.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Status indicator */}
                  {event.type === 'PAUSED' && (
                    <div className="flex items-center gap-1 px-2 py-1 bg-yellow-500/20 rounded text-xs text-yellow-300">
                      <span className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
                      Paused
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Virtualizer warning for large data sets */}
      {events.length > 1000 && (
        <div className="p-2 text-xs text-center text-gray-500 bg-gray-850">
          Showing {virtualizer.getVirtualItems().length} of {events.length} events (virtualized)
        </div>
      )}
    </div>
  );
};

export default ThoughtStream;
