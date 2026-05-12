import { useState } from 'react';
import ThoughtStream from './components/ThoughtStream';
import InjectionHighlight from './components/InjectionHighlight';
import ControlPanel from './components/ControlPanel';
import SessionBar from './components/SessionBar';
import AuditLog from './components/AuditLog';
import { useThoughtStream } from './hooks/useThoughtStream';
import { useSession } from './hooks/useSession';
import { FileText } from 'lucide-react';

function App() {
  const [selectedSession, setSelectedSession] = useState(null);
  const [showAudit, setShowAudit] = useState(false);
  const [activeThreat, setActiveThreat] = useState(null);

  const { sessions, loading: sessionsLoading } = useSession({
    onSelect: setSelectedSession,
    autoRefresh: true
  });

  const { events, isPaused } = useThoughtStream(selectedSession);

  const handleThreatHighlight = (threat) => {
    setActiveThreat(threat);
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <aside className="w-72 shrink-0 border-r border-gray-800 overflow-hidden">
        <SessionBar
          sessions={sessions}
          loading={sessionsLoading}
          selectedSession={selectedSession}
          onSelect={setSelectedSession}
        />
      </aside>

      <main className="flex flex-1 min-w-0 overflow-hidden">
        <section className="flex-[3] min-w-0 overflow-hidden border-r border-gray-800">
          <ThoughtStream
            events={events}
            isPaused={isPaused}
            selectedSession={selectedSession}
          />
        </section>

        <section className="flex-[2] min-w-0 flex flex-col overflow-hidden">
          <div className="flex items-center justify-end gap-2 border-b border-gray-800 bg-gray-950 px-3 py-2">
            <button
              type="button"
              onClick={() => setShowAudit(value => !value)}
              className="inline-flex items-center gap-2 rounded border border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-300 hover:border-cyan-500 hover:text-cyan-300"
            >
              <FileText className="h-3.5 w-3.5" />
              Audit
            </button>
          </div>
          <div className="flex-1 overflow-hidden">
            <InjectionHighlight
              threat={activeThreat}
              events={events}
              onThreatClick={handleThreatHighlight}
            />
          </div>
          <div className="h-96 shrink-0 overflow-hidden">
            <ControlPanel
              sessionId={selectedSession}
              isPaused={isPaused}
              events={events}
            />
          </div>
        </section>
      </main>

      {showAudit && (
        <aside className="w-96 shrink-0 border-l border-gray-800 overflow-hidden">
          <AuditLog
            events={events}
            onClose={() => setShowAudit(false)}
            selectedSession={selectedSession}
          />
        </aside>
      )}
    </div>
  );
}

export default App;
