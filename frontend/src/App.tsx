import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SignedIn, SignedOut, SignIn } from '@clerk/clerk-react';
import { Layout } from './components';
import { AuthTokenProvider } from './components/AuthTokenProvider';
import { HomePage, BrowsePage, AddPage, StatsPage, PresentationPage, AdminPage } from './pages';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

const isClerkActive = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY &&
  !(import.meta.env.VITE_DISABLE_AUTH === 'true' && !import.meta.env.PROD);

function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="browse" element={<BrowsePage />} />
          <Route path="add" element={<AddPage />} />
          <Route path="stats" element={<StatsPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
        <Route path="presentation" element={<PresentationPage />} />
      </Routes>
    </BrowserRouter>
  );
}

function App() {
  if (isClerkActive) {
    return (
      <QueryClientProvider client={queryClient}>
        <SignedOut>
          <div className="min-h-screen flex items-center justify-center bg-[#f8fafc] px-4">
            <div className="text-center w-full max-w-[400px]">
              <div className="flex flex-col items-center justify-center gap-2 mb-10">
                <div className="text-[#0066cc]">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L14.85 9.15L22 12L14.85 14.85L12 22L9.15 14.85L2 12L9.15 9.15L12 2Z" fill="currentColor"/>
                  </svg>
                </div>
                <h1 className="font-sans font-bold text-2xl text-[#001a41]">Nudge</h1>
              </div>
              <p className="text-gray-500 mb-12 text-[13px] leading-relaxed max-w-[320px] mx-auto">
                AI-powered task suggestions for productive moments. Sign in to get started.
              </p>
              <SignIn 
                appearance={{
                  elements: {
                    rootBox: "mx-auto w-full",
                    card: "shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 rounded-3xl p-4",
                    headerTitle: "text-lg font-bold text-[#001a41]",
                    headerSubtitle: "text-gray-400 text-sm",
                    socialButtonsBlockButton: "border border-gray-100 hover:bg-gray-50 transition-all rounded-xl py-2.5",
                    socialButtonsBlockButtonText: "font-medium text-gray-600",
                    formButtonPrimary: "bg-[#001a41] hover:bg-black text-white transition-all rounded-xl py-2.5 text-sm font-semibold",
                    footerActionLink: "text-[#0066cc] hover:text-[#0052a3] font-semibold",
                    identityPreviewText: "text-[#001a41]",
                    formFieldLabel: "text-gray-700 font-semibold text-sm mb-1.5",
                    formFieldInput: "rounded-xl border-gray-100 focus:ring-2 focus:ring-[#0066cc]/10 focus:border-[#0066cc] py-2.5",
                    dividerRow: "my-6",
                    dividerText: "text-gray-300 text-[10px] uppercase tracking-widest"
                  }
                }}
              />
              <p className="mt-12 text-[10px] text-gray-300 uppercase tracking-widest">Secured by Clerk • Development mode</p>
            </div>
          </div>
        </SignedOut>
        <SignedIn>
          <AuthTokenProvider>
            <AppRoutes />
          </AuthTokenProvider>
        </SignedIn>
      </QueryClientProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <AppRoutes />
    </QueryClientProvider>
  );
}

export default App;
