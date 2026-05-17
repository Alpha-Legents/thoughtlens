import { useEffect, useRef, memo } from 'react';

const EVENT_ICON = {
  FILE_READ: '📄', FILE_WRITE: '✏', API_CALL: '⇄', SHELL_CMD: '⌨',
  TOOL_CALL: '⚙', REASONING: '◌', TEXT_CHUNK: '─', SCOPE_EXTRACTED: '⊞',
  SCAN_CLEAN: '✓', SCAN_WARN: '△', SCAN_THREAT: '⚠', DEVIATION_WARN: '↗',
  DEVIATION_THREAT: '⛔', LT_ALLOW: '●', LT_WARN: '◐', LT_BLOCK: '✕',
  LT_REVIEW: '⊙', PAUSED: '⏸', RESUMED: '▶', KILLED: '✕',
  COMPLETE: '◉', ERROR: '!',
};

const SEV_BORDER = {
  CLEAN:    '2px solid var(--color-clean)',
  INFO:     '2px solid var(--color-info)',
  WARN:     '2px solid var(--color-warn)',
  CRITICAL: '2px solid var(--color-critical)',
};
const SEV_BG = {
  CLEAN:    'rgba(52,211,153,0.04)',
  INFO:     'rgba(56,189,248,0.04)',
  WARN:     'rgba(251,191,36,0.06)',
  CRITICAL: 'rgba(248,113,113,0.07)',
};
const SEV_TEXT = {
  CLEAN:    'var(--color-clean)',
  INFO:     'var(--color-info)',
  WARN:     'var(--color-warn)',
  CRITICAL: 'var(--color-critical)',
};

function fmt(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString('en-US', { hour12: false }) +
    '.' + String(d.getMilliseconds()).padStart(3, '0');
}

const Line = memo(({ event, isNew }) => {
  const sev = (event.severity || 'CLEAN').toUpperCase();
  return (
    <div
      data-event={event.type}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: 8,
        padding: '5px 12px', minHeight: 32,
        borderLeft: SEV_BORDER[sev] || SEV_BORDER.CLEAN,
        background: isNew ? SEV_BG[sev] : 'transparent',
        transition: 'background 400ms ease-out',
        cursor: ['SCAN_THREAT','DEVIATION_THREAT'].includes(event.type) ? 'pointer' : 'default',
      }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      <span style={{
        flexShrink: 0, fontFamily: "'Fira Code', monospace",
        fontSize: 10, color: 'var(--text-muted)', width: 80, paddingTop: 2,
      }}>
        {fmt(event.timestamp)}
      </span>
      <span style={{
        flexShrink: 0, fontSize: 12,
        color: SEV_TEXT[sev] || SEV_TEXT.CLEAN,
        width: 16, textAlign: 'center', paddingTop: 1,
      }}>
        {EVENT_ICON[event.type] || '·'}
      </span>
      <span style={{
        flexShrink: 0, fontFamily: "'Fira Code', monospace",
        fontSize: 10, color: SEV_TEXT[sev] || SEV_TEXT.CLEAN,
        width: 120, paddingTop: 2,
      }}>
        {(event.type || '').replace(/_/g, ' ').toLowerCase()}
      </span>
      <span style={{ flex: 1, minWidth: 0, paddingTop: 1 }}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {event.message}
        </span>
        {event.file_path && (
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'Fira Code', monospace", display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {event.file_path}
          </span>
        )}
        {event.api_url && (
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'Fira Code', monospace", display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {event.api_url}
          </span>
        )}
      </span>
    </div>
  );
});
Line.displayName = 'Line';

export default function ThoughtStream({ events, isPaused, selectedSession, onThreatClick }) {
  const containerRef = useRef(null);
  const bottomRef    = useRef(null);
  const autoScroll   = useRef(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = el;
      autoScroll.current = scrollTop + clientHeight >= scrollHeight - 60;
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!isPaused && autoScroll.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [events, isPaused]);

  const lastSev = events.length > 0
    ? (events[events.length - 1].severity || 'CLEAN').toUpperCase() : 'CLEAN';
  const statusColor = SEV_TEXT[lastSev] || SEV_TEXT.CLEAN;

  return (
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column',
      background: 'var(--bg-surface)', overflow: 'hidden',
    }}>

      {/* Header — pinned to top */}
      <div style={{
        flexShrink: 0, display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', gap: 8,
        padding: '6px 12px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--bg-raised)',
        fontSize: 11, fontWeight: 600,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-muted)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
            background: isPaused ? 'var(--color-warn)' : 'var(--color-clean)',
            boxShadow: isPaused ? '0 0 5px var(--color-warn)' : '0 0 5px var(--color-clean)',
            animation: isPaused ? 'blink 1.2s ease-in-out infinite' : 'none',
          }} />
          thought stream
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ color: statusColor, fontWeight: 700 }}>{lastSev}</span>
          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
            {events.length.toLocaleString()} events
          </span>
        </div>
      </div>

      {/* Scrollable event log */}
      {!selectedSession ? (
        <div style={{ flex: '1 1 0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center' }}>
            <div style={{ fontSize: 20, marginBottom: 8, opacity: 0.3 }}>⊙</div>
            select a session to begin
          </div>
        </div>
      ) : events.length === 0 ? (
        <div style={{ flex: '1 1 0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center' }}>
            <div style={{ fontSize: 20, marginBottom: 8, opacity: 0.4 }}>◌</div>
            waiting for events
          </div>
        </div>
      ) : (
        <div ref={containerRef} style={{ flex: '1 1 0', overflowY: 'auto', minHeight: 0 }}>
          {events.map((ev, i) => (
            <div
              key={ev.id || i}
              onClick={() => ['SCAN_THREAT','DEVIATION_THREAT'].includes(ev.type) && onThreatClick?.(ev)}
            >
              <Line event={ev} isNew={i === events.length - 1} />
            </div>
          ))}
          <div ref={bottomRef} style={{ height: 8 }} />
        </div>
      )}

      {/* Paused banner */}
      {isPaused && (
        <div style={{
          flexShrink: 0, padding: '5px 12px',
          background: 'rgba(251,191,36,0.07)',
          borderTop: '1px solid rgba(251,191,36,0.25)',
          color: 'var(--color-warn)', fontSize: 11,
          fontFamily: "'Fira Code', monospace", letterSpacing: '0.05em',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{ animation: 'blink 1s ease-in-out infinite' }}>⏸</span>
          EXECUTION PAUSED — AWAITING OPERATOR DECISION
        </div>
      )}
    </div>
  );
}