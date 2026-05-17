import { useState, useEffect, useRef, useCallback } from 'react';

export const useSession = ({ onSelect = null, autoRefresh = true } = {}) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const selectedRef = useRef(null);
  const prevJson = useRef('');

  const fetchSessions = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      // FastAPI serves /sessions directly — not /api/control/sessions
      const res = await fetch('/sessions');
      if (!res.ok) return;
      const data = await res.json();
      const next = data.sessions || [];
      const nextJson = JSON.stringify(next);

      // Only update state if data actually changed — prevents flicker
      if (nextJson !== prevJson.current) {
        prevJson.current = nextJson;
        setSessions(next);

        // Auto-select first session if none selected yet
        if (!selectedRef.current && next.length > 0) {
          selectedRef.current = next[0].session_id;
          if (onSelect) onSelect(next[0].session_id);
        }
      }
    } catch (err) {
      console.error('Session fetch error:', err);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [onSelect]);

  useEffect(() => {
    fetchSessions(true);
    if (!autoRefresh) return;

    const id = setInterval(() => fetchSessions(false), 3000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchSessions]);

  const handleSelect = useCallback((sessionId) => {
    selectedRef.current = sessionId;
    if (onSelect) onSelect(sessionId);
  }, [onSelect]);

  return {
    sessions,
    loading,
    selectedSession: selectedRef.current,
    setSelectedSession: handleSelect,
    refreshSessions: () => fetchSessions(false),
  };
};
