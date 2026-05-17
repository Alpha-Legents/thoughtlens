import { useState } from 'react';

const SEV_COLOR = {
  CLEAN:    'var(--color-clean)',
  INFO:     'var(--color-info)',
  WARN:     'var(--color-warn)',
  CRITICAL: 'var(--color-critical)',
};

export default function AuditLog({ events, onClose, selectedSession }) {
  const [expanded, setExpanded] = useState(null);

  function exportJson() {
    const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `thoughtlens-audit-${selectedSession?.slice(-8) || 'session'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col h-full" style={{ background: 'var(--bg-surface)' }}>
      {/* Header */}
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <span>audit log — {events.length} events</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={exportJson}
            className="ctrl-btn"
            style={{
              background: 'var(--bg-overlay)',
              borderColor: 'var(--border-default)',
              color: 'var(--text-secondary)',
              padding: '3px 10px',
            }}
          >
            export json
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none',
              color: 'var(--text-muted)', cursor: 'pointer',
              fontSize: 14, lineHeight: 1,
              padding: '2px 4px',
            }}
            aria-label="Close audit log"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div style={{
            padding: 16, textAlign: 'center',
            color: 'var(--text-muted)', fontSize: 'var(--text-sm)',
          }}>
            no events recorded
          </div>
        ) : (
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontFamily: "'Fira Code', monospace",
            fontSize: 'var(--text-xs)',
          }}>
            <thead>
              <tr style={{ background: 'var(--bg-raised)', position: 'sticky', top: 0 }}>
                {['time', 'type', 'sev', 'message'].map(h => (
                  <th key={h} style={{
                    padding: '5px 10px',
                    textAlign: 'left',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    borderBottom: '1px solid var(--border-subtle)',
                    whiteSpace: 'nowrap',
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.map((e, i) => {
                const sev = (e.severity || 'CLEAN').toUpperCase();
                const isExp = expanded === i;
                return [
                  <tr
                    key={`row-${i}`}
                    onClick={() => setExpanded(isExp ? null : i)}
                    style={{
                      cursor: 'pointer',
                      background: isExp ? 'var(--bg-overlay)' : 'transparent',
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background 100ms ease-out',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                    onMouseLeave={e => e.currentTarget.style.background = isExp ? 'var(--bg-overlay)' : 'transparent'}
                  >
                    <td style={{ padding: '4px 10px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {new Date((e.timestamp || 0) * 1000).toLocaleTimeString('en-US', { hour12: false })}
                    </td>
                    <td style={{ padding: '4px 10px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {(e.type || '').replace(/_/g, ' ').toLowerCase()}
                    </td>
                    <td style={{ padding: '4px 10px', whiteSpace: 'nowrap' }}>
                      <span style={{ color: SEV_COLOR[sev] || 'var(--text-muted)', fontWeight: 600 }}>
                        {sev.slice(0, 4)}
                      </span>
                    </td>
                    <td style={{
                      padding: '4px 10px',
                      color: 'var(--text-secondary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: 240,
                    }}>
                      {e.message || '—'}
                    </td>
                  </tr>,
                  isExp && (
                    <tr key={`exp-${i}`}>
                      <td colSpan={4} style={{ padding: '6px 10px 10px', background: 'var(--bg-overlay)' }}>
                        <pre style={{
                          margin: 0,
                          fontSize: 'var(--text-xs)',
                          color: 'var(--text-secondary)',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
                          maxHeight: 200,
                          overflowY: 'auto',
                        }}>
                          {JSON.stringify(e, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  ),
                ];
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
