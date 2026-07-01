/**
 * ProtectedRoute — gate for all authenticated pages.
 *
 * - If authentication check is in progress → full-page loader
 * - If authenticated → render children
 * - If not authenticated → redirect to /login
 */
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { PageLoader } from '../ui/PageLoader';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);

  // While rehydrating from token (page refresh), show a loader
  if (isLoading) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
