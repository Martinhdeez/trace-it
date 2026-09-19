import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import App from './App.tsx'
import { ApiError } from './api/client'
import { AppStateProvider } from './state/app'
import { SessionProvider } from './state/session'
import { ThemeProvider } from './state/theme'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      // A 4xx will not change on retry; show it at once.
      retry: (attempts, error) =>
        attempts < 1 && !(error instanceof ApiError && error.status < 500),
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <SessionProvider>
            <AppStateProvider>
              <App />
            </AppStateProvider>
          </SessionProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
