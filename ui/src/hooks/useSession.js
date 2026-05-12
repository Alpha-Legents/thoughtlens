import { useState, useEffect, useRef, useCallback } from 'react';

export const useSession = ({ onSelect = null, autoRefresh = true } = {}) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const sessionsRef = useRef([]); // Store without triggering re-renders

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/control/sessions');
      if (response.ok) {
        const data = await response.json();
        const newSessions = data.sessions || [];
        
        // Only update state if sessions actually changed
        if (JSON.stringify(sessionsRef.current) !== JSON.stringify(newSessions)) {
          sessionsRef.current = newSessions;
          setSessions(newSessions);
          
          // Auto-select first session if none selected
          if (!selectedSession && newSessions.length > 0) {
            handleSelectSession(newSessions[0].id);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
    setLoading(false);
  }, [selectedSession]);

  const handleSelectSession = (sessionId) => {
    setSelectedSession(sessionId);
    if (onSelect) {
      onSelect(sessionId);
    }
  };

  useEffect(() => {
    if (!autoRefresh) return;
    
    // Initial fetch
    fetchSessions();
    
    // Poll without forcing re-renders on same data
    const interval = setInterval(() => {
      // Fetch in background without loading indicator
      fetch('/api/control/sessions')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.sessions) {
            const newSessions = data.sessions;
            // Only update if changed
            if (JSON.stringify(sessionsRef.current) !== JSON.stringify(newSessions)) {
              sessionsRef.current = newSessions;
              setSessions(newSessions);
              
              if (!selectedSession && newSessions.length > 0) {
                handleSelectSession(newSessions[0].id);
              }
            }
          }
        })
        .catch(err => console.error('Poll error:', err));
    }, 5000);
    
    return () => clearInterval(interval);
  }, [autoRefresh, fetchSessions]);

  return {
    sessions,
    loading,
    selectedSession,
    setSelectedSession: handleSelectSession,
    refreshSessions: fetchSessions
  };
};