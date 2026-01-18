import { NavLink, Outlet } from 'react-router-dom';

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Header */}
      <header className="bg-white sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2 no-underline group">
            <div className="text-[#0066cc]">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L14.85 9.15L22 12L14.85 14.85L12 22L9.15 14.85L2 12L9.15 9.15L12 2Z" fill="currentColor"/>
              </svg>
            </div>
            <h1 className="font-sans font-bold text-xl text-[#001a41]">Nudge</h1>
          </NavLink>
          
          <div className="flex items-center gap-8">
            <nav className="flex items-center gap-8">
              <NavLink to="/browse" className="flex items-center gap-2 text-[#4b5563] hover:text-[#0066cc] transition-colors no-underline text-[15px] font-medium">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="9" y1="3" x2="9" y2="21"></line>
                </svg>
                <span>Browse</span>
              </NavLink>
              <NavLink to="/stats" className="flex items-center gap-2 text-[#4b5563] hover:text-[#0066cc] transition-colors no-underline text-[15px] font-medium">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10"></line>
                  <line x1="12" y1="20" x2="12" y2="4"></line>
                  <line x1="6" y1="20" x2="6" y2="14"></line>
                </svg>
                <span>Stats</span>
              </NavLink>
            </nav>

            <NavLink to="/add" className="bg-[#0066cc] hover:bg-[#0052a3] text-white px-5 py-2 rounded-full font-medium transition-all no-underline flex items-center gap-2 shadow-sm text-[14px]">
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
      <footer className="py-8">
        <div className="max-w-6xl mx-auto px-6 text-center text-gray-400 text-[12px]">
          <p>Nudge — AI-powered task suggestions</p>
        </div>
      </footer>
    </div>
  );
}
