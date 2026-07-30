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
import MyPlan from "@/pages/MyPlan";
import Gmail from "@/pages/Gmail";
import Coach from "@/pages/Coach";
import NextSteps from "@/pages/NextSteps";
import Neurodivergent from "@/pages/Neurodivergent";
import NeurodivergentReports from "@/pages/NeurodivergentReports";
import SpecialNeedsV3 from "@/pages/SpecialNeedsV3";
import ChildGoals from "@/pages/ChildGoals";
import IssuesConcerns from "@/pages/IssuesConcerns";
import PriorityRanking from "@/pages/PriorityRanking";
import CommStyle from "@/pages/CommStyle";
import ReadinessCheck from "@/pages/ReadinessCheck";
import Summary from "@/pages/Summary";
import Safety from "@/pages/Safety";
import Watch from "@/pages/Watch";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
import Accessibility from "@/pages/Accessibility";
import Methodology from "@/pages/Methodology";
import DataRetention from "@/pages/DataRetention";
import DeleteAccount from "@/pages/DeleteAccount";
import Reflection from "@/pages/Reflection";
import Orientation from "@/pages/Orientation";
import ClaimAccount from "@/pages/ClaimAccount";
import CancelSubscription from "@/pages/CancelSubscription";
import MagicLinkConsume from "@/pages/MagicLinkConsume";
import AccountSetup from "@/pages/AccountSetup";
import ProgressPage from "@/pages/Progress";
import AdminDashboard from "@/pages/AdminDashboard";
import AdminUsers from "@/pages/AdminUsers";
import AdminSurveys from "@/pages/AdminSurveys";
import AdminInsights from "@/pages/AdminInsights";
import PostEventSurvey from "@/pages/PostEventSurvey";
import InviteAccept from "@/pages/InviteAccept";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import VerifyEmail from "@/pages/VerifyEmail";
import SignUp from "@/pages/SignUp";
import MediatorBadge from "@/pages/MediatorBadge";
import SafetyAssessment from "@/pages/SafetyAssessment";
import ProblemSolvingWorksheet from "@/pages/ProblemSolvingWorksheet";
import SharedCoParentingReport from "@/pages/SharedCoParentingReport";
import SharedSpecialNeedsReport from "@/pages/SharedSpecialNeedsReport";
import SpecialNeedsInviteAccept from "@/pages/SpecialNeedsInviteAccept";
import FamilyReport from "@/pages/FamilyReport";
import SharedFamilyReport from "@/pages/SharedFamilyReport";
import LegalAcknowledgment from "@/components/LegalAcknowledgment";

const TOAST_OPTIONS = {
  style: {
    background: "#FFFFFF",
    color: "#1A1330",
    border: "1px solid #E5E0EE",
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
        <Route path="/auth/magic" element={<MagicLinkConsume />} />
        <Route path="/auth/setup" element={<AccountSetup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/mediator-badge" element={<MediatorBadge />} />
        <Route path="/shared/coparenting/:token" element={<SharedCoParentingReport />} />
        <Route path="/shared/special-needs/:token" element={<SharedSpecialNeedsReport />} />
        <Route
          path="/invites/special-needs/:token"
          element={
            <ProtectedRoute>
              <SpecialNeedsInviteAccept />
            </ProtectedRoute>
          }
        />
        <Route path="/shared/family/:token" element={<SharedFamilyReport />} />
        <Route path="/survey/:token" element={<PostEventSurvey />} />
        <Route path="/invite/:token" element={<InviteAccept />} />
        <Route
          path="/claim"
          element={
            <ProtectedRoute>
              <ClaimAccount />
            </ProtectedRoute>
          }
        />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/accessibility" element={<Accessibility />} />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="/data-retention" element={<DataRetention />} />
        <Route path="/delete-account" element={<DeleteAccount />} />
        <Route path="/cancel-subscription" element={<CancelSubscription />} />
        <Route path="/safety" element={<Safety />} />
        <Route path="/watch" element={<Watch />} />

        <Route
          path="/safety-assessment"
          element={
            <ProtectedRoute>
              <SafetyAssessment />
            </ProtectedRoute>
          }
        />
        <Route
          path="/problem-solving"
          element={
            <ProtectedRoute>
              <ProblemSolvingWorksheet />
            </ProtectedRoute>
          }
        />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-plan"
          element={
            <ProtectedRoute>
              <MyPlan />
            </ProtectedRoute>
          }
        />
        <Route
          path="/gmail"
          element={
            <ProtectedRoute>
              <Gmail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/coach"
          element={
            <ProtectedRoute>
              <Coach />
            </ProtectedRoute>
          }
        />
        <Route
          path="/coach/:sessionId"
          element={
            <ProtectedRoute>
              <Coach />
            </ProtectedRoute>
          }
        />
        <Route
          path="/next-steps/:assessment"
          element={
            <ProtectedRoute>
              <NextSteps />
            </ProtectedRoute>
          }
        />
        <Route
          path="/neurodivergent"
          element={
            <ProtectedRoute>
              <Neurodivergent />
            </ProtectedRoute>
          }
        />
        <Route
          path="/neurodivergent/reports"
          element={
            <ProtectedRoute>
              <NeurodivergentReports />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v3"
          element={
            <ProtectedRoute>
              <SpecialNeedsV3 />
            </ProtectedRoute>
          }
        />
        <Route
          path="/family-report"
          element={
            <ProtectedRoute>
              <FamilyReport />
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
          path="/reflection"
          element={
            <ProtectedRoute>
              <Reflection />
            </ProtectedRoute>
          }
        />
        <Route
          path="/orientation"
          element={
            <ProtectedRoute>
              <Orientation />
            </ProtectedRoute>
          }
        />
        <Route
          path="/progress"
          element={
            <ProtectedRoute>
              <ProgressPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute>
              <AdminUsers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/surveys"
          element={
            <ProtectedRoute>
              <AdminSurveys />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/insights"
          element={
            <ProtectedRoute>
              <AdminInsights />
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
          <LegalAcknowledgment />
          <AppRoutes />
          <Toaster position="bottom-right" toastOptions={TOAST_OPTIONS} />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
