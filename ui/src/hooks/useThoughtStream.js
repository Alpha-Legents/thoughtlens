import { useState, useEffect, useRef } from 'react';

export const useThoughtStream = (sessionId) => {
  const [events, setEvents] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [severity, setSeverity] = useState('clean');
  const [connection, setConnection] = useState('connecting');
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = () => {
    if (!sessionId) {
      setConnection('disconnected');
      return;
    }

    setConnection('connecting');

    try {
      const eventSource = new EventSource(`/api/control/events/${sessionId}`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setConnection('connected');
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'PAUSED') {
            setIsPaused(true);
          } else if (data.type === 'RESUMED' || data.type === 'KILLED') {
            setIsPaused(false);
          }

          if (data.severity) {
            setSeverity(data.severity);
          }

          setEvents(prev => [...prev, data]);
        } catch (e) {
          console.error('Failed to parse event data:', e);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        setConnection('error');
        eventSource.close();

        // Auto-reconnect after 2 seconds
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          if (sessionId) {
            connect();
          }
        }, 2000);
      };

    } catch (error) {
      console.error('Failed to connect to SSE:', error);
      setConnection('error');

      // Retry after 3 seconds
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      reconnectTimeoutRef.current = setTimeout(() => {
        if (sessionId) {
          connect();
        }
      }, 3000);
    }
  };

  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setEvents([]);
    setIsPaused(false);
    setSeverity('clean');
    setConnection('disconnected');
  };

  useEffect(() => {
    if (sessionId) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [sessionId]);

  return {
    events,
    isPaused,
    severity,
    connection,
    connect,
    disconnect
  };
};
