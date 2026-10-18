import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import DisclaimerBanner from "./components/DisclaimerBanner";
import AssistantWidget from "./components/AssistantWidget";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ChecklistPage from "./pages/ChecklistPage";
import FormPage from "./pages/FormPage";
import DocumentsPage from "./pages/DocumentsPage";
import BookingPage from "./pages/BookingPage";
import QueuePage from "./pages/QueuePage";
import StaffPage from "./pages/StaffPage";
import NotFoundPage from "./pages/NotFoundPage";
import { useAuthStore } from "./features/auth/authStore";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

function StaffRoute({ children }: { children: React.ReactNode }) {
  const { token, role } = useAuthStore((s) => ({ token: s.token, role: s.role }));
  if (!token) return <Navigate to="/login" replace />;
  if (role !== "staff" && role !== "admin") return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <>
      <DisclaimerBanner />
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={<PrivateRoute><DashboardPage /></PrivateRoute>}
          />
          <Route
            path="/cases/:caseId/checklist"
            element={<PrivateRoute><ChecklistPage /></PrivateRoute>}
          />
          <Route
            path="/cases/:caseId/form"
            element={<PrivateRoute><FormPage /></PrivateRoute>}
          />
          <Route
            path="/cases/:caseId/documents"
            element={<PrivateRoute><DocumentsPage /></PrivateRoute>}
          />
          <Route
            path="/booking"
            element={<PrivateRoute><BookingPage /></PrivateRoute>}
          />
          <Route
            path="/queue"
            element={<PrivateRoute><QueuePage /></PrivateRoute>}
          />
          <Route
            path="/staff"
            element={<StaffRoute><StaffPage /></StaffRoute>}
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Layout>
      <AssistantWidget />
    </>
  );
}
