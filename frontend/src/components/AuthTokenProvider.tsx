/**
 * AuthTokenProvider - Sets up token getter for API client.
 * This component should wrap the app to provide authentication tokens to the API client.
 */

import { useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { setTokenGetter } from '../api/authToken';

export function AuthTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    // Set the token getter function for the API client
    setTokenGetter(async () => {
      if (!isSignedIn) {
        return null;
      }
      try {
        // Get session token for backend verification
        // Note: If you need custom claims, create a JWT template in Clerk Dashboard
        // and use: getToken({ template: 'your-template-name' })
        return await getToken();
      } catch (error) {
        console.error('Failed to get auth token:', error);
        return null;
      }
    });
  }, [getToken, isSignedIn]);

  return <>{children}</>;
}
