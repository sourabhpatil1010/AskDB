/**
 * AuthGuard — wraps the entire app.
 *
 * On first mount, if a token exists in localStorage it calls fetchCurrentUser()
 * to re-validate the token with the server and rehydrate the user object.
 * This is the "page refresh" support — the user stays logged in.
 */
import { useEffect, useRef } from 'react';
import { useAuthStore } from '../../store/authStore';

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const fetchCurrentUser = useAuthStore((s) => s.fetchCurrentUser);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const token = localStorage.getItem('askdb-auth-token');
    if (token) {
      fetchCurrentUser();
    }
  }, [fetchCurrentUser]);

  return <>{children}</>;
}
