import { NavLink, Outlet } from 'react-router-dom';
import { 
  SignedIn, 
  SignedOut, 
  SignInButton, 
  UserButton
} from '@clerk/clerk-react';

const navItems = [
  { path: '/', label: 'Home', icon: '✨' },
  { path: '/browse', label: 'Browse', icon: '📋' },
  { path: '/add', label: 'Add', icon: '➕' },
  { path: '/stats', label: 'Stats', icon: '📊' },
];

// Check if Clerk is configured
const isClerkConfigured = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="glass sticky top-0 z-50 border-b border-[var(--karma-border)]">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2 no-underline">
            <span className="text-2xl">✨</span>
            <h1 className="font-serif text-2xl gradient-text">Nudge</h1>
          </NavLink>
          
          <div className="flex items-center gap-4">
            <nav className="flex items-center gap-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 rounded-lg transition-all no-underline ${
                      isActive
                        ? 'bg-[var(--karma-accent)] text-white'
                        : 'text-[var(--karma-text-muted)] hover:bg-[var(--karma-surface)] hover:text-[var(--karma-text)]'
                    }`
                  }
                >
                  <span>{item.icon}</span>
                  <span className="hidden sm:inline">{item.label}</span>
                </NavLink>
              ))}
            </nav>

            {/* Auth Buttons */}
            {isClerkConfigured ? (
              <>
                <SignedOut>
                  <SignInButton mode="modal">
                    <button className="btn btn-primary text-sm">
                      Sign In
                    </button>
                  </SignInButton>
                </SignedOut>
                <SignedIn>
                  <UserButton 
                    afterSignOutUrl="/"
                    appearance={{
                      elements: {
                        avatarBox: "w-9 h-9"
                      }
                    }}
                  />
                </SignedIn>
              </>
            ) : (
              <span className="text-xs text-[var(--karma-text-muted)] bg-[var(--karma-surface)] px-2 py-1 rounded">
                Auth disabled
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--karma-border)] py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-[var(--karma-text-muted)] text-sm">
          <p>Nudge — AI-powered task suggestions</p>
        </div>
      </footer>
    </div>
  );
}

