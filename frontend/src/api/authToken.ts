/**
 * Authentication token management for API client.
 * Provides a way to get Clerk tokens from non-React contexts.
 */

let tokenGetter: (() => Promise<string | null>) | null = null;

/**
 * Set the token getter function.
 * Should be called from a React component that has access to Clerk's useAuth hook.
 */
export function setTokenGetter(getter: () => Promise<string | null>) {
  tokenGetter = getter;
}

/**
 * Get the current authentication token.
 * Returns null if no token is available (dev mode or not authenticated).
 */
export async function getAuthToken(): Promise<string | null> {
  if (tokenGetter) {
    return tokenGetter();
  }
  
  // Fallback: try to get token from Clerk instance if available
  try {
    // @ts-ignore - Clerk may not be available
    const clerk = (window as any).Clerk;
    if (clerk?.session) {
      return await clerk.session.getToken();
    }
  } catch (error) {
    // Clerk not available
  }
  
  return null;
}
