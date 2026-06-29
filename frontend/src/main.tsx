import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { setAuthToken } from './api/client'

// Bootstrap auth token from URL params (e.g., ?auth_token=xxx or #auth_token=xxx)
function bootstrapAuthFromUrl() {
  if (typeof window === 'undefined') return;
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const searchParams = new URLSearchParams(window.location.search);
  const token = hashParams.get('auth_token') ?? searchParams.get('auth_token');
  if (!token) return;

  setAuthToken(token);
  const url = new URL(window.location.href);
  url.hash = '';
  url.searchParams.delete('auth_token');
  window.history.replaceState({}, '', url.toString());
}

bootstrapAuthFromUrl();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
