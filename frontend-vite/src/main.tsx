import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import "./index.css";

import { AuthProvider, useAuth } from "./contexts/auth-context";
import { AppShell } from "./components/layout/app-shell";

// Lazy-loaded pages — each becomes its own chunk
const AuthPage = lazy(() => import("./pages/auth"));
const DashboardPage = lazy(() => import("./pages/dashboard"));
const PostsPage = lazy(() => import("./pages/posts"));
const GalleryPage = lazy(() => import("./pages/gallery"));
const InboxPage = lazy(() => import("./pages/inbox"));
const ApprovalsPage = lazy(() => import("./pages/approvals"));
const BrandsPage = lazy(() => import("./pages/brands"));
const KnowledgePage = lazy(() => import("./pages/knowledge"));
const SettingsPage = lazy(() => import("./pages/settings"));
const ConnectionsPage = lazy(() => import("./pages/connections"));
const TemplatesPage = lazy(() => import("./pages/templates"));
const LegalPage = lazy(() => import("./pages/legal"));
const LandingPage = lazy(() => import("./pages/landing"));

function PageSpinner() {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
    </div>
  );
}

function ProtectedRoute({ children, fullHeight }: { children: React.ReactNode; fullHeight?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center h-screen"><div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" /></div>;
  if (!user) return <Navigate to="/auth" replace />;
  return <AppShell fullHeight={fullHeight}>{children}</AppShell>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Toaster position="top-right" richColors closeButton />
        <Suspense fallback={<PageSpinner />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/posts" element={<ProtectedRoute><PostsPage /></ProtectedRoute>} />
            <Route path="/gallery" element={<ProtectedRoute><GalleryPage /></ProtectedRoute>} />
            <Route path="/inbox" element={<ProtectedRoute fullHeight><InboxPage /></ProtectedRoute>} />
            <Route path="/approvals" element={<ProtectedRoute><ApprovalsPage /></ProtectedRoute>} />
            <Route path="/brands" element={<ProtectedRoute><BrandsPage /></ProtectedRoute>} />
            <Route path="/knowledge" element={<ProtectedRoute><KnowledgePage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="/connections" element={<ProtectedRoute><ConnectionsPage /></ProtectedRoute>} />
          <Route path="/templates" element={<ProtectedRoute><TemplatesPage /></ProtectedRoute>} />
            <Route path="/connections/callback/:platform" element={<ProtectedRoute><ConnectionsPage /></ProtectedRoute>} />
            <Route path="/terms" element={<LegalPage />} />
          <Route path="/privacy" element={<LegalPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
