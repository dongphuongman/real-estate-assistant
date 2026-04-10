'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import type { MarketAnomaly } from '@/lib/types';
import { getApiUrl } from '@/lib/api';
import { ReconnectingEventSource } from '@/lib/streaming';
import { info } from '@/lib/logger';

interface UseAnomalyStreamResult {
  anomalies: MarketAnomaly[];
  connected: boolean;
  error: string | null;
  clearAnomalies: () => void;
  removeAnomaly: (anomalyId: string) => void;
  /** Current reconnection attempt count (Task #74) */
  reconnectAttempts: number;
}

/**
 * Hook to subscribe to real-time anomaly notifications via Server-Sent Events.
 * Uses exponential backoff for reconnection (Task #74).
 *
 * @param enabled - Whether to enable the subscription (default: true)
 * @param maxAnomalies - Maximum number of anomalies to keep in state (default: 50)
 *
 * @example
 * ```tsx
 * function AnomalyDashboard() {
 *   const { anomalies, connected, error } = useAnomalyStream();
 *
 *   if (error) return <div>Error: {error}</div>;
 *
 *   return (
 *     <div>
 *       <div>Status: {connected ? 'Connected' : 'Disconnected'}</div>
 *       {anomalies.map(a => <AnomalyCard key={a.id} anomaly={a} />)}
 *     </div>
 *   );
 * }
 * ```
 */
export function useAnomalyStream(
  enabled: boolean = true,
  maxAnomalies: number = 50
): UseAnomalyStreamResult {
  const [anomalies, setAnomalies] = useState<MarketAnomaly[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const eventSourceRef = useRef<ReconnectingEventSource | null>(null);

  const handleNewAnomaly = useCallback(
    (anomaly: MarketAnomaly) => {
      setAnomalies((prev) => {
        // Add new anomaly at the beginning and limit the list size
        const updated = [anomaly, ...prev];
        return updated.slice(0, maxAnomalies);
      });
    },
    [maxAnomalies]
  );

  useEffect(() => {
    // Don't connect if disabled
    if (!enabled) {
      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      };
    }

    const url = `${getApiUrl()}/anomalies/stream`;

    // Use ReconnectingEventSource with exponential backoff (Task #74)
    const eventSource = new ReconnectingEventSource(url, {
      maxRetries: 10,
      initialDelay: 1000,
      maxDelay: 30000,
    });
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
      setReconnectAttempts(0);
      info('SSE connected to anomaly stream');
    };

    eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);

        // Handle connection status messages
        if (data.type === 'connected') {
          return;
        }
        if (data.type === 'disconnected') {
          setConnected(false);
          return;
        }
        if (data.type === 'error') {
          setError(data.message || 'Stream error');
          return;
        }

        // Handle anomaly data
        if (data.id && data.property_id) {
          handleNewAnomaly(data as MarketAnomaly);
        }
      } catch (err) {
        console.error('[SSE] Failed to parse anomaly:', err);
      }
    };

    eventSource.onerror = () => {
      setConnected(false);
      setError('Connection lost. Reconnecting...');
    };

    // Listen for reconnecting events from ReconnectingEventSource (Task #74)
    eventSource.addEventListener('reconnecting', ((event: Event) => {
      const customEvent = event as CustomEvent<{ attempt: number }>;
      setReconnectAttempts(customEvent.detail?.attempt || 0);
      info('SSE reconnecting', { attempt: customEvent.detail?.attempt || 0 });
    }) as EventListener);

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnected(false);
    };
  }, [enabled, handleNewAnomaly]);

  /**
   * Clear all anomalies
   */
  const clearAnomalies = useCallback(() => {
    setAnomalies([]);
  }, []);

  /**
   * Remove a specific anomaly
   */
  const removeAnomaly = useCallback((anomalyId: string) => {
    setAnomalies((prev) => prev.filter((a) => a.id !== anomalyId));
  }, []);

  return {
    anomalies,
    connected,
    error,
    clearAnomalies,
    removeAnomaly,
    reconnectAttempts,
  };
}

export default useAnomalyStream;
