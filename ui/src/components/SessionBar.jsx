import { memo } from 'react';

const StatusDot = memo(({ status }) => {
  const style = {
    display: 'inline-block', width: 6, height: 6,
    borderRadius: '50%', flexShrink: 0,
  };
  const map = {
    active:   { background: '#00ff9d', boxShadow: '0 0 6px rgba(0,255,157,0.5)' },
    paused:   { background: '#ffb000', animation: 'blink 1.2s ease-in-out infinite' },
    killed:   { background: '#ff3333' },
    complete: { background: '#38bdf8' },
    resumed:  { background: '#00ff9d', boxShadow: '0 0 6px rgba(0,255,157,0.5)' },
  };
  return <span style={{ ...style, ...(map[status] || { background: '#334155' }) }} />;
});
StatusDot.displayName = 'StatusDot';

export default function SessionBar({ sessions, loading, selectedSession, onSelect, onToggleAudit, showAudit }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '0 12px', height: '100%',
      background: '#050505',
      fontFamily: "'JetBrains Mono', monospace",
      overflowX: 'auto',
    }}>

      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0, marginRight: 4 }}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1L13 4V10L7 13L1 10V4L7 1Z"
            stroke="#22d3ee" strokeWidth="1.2" fill="rgba(34,211,238,0.08)" />
          <circle cx="7" cy="7" r="2" fill="#22d3ee" opacity="0.8" />
        </svg>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.08em' }}>
          THOUGHTLENS
        </span>
      </div>

      <div style={{ width: 1, height: 18, background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} />

      {/* Sessions */}
      {loading && (
        <span style={{ fontSize: 11, color: '#334155', animation: 'blink 1.2s ease-in-out infinite' }}>
          scanning...
        </span>
      )}

      {!loading && sessions.length === 0 && (
        <span style={{ fontSize: 11, color: '#334155' }}>
          no sessions — run a scenario to start
        </span>
      )}

      {sessions.map(s => {
        const sel = s.session_id === selectedSession;
        const hasCrit = (s.criticalCount || 0) > 0;
        const hasWarn = (s.warnCount || 0) > 0;
        return (
          <button
            key={s.session_id}
            onClick={() => onSelect?.(s.session_id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '3px 10px', flexShrink: 0,
              background: sel ? 'rgba(34,211,238,0.08)' : 'transparent',
              border: `1px solid ${sel ? 'rgba(34,211,238,0.30)' : hasCrit ? 'rgba(255,51,51,0.30)' : 'rgba(255,255,255,0.08)'}`,
              borderRadius: 0,
              color: sel ? '#22d3ee' : '#64748b',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11, fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 150ms ease-out',
            }}
            onMouseEnter={e => !sel && (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)')}
            onMouseLeave={e => !sel && (e.currentTarget.style.borderColor = hasCrit ? 'rgba(255,51,51,0.30)' : 'rgba(255,255,255,0.08)')}
          >
            <StatusDot status={s.status} />
            <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {s.session_id.slice(-8)}
            </span>
            {hasCrit && <span style={{ color: '#ff3333', fontSize: 10 }}>✕{s.criticalCount}</span>}
            {!hasCrit && hasWarn && <span style={{ color: '#ffb000', fontSize: 10 }}>△{s.warnCount}</span>}
            <span style={{ color: '#1e293b', fontSize: 10 }}>{s.events_count || 0}ev</span>
          </button>
        );
      })}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Audit button */}
      <button
        onClick={onToggleAudit}
        style={{
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '3px 10px', flexShrink: 0,
          background: showAudit ? 'rgba(34,211,238,0.08)' : 'transparent',
          border: `1px solid ${showAudit ? 'rgba(34,211,238,0.30)' : 'rgba(255,255,255,0.08)'}`,
          borderRadius: 0,
          color: showAudit ? '#22d3ee' : '#475569',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, cursor: 'pointer',
          transition: 'all 150ms ease-out',
        }}
      >
        ⊞ AUDIT
      </button>

    </div>
  );
}