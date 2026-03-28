/**
 * Structured JSON logger for frontend (Task #98).
 *
 * Provides consistent structured logging matching backend format.
 * Required fields: timestamp, level, service, message
 * Optional: request_id for cross-service correlation
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  ts: number;
  level: LogLevel;
  service: string;
  message: string;
  request_id?: string;
  [key: string]: unknown;
}

const SERVICE_NAME = 'ai-real-estate-web';

let _requestId: string | undefined;

/**
 * Set the current request ID for log correlation.
 * Call from API route handlers to correlate frontend logs with backend request_id.
 */
export function setLogRequestId(requestId: string): void {
  _requestId = requestId;
}

/** Get current request ID. */
export function getLogRequestId(): string | undefined {
  return _requestId;
}

function createEntry(level: LogLevel, message: string, extra?: Record<string, unknown>): LogEntry {
  const entry: LogEntry = {
    ts: Date.now(),
    level,
    service: SERVICE_NAME,
    message,
    ...extra,
  };
  if (_requestId) {
    entry.request_id = _requestId;
  }
  return entry;
}

function log(level: LogLevel, message: string, extra?: Record<string, unknown>): void {
  const entry = createEntry(level, message, extra);
  const json = JSON.stringify(entry);

  switch (level) {
    case 'debug':
      console.debug(json);
      break;
    case 'info':
      console.info(json);
      break;
    case 'warn':
      console.warn(json);
      break;
    case 'error':
      console.error(json);
      break;
  }
}

/** Log at debug level. */
export function debug(message: string, extra?: Record<string, unknown>): void {
  if (process.env.NODE_ENV === 'production') return;
  log('debug', message, extra);
}

/** Log at info level. */
export function info(message: string, extra?: Record<string, unknown>): void {
  log('info', message, extra);
}

/** Log at warn level. */
export function warn(message: string, extra?: Record<string, unknown>): void {
  log('warn', message, extra);
}

/** Log at error level. */
export function error(message: string, extra?: Record<string, unknown>): void {
  log('error', message, extra);
}

/** Default export for convenience. */
const logger = { debug, info, warn, error, setLogRequestId, getLogRequestId };
export default logger;
