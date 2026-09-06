import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { CircleNav } from "@/components/CircleNav";
import { ArrowLeft } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

export default function Hub() {
  const { user, loading } = useAuth();
  const isPro = user?.role === "professional";

  if (!loading && user && !isPro) return <Navigate to="/dashboard" replace />;

  return (
    <div className="min-h-screen bg-background" data-testid="hub-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="hub-back-link">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <h1 className="text-4xl sm:text-5xl font-semibold text-center" data-testid="hub-heading">Joint Report Builder</h1>
        <p className="text-muted-foreground text-center mt-3 mb-6 max-w-2xl mx-auto" data-testid="hub-subtext">
          Choose the purple circle for a full joint assessment across every subject, or a bubble for one focused area. Family violence assessments are always professional-facilitated.
        </p>
        <CircleNav isPro={isPro} />
      </main>
    </div>
  );
}
