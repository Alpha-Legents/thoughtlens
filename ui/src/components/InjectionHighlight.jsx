import { useState, useEffect, useRef } from 'react';

function confidenceClass(c) {
  if (c >= 0.9) return 'confidence-high';
  if (c >= 0.7) return 'confidence-medium';
  return 'confidence-low';
}
function confidenceColor(c) {
  if (c >= 0.9) return 'var(--color-critical)';
  if (c >= 0.7) return '#fb923c';
  return 'var(--color-warn)';
}
function confidenceLabel(c) {
  if (c >= 0.9) return 'HIGH';
  if (c >= 0.7) return 'MED';
  return 'LOW';
}

function HighlightedPrompt({ text, spans }) {
  if (!text) return null;
  if (!spans || spans.length === 0) {
    return <span style={{ color: 'var(--text-secondary)' }}>{text}</span>;
  }
  const sorted = [...spans].sort((a, b) => a[0] - b[0]);
  const parts = [];
  let cursor = 0;
  sorted.forEach(([start, end], i) => {
    if (start > cursor) {
      parts.push(<span key={`pre-${i}`} style={{ color: 'var(--text-muted)' }}>{text.slice(cursor, start)}</span>);
    }
    const conf = spans[i]?.confidence ?? 0.9;
    parts.push(
      <span key={`t-${i}`} className={`threat-span ${confidenceClass(conf)}`}>
        {text.slice(start, end)}
      </span>
    );
    cursor = end;
  });
  if (cursor < text.length) {
    parts.push(<span key="post" style={{ color: 'var(--text-muted)' }}>{text.slice(cursor)}</span>);
  }
  return <>{parts}</>;
}

export default function InjectionHighlight({ threat, events, onThreatClick }) {
  const [selectedThreat, setSelectedThreat] = useState(null);
  const prevId = useRef(null);

  useEffect(() => {
    if (threat && threat.id !== prevId.current) {
      setSelectedThreat(threat);
      prevId.current = threat?.id;
    }
  }, [threat]);

  const recentThreats = (events || [])
    .filter(e => ['SCAN_THREAT', 'DEVIATION_THREAT'].includes(e.type))
    .slice(-8);

  const active = selectedThreat || recentThreats[recentThreats.length - 1] || null;
  const promptText = active?.original_prompt || active?.evidence || active?.message || '';
  const span = active?.injection_span ? [active.injection_span] : [];
  const vector = active?.injection_vector || active?.type || '';
  const confidence = active?.confidence ?? null;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', background: 'var(--bg-surface)', overflow: 'hidden',
    }}>
      {/* Header — no position absolute */}
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <span>threat analysis</span>
        {confidence != null && (
          <span style={{ color: confidenceColor(confidence), fontWeight: 700, fontSize: 'var(--text-xs)' }}>
            {confidenceLabel(confidence)} {Math.round(confidence * 100)}%
          </span>
        )}
      </div>

      {/* Body */}
      <div style={{ flex: '1 1 0', overflowY: 'auto', padding: '10px 12px', minHeight: 0 }}>

        {!active ? (
          <div style={{
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            height: '100%', color: 'var(--text-muted)',
            fontSize: 'var(--text-sm)', textAlign: 'center',
          }}>
            <div style={{ fontSize: 20, marginBottom: 8, opacity: 0.3 }}>⊙</div>
            no threats detected
          </div>
        ) : (
          <>
            {/* Vector badge */}
            {vector && (
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                padding: '2px 8px',
                border: `1px solid ${confidenceColor(confidence ?? 0.9)}`,
                borderRadius: 2, marginBottom: 10,
                fontSize: 'var(--text-xs)',
                fontFamily: "'Fira Code', monospace",
                color: confidenceColor(confidence ?? 0.9),
              }}>
                {vector.replace(/_/g, ' ')}
              </div>
            )}

            {/* Prompt box */}
            <div style={{
              padding: 10, background: 'var(--bg-raised)',
              border: '1px solid var(--border-subtle)', borderRadius: 3,
              fontFamily: "'Fira Code', monospace", fontSize: 'var(--text-xs)',
              lineHeight: 1.7, wordBreak: 'break-word', marginBottom: 10,
              maxHeight: 160, overflowY: 'auto',
            }}>
              <HighlightedPrompt text={promptText} spans={span} />
            </div>

            {/* Evidence */}
            {active.evidence && active.evidence !== promptText && (
              <div style={{ marginBottom: 10 }}>
                <div style={{
                  fontSize: 'var(--text-xs)', color: 'var(--text-muted)',
                  marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em',
                }}>
                  extracted payload
                </div>
                <div style={{
                  padding: '6px 10px',
                  background: 'rgba(248,113,113,0.06)',
                  border: '1px solid rgba(248,113,113,0.20)',
                  borderRadius: 3,
                  fontFamily: "'Fira Code', monospace",
                  fontSize: 'var(--text-xs)', color: 'var(--color-critical)',
                  wordBreak: 'break-all',
                }}>
                  {active.evidence}
                </div>
              </div>
            )}

            {/* Threat history */}
            {recentThreats.length > 1 && (
              <div>
                <div style={{
                  fontSize: 'var(--text-xs)', color: 'var(--text-muted)',
                  marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em',
                }}>
                  threat history ({recentThreats.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {recentThreats.map((t, i) => (
                    <div
                      key={t.id || i}
                      onClick={() => { setSelectedThreat(t); onThreatClick?.(t); }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '5px 8px',
                        background: t === active ? 'var(--bg-overlay)' : 'transparent',
                        border: `1px solid ${t === active ? 'var(--border-accent)' : 'var(--border-subtle)'}`,
                        borderRadius: 2, cursor: 'pointer',
                        transition: 'all 100ms ease-out',
                      }}
                    >
                      <span style={{
                        fontFamily: "'Fira Code', monospace", fontSize: 'var(--text-xs)',
                        color: confidenceColor(t.confidence ?? 0.8), width: 28, textAlign: 'right',
                      }}>
                        {t.confidence != null ? `${Math.round(t.confidence * 100)}%` : '—'}
                      </span>
                      <span style={{
                        fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
                        flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {(t.injection_vector || t.type || '').replace(/_/g, ' ')}
                      </span>
                      <span style={{
                        fontFamily: "'Fira Code', monospace",
                        fontSize: 'var(--text-xs)', color: 'var(--text-muted)',
                      }}>
                        {new Date((t.timestamp || 0) * 1000).toLocaleTimeString('en-US', { hour12: false })}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}