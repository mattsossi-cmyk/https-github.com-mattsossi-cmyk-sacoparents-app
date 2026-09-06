import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import ReportView from "@/pages/ReportView";
import JointNew from "@/pages/JointNew";
import Join from "@/pages/Join";
import JointAssessment from "@/pages/JointAssessment";
import JointReport from "@/pages/JointReport";
import Hub from "@/pages/Hub";
import CompleteReport from "@/pages/CompleteReport";
import Privacy from "@/pages/Privacy";
import SampleMediation from "@/pages/SampleMediation";
import Resources from "@/pages/Resources";

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
            <Route path="/report/:id" element={<Protected><ReportView /></Protected>} />
            <Route path="/join/:token" element={<Join />} />
            <Route path="/joint/new" element={<Protected><JointNew /></Protected>} />
            <Route path="/joint/:id/assess" element={<Protected><JointAssessment /></Protected>} />
            <Route path="/joint/:id" element={<Protected><JointReport /></Protected>} />
            <Route path="/hub" element={<Protected><Hub /></Protected>} />
            <Route path="/hub/complete" element={<Protected><CompleteReport /></Protected>} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/sample-mediation" element={<SampleMediation />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-center" />
      </AuthProvider>
    </div>
  );
}

export default App;
