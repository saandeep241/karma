import { NavLink, Outlet } from 'react-router-dom';
import { useUser, useClerk } from '@clerk/clerk-react';
import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { checkAdmin } from '../api/client';

const isClerkActive = import.meta.env.PROD && !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function useClerkUser() {
  try {
    if (!isClerkActive) throw new Error('skip');
    const { user, isLoaded } = useUser();
    const { signOut } = useClerk();
    return { user, isLoaded, signOut };
  } catch {
    return { user: null as any, isLoaded: true, signOut: async () => {} };
  }
}

export function Layout() {
  const { user, isLoaded, signOut } = useClerkUser();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const { data: adminCheck, error: adminError } = useQuery({
    queryKey: ['admin', 'check'],
    queryFn: checkAdmin,
    enabled: isClerkActive ? (isLoaded && !!user) : true,
    retry: false,
  });
  
  const isAdmin = adminCheck?.is_admin || false;
  
  useEffect(() => {
    if (isLoaded && user) {
      console.log('🔍 Checking admin status for user:', user.id);
      console.log('Admin check enabled:', isLoaded && !!user);
      if (adminError) {
        console.error('❌ Admin check error:', adminError);
      }
      if (adminCheck) {
        console.log('✅ Admin check result:', adminCheck);
        console.log('Is admin:', isAdmin);
      }
    }
  }, [isLoaded, user, adminCheck, adminError, isAdmin]);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    }

    if (showUserMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showUserMenu]);

  const handleSignOut = async () => {
    try {
      await signOut();
      setShowUserMenu(false);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  // Get user display info
  const userDisplayName = user?.fullName || user?.firstName || user?.emailAddresses[0]?.emailAddress || 'User';
  
  // Calculate user initials
  let userInitials = 'U';
  if (user?.firstName && user?.lastName) {
    userInitials = `${user.firstName[0]}${user.lastName[0]}`.toUpperCase();
  } else if (user?.firstName) {
    userInitials = user.firstName[0].toUpperCase();
  } else if (userDisplayName && userDisplayName.length > 0) {
    userInitials = userDisplayName[0].toUpperCase();
  }
  
  const userEmail = user?.emailAddresses[0]?.emailAddress;

  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Header */}
      <header className="bg-white sticky top-0 z-50 border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2 no-underline group">
            <div className="text-[#0066cc]">
              <svg width="20" height="20" className="sm:w-6 sm:h-6" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L14.85 9.15L22 12L14.85 14.85L12 22L9.15 14.85L2 12L9.15 9.15L12 2Z" fill="currentColor"/>
              </svg>
            </div>
            <h1 className="font-sans font-bold text-lg sm:text-xl text-[#001a41]">Nudge</h1>
          </NavLink>
          
          <div className="flex items-center gap-2 sm:gap-4 md:gap-8">
            <nav className="hidden sm:flex items-center gap-4 md:gap-8">
              <NavLink to="/" className={({ isActive }) => `flex items-center gap-2 transition-colors no-underline text-[15px] font-medium ${isActive ? 'text-[#0066cc]' : 'text-[#4b5563] hover:text-[#0066cc]'}`}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                  <polyline points="9 22 9 12 15 12 15 22"></polyline>
                </svg>
                <span>Home</span>
              </NavLink>
              <NavLink to="/browse" className={({ isActive }) => `flex items-center gap-2 transition-colors no-underline text-[15px] font-medium ${isActive ? 'text-[#0066cc]' : 'text-[#4b5563] hover:text-[#0066cc]'}`}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 7H2V11H22V7Z" />
                  <path d="M2 11V21H22V11" />
                  <path d="M10 15H14" />
                </svg>
                <span>Browse</span>
              </NavLink>
              <NavLink to="/stats" className="flex items-center gap-2 text-[#4b5563] hover:text-[#0066cc] transition-colors no-underline text-[15px] font-medium">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10"></line>
                  <line x1="12" y1="20" x2="12" y2="4"></line>
                  <line x1="6" y1="20" x2="6" y2="14"></line>
                </svg>
                <span>Stats</span>
              </NavLink>
              {isAdmin && (
                <NavLink to="/admin" className={({ isActive }) => `flex items-center gap-2 transition-colors no-underline text-[15px] font-medium ${isActive ? 'text-[#0066cc]' : 'text-[#4b5563] hover:text-[#0066cc]'}`}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    <path d="M9 12l2 2 4-4"></path>
                  </svg>
                  <span>Admin</span>
                </NavLink>
              )}
            </nav>

            <NavLink to="/add" className="bg-[#0066cc] hover:bg-[#0052a3] text-white px-3 sm:px-5 py-1.5 sm:py-2 rounded-full font-medium transition-all no-underline flex items-center gap-1 sm:gap-2 shadow-sm text-xs sm:text-[14px]">
              <span>+</span>
              <span className="hidden sm:inline">Add Task</span>
            </NavLink>

            {/* User Menu */}
            {isLoaded && user && (
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-[#0066cc] focus:ring-offset-2"
                  aria-label="User menu"
                >
                  {/* User Avatar/Initials */}
                  {user.imageUrl ? (
                    <img
                      src={user.imageUrl}
                      alt={userDisplayName}
                      className="w-8 h-8 rounded-full object-cover border-2 border-gray-200"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-[#0066cc] text-white flex items-center justify-center font-medium text-sm">
                      {userInitials}
                    </div>
                  )}
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className={`text-gray-500 transition-transform ${showUserMenu ? 'rotate-180' : ''}`}
                  >
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </button>

                {/* Dropdown Menu */}
                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                    {/* User Info */}
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="font-medium text-gray-900 text-sm">{userDisplayName}</p>
                      {userEmail && (
                        <p className="text-gray-500 text-xs mt-1">{userEmail}</p>
                      )}
                    </div>

                    {/* Menu Items */}
                    <div className="py-1">
                      <button
                        onClick={handleSignOut}
                        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                          <polyline points="16 17 21 12 16 7"></polyline>
                          <line x1="21" y1="12" x2="9" y2="12"></line>
                        </svg>
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-4 sm:py-6 md:py-8">
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
