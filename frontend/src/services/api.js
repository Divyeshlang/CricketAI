// Resolve base URL from VITE_API_URL or fallback to local backend.
// Ensure base URL ends with /api exactly once without trailing slashes.
const envBase = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : (typeof process !== 'undefined' && process.env && process.env.VITE_API_URL ? process.env.VITE_API_URL : 'http://localhost:8000');

const rawBase = envBase.replace(/\/+$/, '');
const BASE = rawBase.endsWith('/api') ? rawBase : `${rawBase}/api`;

export function resolveUrl(path) {
  // Normalize path ensuring it starts with / and /api is prepended exactly once
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  if (cleanPath === '/api' || cleanPath.startsWith('/api/')) {
    const withoutApi = cleanPath.slice(4); // Remove leading '/api'
    return `${BASE}${withoutApi.startsWith('/') ? withoutApi : `/${withoutApi}`}`;
  }
  return `${BASE}${cleanPath}`;
}

export async function api(path, options = {}) {
  const url = resolveUrl(path);
  const response = await fetch(url, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export const post = (path, data) =>
  api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

