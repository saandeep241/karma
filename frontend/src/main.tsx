import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import './index.css'
import App from './App.tsx'

const RAW_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
const AUTH_DISABLED = import.meta.env.VITE_DISABLE_AUTH === 'true' && !import.meta.env.PROD

const PUBLISHABLE_KEY = AUTH_DISABLED ? undefined : RAW_KEY

if (AUTH_DISABLED) {
  console.warn('Auth disabled via VITE_DISABLE_AUTH (dev only)')
} else if (!PUBLISHABLE_KEY) {
  console.warn('Missing VITE_CLERK_PUBLISHABLE_KEY - Auth will be disabled')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {PUBLISHABLE_KEY ? (
      <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
        <App />
      </ClerkProvider>
    ) : (
      <App />
    )}
  </StrictMode>,
)
