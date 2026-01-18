import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { path: '/browse', label: 'Browse', icon: '📋' },
  { path: '/stats', label: 'Stats', icon: '📊' },
];

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white sticky top-0 z-50 border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2 no-underline">
            <span className="text-2xl text-blue-600">✨</span>
            <h1 className="font-serif text-2xl text-gray-800">Karma</h1>
          </NavLink>
          
          <div className="flex items-center gap-6">
            <nav className="flex items-center gap-6">
              <NavLink to="/browse" className="flex items-center gap-2 text-gray-600 hover:text-blue-600 transition-colors no-underline font-medium">
                <span className="text-lg">📋</span>
                <span>Browse</span>
              </NavLink>
              <NavLink to="/stats" className="flex items-center gap-2 text-gray-600 hover:text-blue-600 transition-colors no-underline font-medium">
                <span className="text-lg">📊</span>
                <span>Stats</span>
              </NavLink>
            </nav>

            <NavLink to="/add" className="bg-[#0066cc] hover:bg-[#0052a3] text-white px-4 py-2 rounded-lg font-medium transition-all no-underline flex items-center gap-2 shadow-sm">
              <span>+</span>
              <span>Add Task</span>
            </NavLink>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-gray-400 text-sm">
          <p>Karma — AI-powered task suggestions</p>
        </div>
      </footer>
    </div>
  );
}
