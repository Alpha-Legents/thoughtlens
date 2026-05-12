import { useState, useMemo } from 'react';
import { Download, Filter, Search, ChevronDown, ChevronUp, Clock, Shield } from 'lucide-react';

const AuditLog = ({ events, onClose, selectedSession }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [collapsed, setCollapsed] = useState(false);
  const [sortBy, setSortBy] = useState('timestamp');

  const filteredEvents = useMemo(() => {
    let filtered = events || [];

    if (searchTerm) {
      filtered = filtered.filter(event => {
        const JSONString = JSON.stringify(event).toLowerCase();
        return JSONString.includes(searchTerm.toLowerCase());
      });
    }

    if (severityFilter !== 'all') {
      filtered = filtered.filter(event =>
        event.severity?.toLowerCase() === severityFilter.toLowerCase()
      );
    }

    return filtered.sort((a, b) => {
      switch (sortBy) {
        case 'timestamp':
          return new Date(b.timestamp) - new Date(a.timestamp);
        case 'severity': {
          const severityOrder = { CRITICAL: 0, WARN: 1, INFO: 2, CLEAN: 3 };
          return (severityOrder[a.severity] || 4) - (severityOrder[b.severity] || 4);
        }
        case 'type':
          return (a.type || '').localeCompare(b.type || '');
        default:
          return 0;
      }
    });
  }, [events, searchTerm, severityFilter, sortBy]);

  const stats = useMemo(() => ({
    clean: filteredEvents.filter(e => e.severity === 'CLEAN').length,
    info: filteredEvents.filter(e => e.severity === 'INFO').length,
    warn: filteredEvents.filter(e => e.severity === 'WARN').length,
    critical: filteredEvents.filter(e => e.severity === 'CRITICAL').length
  }), [filteredEvents]);

  const exportToJSON = () => {
    const data = {
      sessionId: selectedSession,
      exportedAt: new Date().toISOString(),
      totalEvents: filteredEvents.length,
      summary: {
        clean: stats.clean,
        info: stats.info,
        warn: stats.warn,
        critical: stats.critical
      },
      events: filteredEvents
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${selectedSession || 'manual'}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown';
    return new Date(timestamp).toLocaleString();
  };

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
    CLEAN: 'bg-gray-100 text-gray-800',
    INFO: 'bg-blue-100 text-blue-800',
    WARN: 'bg-amber-100 text-amber-800',
    CRITICAL: 'bg-red-100 text-red-800'
  };

  const renderEventDetails = (event) => {
    const details = [];

    if (event.file_path) details.push({ label: 'File', value: event.file_path });
    if (event.api_url) details.push({ label: 'URL', value: event.api_url });
    if (event.shell_cmd) details.push({ label: 'Command', value: event.shell_cmd });
    if (event.tool_name && event.tool_name !== event.type) details.push({ label: 'Tool', value: event.tool_name });
    if (event.confidence) details.push({ label: 'Confidence', value: `${Math.round(event.confidence * 100)}%` });
    if (event.reason) details.push({ label: 'Reason', value: event.reason });
    if (event.duration) details.push({ label: 'Duration', value: `${event.duration}ms` });

    return details.map((detail, index) => (
      <div key={index} className="flex justify-between text-sm">
        <span className="text-gray-500">{detail.label}:</span>
        <span className="text-gray-300 font-mono max-w-64 truncate">{detail.value}</span>
      </div>
    ));
  };

  return (
    <div className="h-full flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="p-4 border-b border-gray-750 bg-gray-850">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Audit Log
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={exportToJSON}
              className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
              title="Export to JSON"
            >
              <Download className="w-3 h-3" />
            </button>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-200 transition-colors ml-2"
              title="Close"
            >
              ×
            </button>
          </div>
        </div>

        <div className="mt-3 space-y-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-500 pointer-events-none" />
            <input
              type="text"
              placeholder="Search events..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-7 pr-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm text-gray-300 placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2">
            <Filter className="w-3 h-3 text-gray-500" />

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
            >
              <option value="all">All Severity</option>
              <option value="CLEAN">Clean</option>
              <option value="INFO">Info</option>
              <option value="WARN">Warning</option>
              <option value="CRITICAL">Critical</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
            >
              <option value="timestamp">Time</option>
              <option value="severity">Severity</option>
              <option value="type">Type</option>
            </select>

            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1 text-gray-400 hover:text-gray-200 transition-colors ml-auto"
            >
              {collapsed ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
          <div className="text-center">
            <div className="text-gray-300 font-bold">{filteredEvents.length}</div>
            <div className="text-gray-500">Total</div>
          </div>
          <div className="text-center">
            <div className="text-green-400 font-bold">{stats.clean}</div>
            <div className="text-gray-500">Clean</div>
          </div>
          <div className="text-center">
            <div className="text-amber-400 font-bold">{stats.warn}</div>
            <div className="text-gray-500">Warn</div>
          </div>
          <div className="text-center">
            <div className="text-red-400 font-bold">{stats.critical}</div>
            <div className="text-gray-500">Critical</div>
          </div>
        </div>
      </div>

      {/* Event List */}
      <div className="flex-1 overflow-y-auto">
        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center">
            <Shield className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-sm text-gray-400">
              {searchTerm || severityFilter !== 'all' ? 'No events match your filters' : 'No events'}
            </p>
          </div>
        ) : (
          <div className="space-y-2 p-4">
            {filteredEvents.map((event, index) => (
              <div
                key={event.id || `${event.timestamp}-${index}`}
                className={`
                  p-3 rounded-lg transition-all duration-200
                  ${collapsed ? 'p-2' : 'hover:bg-gray-800'}
                  ${event.severity === 'CRITICAL' ? 'border-l-2 border-red-400' : ''}
                  ${event.severity === 'WARN' ? 'border-l-2 border-amber-400' : ''}
                `}
              >
                <div className="flex items-start gap-3">
                  <div className="text-xl min-w-0">
                    {iconMap[event.type] || '📄'}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-sm font-medium truncate ${event.severity === 'CRITICAL' ? 'text-red-400' : event.severity === 'WARN' ? 'text-amber-400' : 'text-gray-200'}`}>
                        {event.type?.replace('_', ' ').toLowerCase()}
                      </span>

                      <span className={`text-xs px-1.5 py-0.5 rounded ${severityColors[event.severity] || 'bg-gray-100 text-gray-800'}`}>
                        {event.severity}
                      </span>
                    </div>

                    <div className="text-xs text-gray-400 mb-1">
                      {formatTimestamp(event.timestamp)}
                    </div>

                    {!collapsed && (
                      <>
                        <div className="text-xs text-gray-300 mb-2 line-clamp-2">
                          {event.message || event.reason}
                        </div>

                        <div className="space-y-1">
                          {renderEventDetails(event)}
                        </div>
                      </>
                    )}
                  </div>

                  {!collapsed && (
                    <div className="text-2xs text-gray-500">
                      #{filteredEvents.length - index}
                    </div>
                  )}
                </div>

                {/* Expand/Collapse for detailed view */}
                <div
                  className={`transition-all duration-200 overflow-hidden ${
                    collapsed ? 'max-h-0 opacity-0' : 'max-h-96 opacity-100 mt-2'
                  }`}
                >
                  <div className="text-xs font-mono bg-gray-900 p-2 rounded text-gray-400 overflow-x-auto text-left">
                    {JSON.stringify(event, null, 2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditLog;
