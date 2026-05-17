import { useState } from 'react';

const btn = (bg, border, color) => ({
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  gap: 5, padding: '5px 14px',
  background: bg, border: `1px solid ${border}`, borderRadius: 3,
  color, fontFamily: "'Fira Sans', sans-serif",
  fontSize: 12, fontWeight: 500, cursor: 'pointer',
  whiteSpace: 'nowrap', transition: 'all 150ms ease-out',
});

const KILL_BTN    = btn('rgba(239,68,68,0.10)',   'rgba(239,68,68,0.35)',   '#f87171');
const RESUME_BTN  = btn('rgba(52,211,153,0.08)',  'rgba(52,211,153,0.30)',  '#34d399');
const EXPLAIN_BTN = btn('rgba(129,140,248,0.08)', 'rgba(129,140,248,0.30)', '#818cf8');
const DEFAULT_BTN = btn('rgba(255,255,255,0.05)', 'rgba(255,255,255,0.12)', '#94a3b8');

function Stat({ label, value, color }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, padding: '8px 0' }}>
      <span style={{ fontFamily: "'Fira Code', monospace", fontSize: 20, fontWeight: 700, color, lineHeight: 1 }}>
        {value}
      </span>
      <span style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {label}
      </span>
    </div>
  );
}

export default function ControlPanel({ sessionId, isPaused, events = [] }) {
  const [loading, setLoading]             = useState(false);
  const [explanation, setExplanation]     = useState(null);
  const [loadingExplain, setLoadingExplain] = useState(false);

  const clean    = events.filter(e => (e.severity||'').toLowerCase() === 'clean').length;
  const warn     = events.filter(e => (e.severity||'').toLowerCase() === 'warn').length;
  const critical = events.filter(e => (e.severity||'').toLowerCase() === 'critical').length;
  const hasCritical = critical > 0;
  const last = events[events.length - 1];

  async function doAction(action) {
    if (!sessionId || loading) return;
    setLoading(true);
    try { await fetch(`/${action}/${sessionId}`, { method: 'POST' }); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function handleExplain() {
    if (!hasCritical) return;
    setLoadingExplain(true);
    setExplanation(null);
    const critEvents = events.filter(e => (e.severity||'').toLowerCase() === 'critical').slice(-5);
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': import.meta.env.VITE_ANTHROPIC_API_KEY || '',
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 400,
          messages: [{
            role: 'user',
            content: `Explain this AI agent security threat in 3 sentences for an enterprise security team. Be concise and technical.\n\nEvents:\n${JSON.stringify(critEvents, null, 2)}`,
          }],
        }),
      });
      const data = res.ok ? await res.json() : null;
      setExplanation(data?.content?.[0]?.text || `${critical} critical event(s) detected. Review the thought stream.`);
    } catch {
      setExplanation(`${critical} critical event(s) detected. Manual review recommended.`);
    } finally {
      setLoadingExplain(false);
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', background: 'var(--bg-surface)', overflow: 'hidden',
    }}>
      {/* Header */}
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <span>control center</span>
        {sessionId && (
          <span style={{ fontFamily: "'Fira Code', monospace", fontSize: 10, color: 'var(--text-muted)' }}>
            {sessionId.slice(-8)}
          </span>
        )}
      </div>

      <div style={{ flex: '1 1 0', overflowY: 'auto', padding: '10px 12px', minHeight: 0 }}>

        {/* Stats */}
        <div style={{
          display: 'flex', gap: 1,
          background: 'var(--bg-raised)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 3, overflow: 'hidden', marginBottom: 10,
        }}>
          <Stat label="clean"    value={clean}    color="var(--color-clean)"    />
          <div style={{ width: 1, background: 'var(--border-subtle)' }} />
          <Stat label="warn"     value={warn}     color="var(--color-warn)"     />
          <div style={{ width: 1, background: 'var(--border-subtle)' }} />
          <Stat label="critical" value={critical} color="var(--color-critical)" />
        </div>

        {/* Buttons */}
        {sessionId && (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
            <button
              style={{ ...RESUME_BTN, opacity: (!isPaused || loading) ? 0.35 : 1, cursor: (!isPaused || loading) ? 'not-allowed' : 'pointer' }}
              disabled={!isPaused || loading}
              onClick={() => doAction('resume')}
            >
              ▶ resume
            </button>
            <button
              style={{ ...KILL_BTN, opacity: loading ? 0.35 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
              disabled={loading}
              onClick={() => doAction('kill')}
            >
              ✕ kill
            </button>
            {hasCritical && (
              <button
                style={{ ...EXPLAIN_BTN, opacity: loadingExplain ? 0.6 : 1 }}
                disabled={loadingExplain}
                onClick={handleExplain}
              >
                {loadingExplain ? '◌ analyzing…' : '⊙ explain'}
              </button>
            )}
          </div>
        )}

        {/* Paused indicator */}
        {isPaused && (
          <div style={{
            padding: '5px 10px', marginBottom: 10,
            background: 'rgba(251,191,36,0.07)',
            border: '1px solid rgba(251,191,36,0.25)',
            borderRadius: 3, fontSize: 11,
            fontFamily: "'Fira Code', monospace",
            color: 'var(--color-warn)', letterSpacing: '0.05em',
          }}>
            ⏸ awaiting operator decision
          </div>
        )}

        {/* No session */}
        {!sessionId && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>
            no session selected
          </div>
        )}

        {/* Last event */}
        {last && (
          <div style={{
            fontSize: 11, color: 'var(--text-muted)',
            fontFamily: "'Fira Code', monospace",
            paddingTop: 8, borderTop: '1px solid var(--border-subtle)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            last: {(last.type||'').replace(/_/g,' ').toLowerCase()}
            {last.message ? ` — ${last.message.slice(0,55)}` : ''}
          </div>
        )}

        {/* AI explanation */}
        {explanation && (
          <div style={{
            marginTop: 10, padding: '8px 10px', position: 'relative',
            background: 'rgba(129,140,248,0.06)',
            border: '1px solid rgba(129,140,248,0.20)',
            borderRadius: 3, fontSize: 11,
            color: 'var(--text-secondary)', lineHeight: 1.6,
          }}>
            <div style={{ fontSize: 10, color: '#818cf8', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              ai analysis
            </div>
            {explanation}
            <button
              onClick={() => setExplanation(null)}
              style={{ position: 'absolute', top: 6, right: 8, background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}
            >
              ✕
            </button>
          </div>
        )}
      </div>
    </div>
  );
}