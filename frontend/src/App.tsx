import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SignedIn, SignedOut, SignIn } from '@clerk/clerk-react';
import { Layout } from './components';
import { AuthTokenProvider } from './components/AuthTokenProvider';
import { HomePage, BrowsePage, AddPage, StatsPage, PresentationPage } from './pages';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

// Check if Clerk is configured
const isClerkConfigured = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function App() {
  // If Clerk is configured, require authentication
  if (isClerkConfigured) {
    return (
      <QueryClientProvider client={queryClient}>
        <SignedOut>
          <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="text-center">
              <h1 className="text-4xl font-serif italic mb-6 text-gray-800">
                ✨ Welcome to Karma
              </h1>
              <p className="text-gray-600 mb-8 max-w-md mx-auto">
                AI-powered task suggestions for productive moments. Sign in to get started.
              </p>
              <SignIn 
                appearance={{
                  elements: {
                    rootBox: "mx-auto",
                    card: "shadow-xl"
                  }
                }}
              />
            </div>
          </div>
        </SignedOut>
        <SignedIn>
          <AuthTokenProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Layout />}>
                  <Route index element={<HomePage />} />
                  <Route path="browse" element={<BrowsePage />} />
                  <Route path="add" element={<AddPage />} />
                  <Route path="stats" element={<StatsPage />} />
                </Route>
                <Route path="presentation" element={<PresentationPage />} />
              </Routes>
            </BrowserRouter>
          </AuthTokenProvider>
        </SignedIn>
      </QueryClientProvider>
    );
  }

  // If Clerk is not configured, show app without auth
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="browse" element={<BrowsePage />} />
            <Route path="add" element={<AddPage />} />
            <Route path="stats" element={<StatsPage />} />
          </Route>
          <Route path="presentation" element={<PresentationPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
