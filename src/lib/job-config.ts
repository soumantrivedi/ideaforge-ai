/**
 * Job Processing Configuration
 * 
 * Reads configuration from runtime environment (ConfigMap) or uses defaults
 * This allows configuration without rebuilding the frontend image
 */

/**
 * Get polling interval from runtime config or use default
 * Default: 5000ms (5 seconds) - reduced from 2000ms to lower network load
 */
export function getJobPollInterval(): number {
  // Check for runtime configuration (injected by entrypoint script)
  if (typeof window !== 'undefined' && '__JOB_POLL_INTERVAL_MS__' in window) {
    const interval = (window as any).__JOB_POLL_INTERVAL_MS__;
    if (interval && !isNaN(Number(interval))) {
      return Number(interval);
    }
  }
  
  // Default: 5 seconds (5000ms) - better for 400+ concurrent users
  return 5000;
}

/**
 * Get max polling attempts from runtime config or use default
 * Default: 120 attempts (10 minutes at 5s intervals)
 */
export function getJobMaxPollAttempts(): number {
  if (typeof window !== 'undefined' && '__JOB_MAX_POLL_ATTEMPTS__' in window) {
    const attempts = (window as any).__JOB_MAX_POLL_ATTEMPTS__;
    if (attempts && !isNaN(Number(attempts))) {
      return Number(attempts);
    }
  }
  
  // Default: 120 attempts (10 minutes at 5s intervals)
  return 120;
}

/**
 * Get job timeout from runtime config or use default
 * Default: 600000ms (10 minutes)
 */
export function getJobTimeout(): number {
  if (typeof window !== 'undefined' && '__JOB_TIMEOUT_MS__' in window) {
    const timeout = (window as any).__JOB_TIMEOUT_MS__;
    if (timeout && !isNaN(Number(timeout))) {
      return Number(timeout);
    }
  }
  
  // Default: 10 minutes (600000ms)
  return 600000;
}

