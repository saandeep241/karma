import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Home', icon: '✨' },
  { path: '/browse', label: 'Browse', icon: '📋' },
  { path: '/add', label: 'Add', icon: '➕' },
  { path: '/stats', label: 'Stats', icon: '📊' },
];

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="glass sticky top-0 z-50 border-b border-[var(--karma-border)]">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2 no-underline">
            <span className="text-2xl">✨</span>
            <h1 className="font-serif text-2xl italic gradient-text">Karma</h1>
          </NavLink>
          
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
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--karma-border)] py-6">
        <div className="max-w-4xl mx-auto px-4 text-center text-[var(--karma-text-muted)] text-sm">
          <p>Karma — AI-powered task suggestions for productive moments</p>
        </div>
      </footer>
    </div>
  );
}

