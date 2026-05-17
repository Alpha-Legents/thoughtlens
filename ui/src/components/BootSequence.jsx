import { useState, useEffect, useRef } from 'react';

const LINES = [
  { text: '▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮', delay: 200, style: 'brand' },
  { text: '    T H O U G H T L E N S    ', delay: 400, style: 'brand' },
  { text: '────────────────────────────────────', delay: 600, style: 'dim' },
  { text: '> init threat_detection_module...', delay: 800, style: 'cmd' },
  { text: '  [OK] pattern matcher loaded', delay: 1100, style: 'ok' },
  { text: '  [OK] deviation engine loaded', delay: 1300, style: 'ok' },
  { text: '  [OK] sandbox monitor loaded', delay: 1500, style: 'ok' },
  { text: '> establishing secure event stream...', delay: 1800, style: 'cmd' },
  { text: '  [OK] SSE connection ready', delay: 2200, style: 'ok' },
  { text: '> scanning active sessions...', delay: 2600, style: 'cmd' },
  { text: '  [FOUND] 5 sessions', delay: 2900, style: 'warn' },
  { text: '> all systems nominal', delay: 3300, style: 'ok' },
  { text: '', delay: 3700, style: 'dim' },
  { text: 'PRESS ANY KEY TO INITIALIZE', delay: 3900, style: 'blink' },
];

export default function BootSequence({ onComplete }) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [cursorOn, setCursorOn] = useState(true);
  const [done, setDone] = useState(false);
  const [progress, setProgress] = useState(0);
  const containerRef = useRef(null);

  // Type out lines
  useEffect(() => {
    let timeouts = [];
    LINES.forEach((line, i) => {
      timeouts.push(setTimeout(() => setVisibleCount(i + 1), line.delay));
    });
    // Progress bar animation (slow and smooth)
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 1;
      });
    }, 50); // 50ms per 1% = 5 seconds total
    // Auto-complete after last line + 1s
    timeouts.push(setTimeout(() => setDone(true), 5200));
    return () => {
      timeouts.forEach(clearTimeout);
      clearInterval(progressInterval);
    };
  }, []);

  // Blink cursor
  useEffect(() => {
    const id = setInterval(() => setCursorOn(v => !v), 530);
    return () => clearInterval(id);
  }, []);

  // Handle interaction
  const handleInteract = () => {
    if (visibleCount < LINES.length) {
      setVisibleCount(LINES.length);
      setProgress(100);
      setTimeout(() => setDone(true), 300);
    } else {
      setDone(true);
    }
  };

  // Trigger exit animation then callback
  useEffect(() => {
    if (!done) return;
    const t = setTimeout(onComplete, 800);
    return () => clearTimeout(t);
  }, [done, onComplete]);

  return (
    <div
      ref={containerRef}
      onClick={handleInteract}
      onKeyDown={handleInteract}
      tabIndex={0}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: '#000',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 14,
        lineHeight: 1.8,
        cursor: 'pointer',
        outline: 'none',
        opacity: done ? 0 : 1,
        transition: 'opacity 600ms ease-out',
        pointerEvents: done ? 'none' : 'all',
      }}
    >
      <div style={{ width: 560, maxWidth: '90vw', textAlign: 'center' }}>
        {LINES.slice(0, visibleCount).map((line, i) => (
          <div
            key={i}
            style={{
              opacity: 0,
              animation: 'line-enter 150ms ease-out forwards',
              animationDelay: '0ms',
              color:
                line.style === 'brand' ? '#22d3ee' :
                line.style === 'ok' ? '#00ff9d' :
                line.style === 'warn' ? '#ffb000' :
                line.style === 'cmd' ? '#94a3b8' :
                line.style === 'blink' ? '#22d3ee' :
                '#334155',
              fontWeight: line.style === 'brand' ? 700 : 400,
              letterSpacing: line.style === 'brand' ? '0.3em' : '0.02em',
              fontSize: line.style === 'brand' ? 24 : 13,
              textShadow: line.style === 'brand' ? '0 0 15px rgba(34,211,238,0.5)' : 'none',
              marginBottom: line.style === 'brand' ? 8 : 0,
              animation: line.style === 'blink' ? 'blink 1s ease-in-out infinite' : 'none',
            }}
          >
            {line.text}
            {i === visibleCount - 1 && cursorOn && line.style !== 'brand' && (
              <span style={{ color: '#22d3ee', marginLeft: 2 }}>█</span>
            )}
          </div>
        ))}
        
        {/* Fancy progress bar */}
        {visibleCount >= 9 && visibleCount < 12 && (
          <div style={{ marginTop: 24, width: '100%' }}>
            <div style={{
              height: 2,
              background: '#111',
              borderRadius: 1,
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                width: `${progress}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #22d3ee, #00ff9d)',
                transition: 'width 50ms linear',
                boxShadow: '0 0 8px rgba(34,211,238,0.5)'
              }} />
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: 6,
              fontSize: 9,
              color: '#334155',
              fontFamily: "'JetBrains Mono', monospace"
            }}>
              <span>SCANNING</span>
              <span>{progress}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Subtle "click to skip" hint */}
      <div style={{
        position: 'absolute',
        bottom: 24,
        fontSize: 10,
        color: '#1a1a1a',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
      }}>
        click or press any key to skip
      </div>
    </div>
  );
}