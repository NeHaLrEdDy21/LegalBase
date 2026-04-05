import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import { AuthProvider } from './auth/AuthContext'
import './index.css'
import App from './App.tsx'

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ?? ''
// A real Clerk key is pk_test_<base58, ≥40 chars> — exclude the placeholder
const clerkConfigured = (CLERK_KEY.startsWith('pk_test_') || CLERK_KEY.startsWith('pk_live_'))
  && CLERK_KEY.length > 40
  && !CLERK_KEY.includes('YOUR_CLERK')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {clerkConfigured ? (
      <ClerkProvider publishableKey={CLERK_KEY} afterSignOutUrl="/">
        <App />
      </ClerkProvider>
    ) : (
      <AuthProvider>
        <App />
      </AuthProvider>
    )}
  </StrictMode>,
)
