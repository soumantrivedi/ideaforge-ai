/**
 * API Client with automatic 401 handling
 * Automatically clears invalid tokens and redirects to login on 401 errors
 */

// Use runtime configuration for API URL (supports ConfigMap-based configuration)
import { getValidatedApiUrl } from './runtime-config';
const API_URL = getValidatedApiUrl();

let onUnauthorizedCallback: (() => void) | null = null;

export function setUnauthorizedHandler(callback: () => void) {
  onUnauthorizedCallback = callback;
}

export async function apiFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('auth_token');
  
  // Add Authorization header if token exists
  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  // Merge with existing headers
  const mergedOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'include',
  };
  
  try {
    const response = await fetch(`${API_URL}${url}`, mergedOptions);
    
    // Handle 401 Unauthorized
    if (response.status === 401) {
      // Clear invalid token
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_id');
      localStorage.removeItem('tenant_id');
      
      // Call unauthorized handler if set (this will update React state and show login page)
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback();
      } else {
        // Fallback: reload page to trigger login
        window.location.reload();
      }
      
      // Throw error to prevent further processing (but don't log it - it's expected)
      // The error will be caught by the caller, which should handle it gracefully
      throw new Error('Unauthorized: Session expired. Please login again.');
    }
    
    return response;
  } catch (error) {
    // Re-throw if it's our 401 error
    if (error instanceof Error && error.message.includes('Unauthorized')) {
      throw error;
    }
    // Otherwise, re-throw the original error
    throw error;
  }
}

// Convenience methods
export const api = {
  get: (url: string, options?: RequestInit) => 
    apiFetch(url, { ...options, method: 'GET' }),
  
  post: (url: string, body?: any, options?: RequestInit) =>
    apiFetch(url, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    }),
  
  put: (url: string, body?: any, options?: RequestInit) =>
    apiFetch(url, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    }),
  
  delete: (url: string, options?: RequestInit) =>
    apiFetch(url, { ...options, method: 'DELETE' }),
  
  patch: (url: string, body?: any, options?: RequestInit) =>
    apiFetch(url, {
      ...options,
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    }),
};

