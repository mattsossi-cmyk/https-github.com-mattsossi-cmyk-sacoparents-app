import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import ReportView from "@/pages/ReportView";
import JointNew from "@/pages/JointNew";
import Join from "@/pages/Join";
import JointAssessment from "@/pages/JointAssessment";
import SafetyScreening from "@/pages/SafetyScreening";
import SafetyHub from "@/pages/SafetyHub";
import PrivacyNotice from "@/pages/PrivacyNotice";
import ProfessionalNotice from "@/pages/ProfessionalNotice";
import StartWithSafety, { SEEN_KEY as START_SAFETY_SEEN } from "@/pages/StartWithSafety";
export const PRIVACY_NOTICE_VERSION = "2026-10-10.2";
export const PROFESSIONAL_NOTICE_VERSION = "2026-10-13.1";
import CommunicationReadiness from "@/pages/CommunicationReadiness";
import SafetyResponses from "@/pages/SafetyResponses";
import JointReport from "@/pages/JointReport";
import Hub from "@/pages/Hub";
import CompleteReport from "@/pages/CompleteReport";
import Privacy from "@/pages/Privacy";
import SampleReport from "@/pages/SampleReport";
import Samples from "@/pages/Samples";
import SampleLegalLensReport from "@/pages/SampleLegalLensReport";
import SampleAgreement from "@/pages/SampleAgreement";
import SampleFoundationStatement from "@/pages/SampleFoundationStatement";
import FoundationEditor from "@/pages/FoundationEditor";
import LegalLensReport from "@/pages/LegalLensReport";
import ProfessionalReportHome from "@/pages/ProfessionalReportHome";

function LegalLensRedirect() {
  const { id } = useParams();
  return <Navigate to={`/cases/${id}/professional-report`} replace />;
}
import Legal from "@/pages/Legal";
import AcceptInvite from "@/pages/AcceptInvite";
import Methodology from "@/pages/Methodology";
import Professionals from "@/pages/Professionals";
import FindProfessional from "@/pages/FindProfessional";
import Resources from "@/pages/Resources";
import FamilyMatters from "@/pages/FamilyMatters";
import Verify from "@/pages/Verify";
import CourtPacket from "@/pages/CourtPacket";
import CourtDashboard from "@/pages/CourtDashboard";
import CourtCase from "@/pages/CourtCase";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background" data-testid="auth-loading">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </div>
    );
  }
  if (!user) return <Navigate to="/auth" replace />;
  if (user.privacy_notice_version !== PRIVACY_NOTICE_VERSION && window.location.pathname !== "/privacy-notice") {
    sessionStorage.setItem("post-privacy-redirect", window.location.pathname + window.location.search);
    return <Navigate to="/privacy-notice" replace />;
  }
  if (user.role === "professional" && user.professional_notice_version !== PROFESSIONAL_NOTICE_VERSION && !["/professional-notice", "/privacy-notice"].includes(window.location.pathname)) {
    sessionStorage.setItem("post-pro-notice-redirect", window.location.pathname + window.location.search);
    return <Navigate to="/professional-notice" replace />;
  }
  if (user.role === "parent" && !sessionStorage.getItem(START_SAFETY_SEEN) && window.location.pathname === "/dashboard") {
    return <Navigate to="/start-with-safety" replace />;
  }
  if (user.role === "judge" && !/^\/(court-dashboard|court\/case\/|privacy-notice)/.test(window.location.pathname)) return <Navigate to="/court-dashboard" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
            <Route path="/court-dashboard" element={<Protected><CourtDashboard /></Protected>} />
            <Route path="/court/case/:refId" element={<Protected><CourtCase /></Protected>} />
            <Route path="/court/sample" element={<CourtCase sample />} />
            <Route path="/report/:id" element={<Protected><ReportView /></Protected>} />
            <Route path="/join/:token" element={<Join />} />
            <Route path="/joint/new" element={<Protected><JointNew /></Protected>} />
            <Route path="/joint/:id/assess" element={<Protected><JointAssessment /></Protected>} />
            <Route path="/joint/:id/safety" element={<Protected><SafetyHub /></Protected>} />
            <Route path="/privacy-notice" element={<Protected><PrivacyNotice /></Protected>} />
            <Route path="/professional-notice" element={<Protected><ProfessionalNotice /></Protected>} />
            <Route path="/start-with-safety" element={<Protected><StartWithSafety /></Protected>} />
            <Route path="/joint/:id/communication-readiness" element={<Protected><CommunicationReadiness /></Protected>} />
            <Route path="/joint/:id/safety-screening" element={<Protected><SafetyScreening /></Protected>} />
            <Route path="/joint/:id/safety-screening/:role" element={<Protected><SafetyResponses /></Protected>} />
            <Route path="/joint/:id/legal-report" element={<Protected><LegalLensRedirect /></Protected>} />
            <Route path="/joint/:id/legal-report/sample" element={<Protected><LegalLensRedirect /></Protected>} />
            <Route path="/samples/legal-report" element={<Navigate to="/samples/legal-lens-report" replace />} />
            <Route path="/professional-report" element={<Protected><ProfessionalReportHome /></Protected>} />
            <Route path="/cases/:id/professional-report" element={<Protected><LegalLensReport /></Protected>} />
            <Route path="/joint/:id" element={<Protected><JointReport /></Protected>} />
            <Route path="/hub" element={<Protected><Hub /></Protected>} />
            <Route path="/foundation" element={<Protected><FoundationEditor /></Protected>} />
            <Route path="/hub/complete" element={<Protected><CompleteReport /></Protected>} />
            <Route path="/privacy-policy" element={<Privacy />} />
            {/* Policy page content (frontend/src/content/policies.json + pages/PolicyPage.jsx) is intentionally NOT routed — owner decision 2026-10-11. */}
            <Route path="/sample-mediation" element={<SampleReport fixedKey="mediation" />} />
            <Route path="/samples" element={<Samples />} />
            <Route path="/samples/professional-report" element={<Navigate to="/samples/legal-lens-report" replace />} />
            <Route path="/samples/legal-lens-report" element={<SampleLegalLensReport />} />
            <Route path="/samples/coparenting-agreement" element={<SampleAgreement />} />
            <Route path="/samples/foundation-statement" element={<SampleFoundationStatement />} />
            <Route path="/samples/:key" element={<SampleReport />} />
            <Route path="/legal/:page" element={<Legal />} />
            <Route path="/accept-invite" element={<Protected><AcceptInvite /></Protected>} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/matters" element={<Protected><FamilyMatters /></Protected>} />
            <Route path="/verify" element={<Verify />} />
            <Route path="/court/:token" element={<CourtPacket />} />
            <Route path="/methodology" element={<Methodology />} />
            <Route path="/professionals" element={<Protected><Professionals /></Protected>} />
            <Route path="/find-a-professional" element={<FindProfessional />} />
            <Route path="/find-a-professional/:proId" element={<FindProfessional />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <footer className="py-4 text-center text-xs text-muted-foreground" data-testid="copyright-footer">
            Copyright 2026 SA CoParents. All Rights Reserved. · sacoparentsalign.com
          </footer>
        </BrowserRouter>
        <Toaster position="top-center" />
      </AuthProvider>
    </div>
  );
}

export default App;
