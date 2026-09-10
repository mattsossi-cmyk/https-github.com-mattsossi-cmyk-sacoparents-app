/**
 * `/join` — Manual Alignment Code entry.
 *
 * For parents who didn't receive the invitation email or who prefer to
 * type the visible SA-XXXXXX code. Requires auth — the code alone is
 * never sufficient (email-match guard on the backend).
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ShieldCheck,
  Loader2,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const ASSESSMENT_LABELS = {
  "co-parenting": "Co-Parenting Assessment",
  communication: "Communication Assessment",
  educational: "Educational Needs Assessment",
  medical: "Medical Needs Assessment",
  psychological: "Psychological / Emotional Needs Assessment",
  "special-needs": "Special Needs Assessment",
};

const ASSESSMENT_ROUTES = {
  "co-parenting": "/special-needs-v2",
  communication: "/communication",
  educational: "/edu-deep",
  medical: "/med-deep",
  psychological: "/psych-deep",
  "special-needs": "/special-needs-v2",
};

export default function JoinCode() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [linked, setLinked] = useState(null);
  const [error, setError] = useState(null);
  const isSignedIn = !!user;

  // Pre-fill the code input from `?code=` — the Landing page's Path B
  // deep-link passes the code the parent typed there, so we don't
  // make them retype it after login.
  useEffect(() => {
    const fromUrl = (searchParams.get("code") || "").trim();
    if (fromUrl) setCode(fromUrl.toUpperCase());
  }, [searchParams]);

  const submit = async (e) => {
    e.preventDefault();
    if (!isSignedIn) {
      navigate(`/login?redirect=${encodeURIComponent("/join")}`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      // Session cookie sent automatically via api.withCredentials.
      const r = await api.post("/joint-alignment/manual-code", { code });
      setLinked(r.data);
      toast.success("Alignment code linked");
    } catch (err) {
      const status = err?.response?.status ?? 0;
      const detail = err?.response?.data?.detail || "";
      if (status === 403) setError({ code: 403, msg: detail });
      else if (status === 404) setError({ code: 404, msg: "Case not found or expired" });
      else if (status === 409) setError({ code: 409, msg: detail });
      else if (status) setError({ code: status, msg: detail || "Something went wrong" });
      else setError({ code: 0, msg: "Network error" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div
        className="max-w-2xl mx-auto px-4 sm:px-6 py-10 sm:py-14"
        data-testid="join-code-page"
      >
        <div className="rounded-3xl bg-white border border-[#E5E0EE] p-6 sm:p-10 shadow-sm">
          <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
            Joint Alignment
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
            I have an Alignment Code
          </h1>
          <p className="text-[#4B4567] mt-3 leading-relaxed">
            Enter the <code className="font-mono text-[#3D1A78]">SA-XXXXXX</code>{" "}
            code from your invitation email. We&rsquo;ll match it to the
            account you&rsquo;re signed in with.
          </p>

          {!linked && (
            <form onSubmit={submit} className="mt-6">
              <label
                htmlFor="join-code-input"
                className="text-[11px] uppercase tracking-[0.14em] font-bold text-[#857E9C]"
              >
                Alignment Code
              </label>
              <input
                id="join-code-input"
                type="text"
                inputMode="numeric"
                autoComplete="off"
                spellCheck="false"
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="SA-482731"
                className="mt-1 block w-full text-2xl font-mono tracking-widest rounded-xl border-2 border-[#E5E0EE] focus:border-[#3D1A78] focus:ring-2 focus:ring-[#3D1A78]/20 px-4 py-3 outline-none transition"
                data-testid="join-code-input"
              />

              <div className="mt-4 rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-4 flex gap-3 items-start text-[13.5px] text-[#4B4567] leading-relaxed">
                <ShieldCheck
                  size={18}
                  className="text-[#3D1A78] flex-shrink-0 mt-0.5"
                />
                <p className="!m-0">
                  Entering a code alone is never enough to see anything —
                  we&rsquo;ll only link the case if this code was issued for
                  the email address on your SA CoParents account.
                </p>
              </div>

              {error && (
                <div
                  className="mt-4 rounded-xl border border-[#F5C5C5] bg-[#FDECEC] p-3 flex items-start gap-2 text-[13px] text-[#8F1D24]"
                  data-testid="join-code-error"
                >
                  <AlertTriangle size={15} className="flex-shrink-0 mt-0.5" />
                  <span>{error.msg}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={submitting || !code}
                className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-6 py-3 text-sm font-semibold hover:bg-[#2A0F5F] transition disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="join-code-submit"
              >
                {submitting && <Loader2 className="animate-spin" size={16} />}
                Link my account
                <ArrowRight size={14} />
              </button>
            </form>
          )}

          {linked && (
            <div
              className="mt-6 rounded-2xl border-2 border-[#1E7A55] bg-[#F1F9F4] p-5"
              data-testid="join-code-linked"
            >
              <h2 className="font-serif text-xl text-[#1A1330] flex items-center gap-2">
                <CheckCircle2 size={18} className="text-[#1E7A55]" />
                You&rsquo;re linked to case {linked.case_id}
              </h2>
              <p className="text-[13.5px] text-[#4B4567] mt-2 leading-relaxed">
                Assessment:{" "}
                <strong>
                  {ASSESSMENT_LABELS[linked.assessment_type] ||
                    linked.assessment_type}
                </strong>
                <br />
                Requested by:{" "}
                <strong>{linked.professional?.name || "your professional"}</strong>
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() =>
                    navigate(ASSESSMENT_ROUTES[linked.assessment_type] || "/dashboard")
                  }
                  className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
                >
                  Start My Assessment
                  <ArrowRight size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => navigate("/dashboard")}
                  className="rounded-full border border-[#E5E0EE] text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:border-[#3D1A78] transition"
                >
                  Go to my dashboard
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
