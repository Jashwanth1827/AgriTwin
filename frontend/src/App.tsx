import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { Spinner } from "./components/ui/misc";
import { useAuth } from "./lib/auth";
import BuyersPage from "./pages/BuyersPage";
import CropHealthPage from "./pages/CropHealthPage";
import DashboardPage from "./pages/DashboardPage";
import DecisionsPage from "./pages/DecisionsPage";
import FarmsPage from "./pages/FarmsPage";
import LoginPage from "./pages/LoginPage";
import MarketPage from "./pages/MarketPage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import TransportPage from "./pages/TransportPage";
import YieldPage from "./pages/YieldPage";

function FullScreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center gap-3 text-sm text-muted-foreground">
      <Spinner />
      Loading AgriTwin…
    </div>
  );
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PublicOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnly>
            <LoginPage />
          </PublicOnly>
        }
      />
      <Route
        path="/register"
        element={
          <PublicOnly>
            <RegisterPage />
          </PublicOnly>
        }
      />
      <Route
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/farms" element={<FarmsPage />} />
        <Route path="/crop-health" element={<CropHealthPage />} />
        <Route path="/yield" element={<YieldPage />} />
        <Route path="/market" element={<MarketPage />} />
        <Route path="/buyers" element={<BuyersPage />} />
        <Route path="/transport" element={<TransportPage />} />
        <Route path="/decisions" element={<DecisionsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
