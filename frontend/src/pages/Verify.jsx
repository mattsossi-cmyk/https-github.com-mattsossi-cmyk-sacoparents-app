import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, ShieldCheck, BadgeCheck, Search, AlertCircle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { VerifiedBadge } from "@/components/VerifiedBadge";

export default function Verify() {
  const [params] = useSearchParams();
  const [code, setCode] = useState(params.get("code") || "");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const check = async (e) => {
    e?.preventDefault();
    setBusy(true); setError(""); setResult(null);
    try {
      const { data } = await api.get(`/verify/${encodeURIComponent(code.trim())}`);
      setResult(data);
    } catch (err) { setError(formatApiError(err)); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-background" data-testid="verify-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="verify-back-link"><ArrowLeft className="h-4 w-4" /> Home</Link>
          <BrandLogo size="text-xl" />
          <span className="w-16" />
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-12">
        <div className="flex items-center gap-3 text-brand-teal mb-3"><ShieldCheck className="h-7 w-7" /><p className="text-xs uppercase tracking-widest font-bold">For Parents</p></div>
        <h1 className="text-4xl font-semibold" data-testid="verify-heading">Confirm Your Professional</h1>
        <p className="text-muted-foreground mt-3 max-w-xl">Received an invitation? Enter the case code from your email to confirm the professional who sent it holds an approved SA CoParents Align account and whether their license or credentials have been verified.</p>
        <form onSubmit={check} className="mt-8 flex gap-2 max-w-md" data-testid="verify-form">
          <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="e.g. SA-EDU-482731" className="h-12 tracking-[0.2em] uppercase font-semibold" maxLength={20} data-testid="verify-code-input" />
          <Button type="submit" disabled={code.trim().length < 6 || busy} className="h-12 gap-2" data-testid="verify-submit-btn"><Search className="h-4 w-4" /> {busy ? "Checking…" : "Check"}</Button>
        </form>
        {error && <p className="mt-4 text-sm text-destructive flex items-center gap-2" data-testid="verify-error"><AlertCircle className="h-4 w-4" /> {error}</p>}
        {result && (
          <div className="mt-8 bg-white border-2 border-primary/30 rounded-lg p-6" data-testid="verify-result">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">Case {result.case_code} · {result.subject_label}</p>
            <h2 className="text-2xl font-semibold mt-2 flex items-center gap-3 flex-wrap" data-testid="verify-pro-name">{result.professional_name}{result.credentials_verified && <VerifiedBadge testId="verify-verified-badge" />}</h2>
            {(result.professional_role || result.organization) && <p className="text-sm text-muted-foreground mt-1" data-testid="verify-pro-details">{[result.professional_role, result.organization].filter(Boolean).join(" · ")}</p>}
            <ul className="mt-5 space-y-2 text-sm">
              <li className="flex items-center gap-2" data-testid="verify-approved-row"><BadgeCheck className={`h-4 w-4 ${result.account_approved ? "text-align-green" : "text-muted-foreground"}`} /> Approved professional account: <strong>{result.account_approved ? "Yes" : "Pending review"}</strong></li>
              <li className="flex items-center gap-2" data-testid="verify-credentials-row"><BadgeCheck className={`h-4 w-4 ${result.credentials_verified ? "text-align-green" : "text-muted-foreground"}`} /> License / credentials verified by SA CoParents: <strong>{result.credentials_verified ? "Yes" : "Not yet verified"}</strong></li>
              <li className="flex items-center gap-2" data-testid="verify-active-row"><BadgeCheck className={`h-4 w-4 ${result.case_active ? "text-align-green" : "text-muted-foreground"}`} /> Case status: <strong>{result.case_active ? "Active" : "Closed / archived"}</strong></li>
            </ul>
            <p className="text-xs text-muted-foreground mt-5">This check shows only the professional's account standing. It never reveals the other parent's information or any assessment responses. If anything looks wrong, do not proceed — contact the professional directly using contact details you already trust.</p>
          </div>
        )}
      </main>
    </div>
  );
}
