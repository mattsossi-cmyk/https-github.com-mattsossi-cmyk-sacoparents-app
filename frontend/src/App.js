import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import "@/App.css";
import { Toaster } from "sonner";

import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import BiometricGate from "@/components/BiometricGate";

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import ChildGoals from "@/pages/ChildGoals";
import IssuesConcerns from "@/pages/IssuesConcerns";
import PriorityRanking from "@/pages/PriorityRanking";
import CommStyle from "@/pages/CommStyle";
import ReadinessCheck from "@/pages/ReadinessCheck";
import Summary from "@/pages/Summary";
import Resources from "@/pages/Resources";
import Safety from "@/pages/Safety";

const TOAST_OPTIONS = {
  style: {
    background: "#FFFFFF",
    color: "#2A3631",
    border: "1px solid #E8ECE9",
    borderRadius: "16px",
  },
};

function HashAuthGuard({ children }) {
  // Catch Emergent OAuth hash before normal routing
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return children;
}

function AppRoutes() {
  return (
    <HashAuthGuard>
      <BiometricGate>
        <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/safety" element={<Safety />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prep/child-goals"
          element={
            <ProtectedRoute>
              <ChildGoals />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prep/issues"
          element={
            <ProtectedRoute>
              <IssuesConcerns />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prep/priority"
          element={
            <ProtectedRoute>
              <PriorityRanking />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prep/communication"
          element={
            <ProtectedRoute>
              <CommStyle />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prep/readiness"
          element={
            <ProtectedRoute>
              <ReadinessCheck />
            </ProtectedRoute>
          }
        />
        <Route
          path="/summary"
          element={
            <ProtectedRoute>
              <Summary />
            </ProtectedRoute>
          }
        />
        <Route
          path="/resources"
          element={
            <ProtectedRoute>
              <Resources />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </BiometricGate>
    </HashAuthGuard>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
          <Toaster position="bottom-right" toastOptions={TOAST_OPTIONS} />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
