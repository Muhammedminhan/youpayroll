import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import './index.css'
import App from './App.jsx'
import { bootstrapCsrf } from './api.js'

bootstrapCsrf();

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

const RootComponent = () => {
  if (!GOOGLE_CLIENT_ID) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'red', fontFamily: 'sans-serif' }}>
        <h1>Configuration Error</h1>
        <p>VITE_GOOGLE_CLIENT_ID is missing in environment.</p>
        <p style={{ color: '#666', fontSize: '0.9rem' }}>Please check your .env files or deployment secrets.</p>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  );
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RootComponent />
  </StrictMode>,
)
