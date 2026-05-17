import { useState, useEffect, useRef } from 'react';

// Store events per session globally (outside component)
const sessionEventsCache = new Map();
const sessionPausedCache = new Map();

export const useThoughtStream = (sessionId) => {
  const [events, setEvents] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [connection, setConnection] = useState('disconnected');
  const esRef = useRef(null);
  const retryRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // When session changes, load cached events for that session
  useEffect(() => {
    if (!sessionId) {
      setEvents([]);
      setIsPaused(false);
      return;
    }

    // Load cached events for this session
    if (sessionEventsCache.has(sessionId)) {
      setEvents(sessionEventsCache.get(sessionId));
      setIsPaused(sessionPausedCache.get(sessionId) || false);
    } else {
      setEvents([]);
      setIsPaused(false);
    }

    // Connect SSE for this session
    connect(sessionId);

    return () => cleanup();
  }, [sessionId]);

  function connect(id) {
    cleanup();
    if (!id || !mountedRef.current) return;

    setConnection('connecting');

    const es = new EventSource(`/events/${id}`);
    esRef.current = es;

    es.onopen = () => {
      if (!mountedRef.current) return;
      setConnection('connected');
    };

    es.onmessage = (e) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(e.data);

        if (data.type === 'PAUSED') {
          setIsPaused(true);
          sessionPausedCache.set(id, true);
        }
        if (data.type === 'RESUMED' || data.type === 'KILLED') {
          setIsPaused(false);
          sessionPausedCache.set(id, false);
        }

        // Update cache and state
        const currentEvents = sessionEventsCache.get(id) || [];
        const newEvents = [...currentEvents, data];
        sessionEventsCache.set(id, newEvents);
        
        // Only update UI if this is the active session
        if (id === sessionId) {
          setEvents(newEvents);
        }
      } catch (err) {
        console.warn('SSE parse error:', err);
      }
    };

    es.onerror = () => {
      if (!mountedRef.current) return;
      setConnection('error');
      es.close();

      retryRef.current = setTimeout(() => {
        if (mountedRef.current && sessionId) connect(sessionId);
      }, 3000);
    };
  }

  function cleanup() {
    if (retryRef.current) {
      clearTimeout(retryRef.current);
      retryRef.current = null;
    }
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setConnection('disconnected');
  }

  return { events, isPaused, connection };
};