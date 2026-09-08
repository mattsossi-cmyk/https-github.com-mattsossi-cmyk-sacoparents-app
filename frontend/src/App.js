import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import "@/App.css";
import { Toaster } from "sonner";

import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import BiometricGate from "@/components/BiometricGate";
import { PreShareConsentHost } from "@/components/PreShareConsentDialog";
import PolicyRefreshBanner from "@/components/PolicyRefreshBanner";
import BackToDashboardPill from "@/components/BackToDashboardPill";

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import OnboardingIntake from "@/pages/OnboardingIntake";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import MyPlan from "@/pages/MyPlan";
import Gmail from "@/pages/Gmail";
import Coach from "@/pages/Coach";
import NextSteps from "@/pages/NextSteps";
import ChildGoals from "@/pages/ChildGoals";
import IssuesConcerns from "@/pages/IssuesConcerns";
import PriorityRanking from "@/pages/PriorityRanking";
import CommStyle from "@/pages/CommStyle";
import ReadinessCheck from "@/pages/ReadinessCheck";
import Summary from "@/pages/Summary";
import Safety from "@/pages/Safety";
import Watch from "@/pages/Watch";
import Privacy from "@/pages/Privacy";
import AppStorePrivacy from "@/pages/AppStorePrivacy";
import HipaaNotice from "@/pages/HipaaNotice";
import PrivacyPractices from "@/pages/PrivacyPractices";
import Hb300Notice from "@/pages/Hb300Notice";
import Terms from "@/pages/Terms";
import Accessibility from "@/pages/Accessibility";
import Methodology from "@/pages/Methodology";
import DataRetention from "@/pages/DataRetention";
import Account from "@/pages/Account";
import DeleteAccount from "@/pages/DeleteAccount";
import Reflection from "@/pages/Reflection";
import FoundationStatementDemo from "@/pages/FoundationStatementDemo";
import JointReportsPicker from "@/pages/JointReportsPicker";
import CommunicationPathway from "@/pages/CommunicationPathway";
import CommunicationReflection from "@/pages/CommunicationReflection";
import CommunicationAlignment from "@/pages/CommunicationAlignment";
import ParentingScheduleReflection from "@/pages/ParentingScheduleReflection";
import ParentingScheduleAlignment from "@/pages/ParentingScheduleAlignment";
import ActivitiesReflection from "@/pages/ActivitiesReflection";
import ActivitiesAlignment from "@/pages/ActivitiesAlignment";
import Samples from "@/pages/Samples";
import JoinInvitation from "@/pages/JoinInvitation";
import JoinCode from "@/pages/JoinCode";
import ProfessionalsDirectory from "@/pages/ProfessionalsDirectory";
import ForProfessionals from "@/pages/ForProfessionals";
import ProfessionalJointAlignmentNew from "@/pages/ProfessionalJointAlignmentNew";
import ProfessionalJointAlignmentMine from "@/pages/ProfessionalJointAlignmentMine";
import ProfessionalJointAlignmentBulk from "@/pages/ProfessionalJointAlignmentBulk";
import ProfessionalJointAlignmentBulkHistory from "@/pages/ProfessionalJointAlignmentBulkHistory";
import ShareWithProfessional from "@/pages/ShareWithProfessional";
import SharedWithProfessionals from "@/pages/SharedWithProfessionals";
import ForPortalEngineers from "@/pages/ForPortalEngineers";
import AdminProfessionalsEditor from "@/pages/AdminProfessionalsEditor";
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
import VerifySignature from "@/pages/VerifySignature";
import VerifyBriefing from "@/pages/VerifyBriefing";
import VerifyPathway from "@/pages/VerifyPathway";
import VerifyCourtReport from "@/pages/VerifyCourtReport";
import AdminReviewers from "@/pages/AdminReviewers";
import AdminNDCoordinator from "@/pages/AdminNDCoordinator";
import PathwayReport from "@/pages/PathwayReport";
import JointProfessionalReport from "@/pages/JointProfessionalReport";
import JointAgreement from "@/pages/JointAgreement";
import JointAgreementShared from "@/pages/JointAgreementShared";
import FoundationStatementShared from "@/pages/FoundationStatementShared";
import JointReportShared from "@/pages/JointReportShared";
import NDRiskAssessment from "@/pages/NDRiskAssessment";
import NDRiskAssessmentResult from "@/pages/NDRiskAssessmentResult";
import DimensionCompanion from "@/pages/DimensionCompanion";
import InterventionCompliance from "@/pages/InterventionCompliance";
import SignUp from "@/pages/SignUp";
import MediatorBadge from "@/pages/MediatorBadge";
import SafetyAssessment from "@/pages/SafetyAssessment";
import ProblemSolvingWorksheet from "@/pages/ProblemSolvingWorksheet";
import SharedCoParentingReport from "@/pages/SharedCoParentingReport";
import SpecialNeedsV2 from "@/pages/SpecialNeedsV2";
import SpecialNeedsV2Report from "@/pages/SpecialNeedsV2Report";
import SpecialNeedsV2Compare from "@/pages/SpecialNeedsV2Compare";
import SpecialNeedsV2CompareView from "@/pages/SpecialNeedsV2CompareView";
import SpecialNeedsV2EducationalDeepDive from "@/pages/SpecialNeedsV2EducationalDeepDive";
import SpecialNeedsV2EducationalDeepDiveReport from "@/pages/SpecialNeedsV2EducationalDeepDiveReport";
import SpecialNeedsV2EducationalDeepDiveCompare from "@/pages/SpecialNeedsV2EducationalDeepDiveCompare";
import SpecialNeedsV2EducationalDeepDiveCompareView from "@/pages/SpecialNeedsV2EducationalDeepDiveCompareView";
import SpecialNeedsV2PsychologicalDeepDive from "@/pages/SpecialNeedsV2PsychologicalDeepDive";
import SpecialNeedsV2PsychologicalDeepDiveReport from "@/pages/SpecialNeedsV2PsychologicalDeepDiveReport";
import SpecialNeedsV2PsychologicalDeepDiveCompare from "@/pages/SpecialNeedsV2PsychologicalDeepDiveCompare";
import SpecialNeedsV2PsychologicalDeepDiveCompareView from "@/pages/SpecialNeedsV2PsychologicalDeepDiveCompareView";
import SpecialNeedsV2MedicalDeepDive from "@/pages/SpecialNeedsV2MedicalDeepDive";
import SpecialNeedsV2MedicalDeepDiveReport from "@/pages/SpecialNeedsV2MedicalDeepDiveReport";
import SpecialNeedsV2MedicalDeepDiveCompare from "@/pages/SpecialNeedsV2MedicalDeepDiveCompare";
import SpecialNeedsV2MedicalDeepDiveCompareView from "@/pages/SpecialNeedsV2MedicalDeepDiveCompareView";
import LearningCenter from "@/pages/LearningCenter";
import LearningArticle from "@/pages/LearningArticle";
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
        <PolicyRefreshBanner />
        <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/samples" element={<Samples />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/onboarding/what-do-you-need" element={<ProtectedRoute><OnboardingIntake /></ProtectedRoute>} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/auth/magic" element={<MagicLinkConsume />} />
        <Route path="/auth/setup" element={<AccountSetup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/verify/briefing/:sig_id" element={<VerifyBriefing />} />
        <Route path="/verify/pathway/:sig_id" element={<VerifyPathway />} />
        <Route path="/verify/court-report/:sig_id" element={<VerifyCourtReport />} />
        <Route path="/verify/:sig_id" element={<VerifySignature />} />
        <Route path="/admin/reviewers" element={<AdminReviewers />} />
        <Route path="/admin/nd-coordinator" element={<AdminNDCoordinator />} />
        <Route path="/pathway-report" element={<PathwayReport />} />
        <Route path="/joint-professional-report" element={<JointProfessionalReport />} />
        <Route path="/joint-agreement" element={<JointAgreement />} />
        <Route path="/joint-reports" element={<JointReportsPicker />} />
        <Route path="/communication" element={<CommunicationPathway />} />
        <Route path="/communication/reflection" element={<CommunicationReflection />} />
        <Route path="/communication/alignment" element={<CommunicationAlignment />} />
        <Route path="/schedule/reflection" element={<ParentingScheduleReflection />} />
        <Route path="/schedule/alignment" element={<ParentingScheduleAlignment />} />
        <Route path="/activities/reflection" element={<ActivitiesReflection />} />
        <Route path="/activities/alignment" element={<ActivitiesAlignment />} />
        <Route path="/join" element={<JoinCode />} />
        <Route path="/join/:token" element={<JoinInvitation />} />
        <Route path="/professionals" element={<ProfessionalsDirectory />} />
        <Route path="/for-professionals" element={<ForProfessionals />} />
        <Route
          path="/professional/joint-alignment/new"
          element={<ProtectedRoute><ProfessionalJointAlignmentNew /></ProtectedRoute>}
        />
        <Route
          path="/professional/joint-alignment/mine"
          element={<ProtectedRoute><ProfessionalJointAlignmentMine /></ProtectedRoute>}
        />
        <Route
          path="/professional/joint-alignment/bulk"
          element={<ProtectedRoute><ProfessionalJointAlignmentBulk /></ProtectedRoute>}
        />
        <Route
          path="/professional/joint-alignment/bulk/history"
          element={<ProtectedRoute><ProfessionalJointAlignmentBulkHistory /></ProtectedRoute>}
        />
        <Route
          path="/share/professional"
          element={<ProtectedRoute><ShareWithProfessional /></ProtectedRoute>}
        />
        <Route
          path="/shared-with-professionals"
          element={<ProtectedRoute><SharedWithProfessionals /></ProtectedRoute>}
        />
        <Route path="/for-portal-engineers" element={<ForPortalEngineers />} />
        <Route path="/admin/professionals" element={<AdminProfessionalsEditor />} />
        <Route path="/joint-agreement/shared/:token" element={<JointAgreementShared />} />
        <Route path="/foundation/shared/:token" element={<FoundationStatementShared />} />
        <Route path="/joint-report/shared/:token" element={<JointReportShared />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/mediator-badge" element={<MediatorBadge />} />
        <Route path="/shared/coparenting/:token" element={<SharedCoParentingReport />} />
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
        <Route path="/legal/app-store-privacy" element={<AppStorePrivacy />} />
        <Route path="/legal/hipaa" element={<HipaaNotice />} />
        <Route path="/legal/privacy-practices" element={<PrivacyPractices />} />
        <Route path="/legal/hb300" element={<Hb300Notice />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/accessibility" element={<Accessibility />} />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="/foundation/demo" element={<FoundationStatementDemo />} />
        <Route path="/data-retention" element={<DataRetention />} />
        <Route path="/account" element={<ProtectedRoute><Account /></ProtectedRoute>} />
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
          path="/nd-risk-assessment"
          element={
            <ProtectedRoute>
              <NDRiskAssessment />
            </ProtectedRoute>
          }
        />
        <Route
          path="/nd-risk-assessment/result/:aid"
          element={
            <ProtectedRoute>
              <NDRiskAssessmentResult />
            </ProtectedRoute>
          }
        />
        <Route
          path="/companion-assessment"
          element={
            <ProtectedRoute>
              <DimensionCompanion />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interventions"
          element={
            <ProtectedRoute>
              <InterventionCompliance />
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
          path="/learning"
          element={
            <ProtectedRoute>
              <LearningCenter />
            </ProtectedRoute>
          }
        />
        <Route
          path="/learning/:hubSlug/:articleSlug"
          element={
            <ProtectedRoute>
              <LearningArticle />
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
          path="/prep/child-goals"
          element={
            <ProtectedRoute>
              <ChildGoals />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2 />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/report"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2Report />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/compare"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2Compare />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/compare/:share_id"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2CompareView />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/educational-deep-dive"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2EducationalDeepDive />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/educational-deep-dive/report"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2EducationalDeepDiveReport />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/educational-deep-dive/compare"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2EducationalDeepDiveCompare />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/educational-deep-dive/compare/:share_id"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2EducationalDeepDiveCompareView />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/psychological-deep-dive"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2PsychologicalDeepDive />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/psychological-deep-dive/report"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2PsychologicalDeepDiveReport />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/psychological-deep-dive/compare"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2PsychologicalDeepDiveCompare />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/psychological-deep-dive/compare/:share_id"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2PsychologicalDeepDiveCompareView />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/medical-deep-dive"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2MedicalDeepDive />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/medical-deep-dive/report"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2MedicalDeepDiveReport />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/medical-deep-dive/compare"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2MedicalDeepDiveCompare />
            </ProtectedRoute>
          }
        />
        <Route
          path="/special-needs-v2/medical-deep-dive/compare/:share_id"
          element={
            <ProtectedRoute>
              <SpecialNeedsV2MedicalDeepDiveCompareView />
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
          <BackToDashboardPill />
          <PreShareConsentHost />
          <Toaster position="bottom-right" toastOptions={TOAST_OPTIONS} />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
