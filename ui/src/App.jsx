import { useState, useEffect, useCallback } from 'react';
import BootSequence from './components/BootSequence';
import ThoughtStream from './components/ThoughtStream';
import InjectionHighlight from './components/InjectionHighlight';
import ControlPanel from './components/ControlPanel';
import SessionBar from './components/SessionBar';
import AuditLog from './components/AuditLog';
import { useThoughtStream } from './hooks/useThoughtStream';
import { useSession } from './hooks/useSession';

export default function App() {
  const [booted, setBooted] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [activeThreat, setActiveThreat] = useState(null);
  const [panelStates, setPanelStates] = useState({
    topbar: false,
    left: false,
    rightTop: false,
    rightBottom: false,
  });

  const handleSelect = useCallback((id) => {
    setSelectedSession(id);
    setActiveThreat(null);
  }, []);

  const { sessions, loading: sessionsLoading } = useSession({
    onSelect: handleSelect,
    autoRefresh: true,
  });

  const { events, isPaused } = useThoughtStream(selectedSession);

  const latestThreat = [...events]
    .reverse()
    .find(e => ['SCAN_THREAT', 'DEVIATION_THREAT'].includes(e.type));

  // Trigger panel animations after boot
  useEffect(() => {
    if (!booted) return;
    const timeouts = [
      setTimeout(() => setPanelStates(s => ({ ...s, topbar: true })), 100),
      setTimeout(() => setPanelStates(s => ({ ...s, left: true })), 250),
      setTimeout(() => setPanelStates(s => ({ ...s, rightTop: true })), 400),
      setTimeout(() => setPanelStates(s => ({ ...s, rightBottom: true })), 550),
    ];
    return () => timeouts.forEach(clearTimeout);
  }, [booted]);

  const toggleAudit = () => setShowAudit(v => !v);

  if (!booted) {
    return <BootSequence onComplete={() => setBooted(true)} />;
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-void)',
      color: 'var(--text-primary)',
      overflow: 'hidden',
      fontFamily: "'Fira Sans', system-ui, sans-serif",
    }}>

      {/* ── TOP BAR ── */}
      <div style={{
        height: 40,
        flexShrink: 0,
        transform: panelStates.topbar ? 'translateY(0)' : 'translateY(-100%)',
        opacity: panelStates.topbar ? 1 : 0,
        transition: 'all 500ms cubic-bezier(0.16, 1, 0.3, 1)',
      }}>
        <SessionBar
          sessions={sessions}
          loading={sessionsLoading}
          selectedSession={selectedSession}
          onSelect={handleSelect}
          onToggleAudit={toggleAudit}
          showAudit={showAudit}
        />
      </div>

      {/* ── MAIN CONTENT ── */}
      <div style={{
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'row',
        overflow: 'hidden',
      }}>

        {/* LEFT — ThoughtStream */}
        <div style={{
          width: '60%',
          height: '100%',
          minHeight: 0,
          borderRight: '1px solid var(--border-subtle)',
          transform: panelStates.left ? 'translateX(0)' : 'translateX(-40px)',
          opacity: panelStates.left ? 1 : 0,
          transition: 'all 600ms cubic-bezier(0.16, 1, 0.3, 1) 100ms',
        }}>
          <ThoughtStream
            events={events}
            isPaused={isPaused}
            selectedSession={selectedSession}
            onThreatClick={setActiveThreat}
          />
        </div>

        {/* RIGHT — stacked */}
        <div style={{
          width: '40%',
          height: '100%',
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>

          {/* TOP RIGHT — InjectionHighlight */}
          <div style={{
            flex: 2,
            minHeight: 0,
            borderBottom: '1px solid var(--border-subtle)',
            transform: panelStates.rightTop ? 'translateY(0)' : 'translateY(20px)',
            opacity: panelStates.rightTop ? 1 : 0,
            transition: 'all 600ms cubic-bezier(0.16, 1, 0.3, 1) 200ms',
          }}>
            <InjectionHighlight
              threat={activeThreat || latestThreat}
              events={events}
              onThreatClick={setActiveThreat}
            />
          </div>

          {/* BOTTOM RIGHT — ControlPanel */}
          <div style={{
            flex: 1,
            minHeight: 0,
            transform: panelStates.rightBottom ? 'scale(1)' : 'scale(0.96)',
            opacity: panelStates.rightBottom ? 1 : 0,
            transition: 'all 600ms cubic-bezier(0.16, 1, 0.3, 1) 300ms',
          }}>
            <ControlPanel
              sessionId={selectedSession}
              isPaused={isPaused}
              events={events}
            />
          </div>

        </div>
      </div>

      {/* ── AUDIT DRAWER ── */}
      {showAudit && (
        <div style={{
          height: 220,
          flexShrink: 0,
          borderTop: '1px solid var(--border-subtle)',
          overflow: 'hidden',
        }}>
          <AuditLog
            events={events}
            onClose={() => setShowAudit(false)}
            selectedSession={selectedSession}
          />
        </div>
      )}

    </div>
  );
}