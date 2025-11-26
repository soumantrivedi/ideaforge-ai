/**
 * Runtime Configuration Utility
 * 
 * This allows the API URL to be configured at runtime via:
 * 1. window.__API_URL__ (injected by entrypoint script)
 * 2. import.meta.env.VITE_API_URL (build-time fallback)
 * 3. Empty string (for relative paths, nginx proxy)
 * 
 * This enables ConfigMap-based configuration without rebuilding the image.
 */

/**
 * Get the API URL from runtime configuration
 * Priority:
 * 1. window.__API_URL__ (runtime injection, even if empty string)
 * 2. import.meta.env.VITE_API_URL (build-time)
 * 3. '' (empty string for relative paths)
 */
export function getApiUrl(): string {
  // Check for runtime configuration (injected by entrypoint script)
  // Use 'in' operator to check if property exists, even if it's an empty string
  if (typeof window !== 'undefined' && '__API_URL__' in window) {
    const runtimeUrl = (window as any).__API_URL__;
    // Return the value even if it's an empty string (for relative paths)
    return runtimeUrl !== undefined ? runtimeUrl : '';
  }
  
  // Fallback to build-time configuration
  return import.meta.env.VITE_API_URL || '';
}

/**
 * Get the API URL with validation
 * Returns empty string if invalid (for relative paths)
 */
export function getValidatedApiUrl(): string {
  const url = getApiUrl();
  
  // If empty, use relative paths (nginx will proxy)
  if (!url || url.trim() === '') {
    return '';
  }
  
  // Validate URL format
  try {
    new URL(url);
    return url;
  } catch {
    // Invalid URL, fallback to relative paths
    console.warn(`Invalid API URL: ${url}, falling back to relative paths`);
    return '';
  }
}

// Export the API URL as a constant for convenience
export const API_URL = getValidatedApiUrl();

