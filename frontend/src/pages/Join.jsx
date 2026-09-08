import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Mail } from "lucide-react";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { ConfidentialityNotice } from "@/components/ConfidentialityNotice";
import { Button } from "@/components/ui/button";

export default function Join() {
  const { token } = useParams();
  const { user, loading } = useAuth();
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get(`/joint/invitations/lookup/${token}`)
      .then((r) => setInfo(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [token]);

  const accept = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/joint/invitations/accept", { code: token });
      toast.success("Invitation accepted");
      navigate(`/joint/${data.report_id}/assess`);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background" data-testid="join-page">
      <header className="max-w-6xl mx-auto px-6 py-6">
        <Link to="/" className="w-fit block" data-testid="join-brand-link">
          <BrandLogo />
        </Link>
      </header>
      <main className="max-w-xl mx-auto px-6 py-10">
        {error ? (
          <div className="bg-white border border-border rounded-lg p-8 text-center" data-testid="join-error">
            <p className="text-lg font-medium">{error}</p>
            <Link to="/dashboard" className="inline-block mt-6">
              <Button variant="outline" data-testid="join-error-dash-btn">Go to dashboard</Button>
            </Link>
          </div>
        ) : !info ? (
          <p className="text-muted-foreground text-center" data-testid="join-loading">Loading invitation…</p>
        ) : (
          <div className="bg-white border border-border rounded-lg p-8" data-testid="invitation-card">
            <Mail className="h-10 w-10 text-primary mb-4" />
            <h1 className="text-3xl font-semibold mb-4" data-testid="invitation-heading">You've been invited</h1>
            <p className="text-muted-foreground leading-relaxed">
              You've been invited to participate in an SA CoParents Joint Report.
            </p>
            <p className="mt-4 leading-relaxed">
              <strong>{info.inviter_name}</strong>{info.professional_verified && <> <VerifiedBadge testId="invite-pro-verified-badge" className="align-middle" /></>} has invited you to independently provide your perspective
              regarding <strong>{info.child_name}</strong> on the subject of <strong>{info.subject_label}</strong>.
            </p>
            <p className="mt-4 text-sm text-muted-foreground leading-relaxed" data-testid="invitation-privacy">
              Your individual answers remain private. SA CoParents will compare the parents' completed
              responses to identify areas of alignment, differences in perspective, child-focused concerns,
              and possible options for discussion.
            </p>
            <div className="mt-6">
              <ConfidentialityNotice />
            </div>
            {loading ? (
              <p className="mt-6 text-sm text-muted-foreground">Checking your session…</p>
            ) : user ? (
              <div className="mt-8">
                <Button className="w-full h-12" onClick={accept} disabled={busy} data-testid="accept-invitation-btn">
                  {busy ? "Accepting…" : "Accept Invitation"}
                </Button>
                <p className="mt-3 text-xs text-muted-foreground text-center">
                  Signed in as {user.email}. This invitation was sent to {info.invitee_email}.
                </p>
              </div>
            ) : (
              <div className="mt-8 space-y-3">
                <Link to={`/auth?next=/join/${token}`} data-testid="join-signin-link">
                  <Button className="w-full h-12" data-testid="join-signin-btn">Sign in to accept</Button>
                </Link>
                <Link to={`/auth?mode=register&next=/join/${token}`} className="block" data-testid="join-register-link">
                  <Button variant="outline" className="w-full h-12" data-testid="join-register-btn">Create your free parent account</Button>
                </Link>
                <p className="text-xs text-muted-foreground text-center">
                  Use <strong>{info.invitee_email}</strong> — the email this invitation was sent to.
                </p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
