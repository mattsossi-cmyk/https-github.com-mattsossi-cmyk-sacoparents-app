import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "@/lib/api";

// Stable alias for the parent app: /check-in or /check-in?case=SA-XXXXXX → the signed-in parent's own Family check-in.
export default function CheckInAlias({ to = "check-in" }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const code = params.get("case");

  useEffect(() => {
    api.get("/me/check-in", { params: code ? { case: code } : {} })
      .then(({ data }) => navigate(to === "hub" ? `/joint/${data.report_id}/safety#who-looked` : data.path, { replace: true }))
      .catch((e) => setError(e?.response?.data?.detail || "We could not find your check-in."));
  }, [code, navigate, to]);

  return (
    <main className="mx-auto max-w-md px-4 py-16 text-center" data-testid="check-in-alias">
      {error ? (
        <>
          <p className="text-sm text-muted-foreground" data-testid="check-in-alias-error">{error}</p>
          <Link to="/dashboard" className="mt-4 inline-block text-sm font-semibold text-brand-purple underline underline-offset-2" data-testid="check-in-alias-home">Go to your home screen</Link>
        </>
      ) : (
        <p className="text-sm text-muted-foreground" data-testid="check-in-alias-loading">Opening…</p>
      )}
    </main>
  );
}
