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

// Check if Clerk is configured
const isClerkConfigured = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function App() {
  // If Clerk is configured, require authentication
  if (isClerkConfigured) {
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
          </AuthTokenProvider>
        </SignedIn>
      </QueryClientProvider>
    );
  }

  // If Clerk is not configured, show app with simulation
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/*" element={
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
                <div className="bg-white p-10 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 text-left">
                  <h2 className="text-lg font-bold text-[#001a41] mb-1 text-center">Sign in to Nudge</h2>
                  <p className="text-gray-400 text-sm mb-8 text-center">Welcome back! Please sign in to continue</p>
                  
                  <button onClick={() => window.location.href = '/'} className="w-full flex items-center justify-center gap-3 py-2.5 border border-gray-100 rounded-xl hover:bg-gray-50 transition-all mb-6 font-medium text-gray-600 text-sm">
                    <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                    Continue with Google
                  </button>
                  
                  <div className="relative my-8">
                    <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-gray-50"></span></div>
                    <div className="relative flex justify-center text-[10px] uppercase tracking-widest"><span className="bg-white px-3 text-gray-300">or</span></div>
                  </div>
                  
                  <div className="mb-6">
                    <label className="block text-gray-700 font-semibold text-sm mb-2">Email address</label>
                    <input type="email" placeholder="Enter your email address" className="w-full px-4 py-2.5 border border-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#0066cc]/10 focus:border-[#0066cc] transition-all text-sm" />
                  </div>
                  
                  <button onClick={() => window.location.href = '/'} className="w-full bg-[#001a41] hover:bg-black text-white py-3 rounded-xl font-semibold transition-all mb-8 shadow-sm text-sm">
                    Continue
                  </button>
                  
                  <p className="text-center text-sm text-gray-400">
                    Don't have an account? <a href="#" className="text-[#0066cc] font-semibold hover:underline">Sign up</a>
                  </p>
                </div>
                <p className="mt-12 text-[10px] text-gray-300 uppercase tracking-widest">Secured by Clerk • Development mode</p>
              </div>
            </div>
          } />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
