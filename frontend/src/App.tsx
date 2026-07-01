import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { lazy, Suspense } from "react";
import { AppLayout } from "./layouts/AppLayout";
import { PageLoader } from "./components/ui/PageLoader";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { AuthGuard } from "./components/auth/AuthGuard";

// Public pages (no lazy needed — small & fast)
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// Protected pages (lazy loaded)
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const AISearchPage = lazy(() => import("./pages/AISearchPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const SavedQueriesPage = lazy(() => import("./pages/SavedQueriesPage"));
const SchemaExplorerPage = lazy(() => import("./pages/SchemaExplorerPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {/*
          AuthGuard runs once on mount to revalidate a stored token.
          This enables "stay logged in on page refresh" behaviour.
        */}
        <AuthGuard>
          <Routes>
            {/* ── Public routes ── */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* ── Protected routes (require authentication) ── */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route
                path="dashboard"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <DashboardPage />
                  </Suspense>
                }
              />
              <Route
                path="search"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <AISearchPage />
                  </Suspense>
                }
              />
              <Route
                path="history"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <HistoryPage />
                  </Suspense>
                }
              />
              <Route
                path="saved"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <SavedQueriesPage />
                  </Suspense>
                }
              />
              <Route
                path="schema"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <SchemaExplorerPage />
                  </Suspense>
                }
              />
              <Route
                path="analytics"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <AnalyticsPage />
                  </Suspense>
                }
              />
              <Route
                path="settings"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <SettingsPage />
                  </Suspense>
                }
              />
              <Route
                path="*"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <NotFoundPage />
                  </Suspense>
                }
              />
            </Route>
          </Routes>
        </AuthGuard>
      </BrowserRouter>
      <Toaster
        position="top-right"
        richColors
        toastOptions={{
          style: {
            borderRadius: '12px',
            fontSize: '14px',
          },
        }}
      />
    </QueryClientProvider>
  );
}

export default App;
