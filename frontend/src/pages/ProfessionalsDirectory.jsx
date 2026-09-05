/**
 * `/professionals` — Directory of professionals a parent can send a
 * Joint Alignment code to.
 *
 * Flow:
 *   1. Parent lands here (typically after completing an assessment).
 *   2. Picks a professional card.
 *   3. Picks the assessment type + optional short message.
 *   4. Confirms → App mints an alignment code and emails the
 *      professional. Code also shown on-screen as a backup.
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  Mail,
  MapPin,
  Send,
  Loader2,
  CheckCircle2,
  Copy,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

const ASSESSMENT_OPTIONS = [
  { value: "co-parenting", label: "Co-Parenting" },
  { value: "communication", label: "Communication" },
  { value: "educational", label: "Educational Needs" },
  { value: "medical", label: "Medical Needs" },
  { value: "psychological", label: "Psychological / Emotional" },
  { value: "special-needs", label: "Special Needs" },
];

function getAuthToken() {
  try {
    return localStorage.getItem("token");
  } catch {
    return null;
  }
}

export default function ProfessionalsDirectory() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preselectedType = params.get("assessment") || "";
  const [professionals, setProfessionals] = useState(null);
  const [error, setError] = useState(null);
  const [chosen, setChosen] = useState(null);
  const [assessmentType, setAssessmentType] = useState(preselectedType);
  const [parentMessage, setParentMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API}/professionals`);
        const body = await r.json();
        if (cancelled) return;
        if (r.ok) setProfessionals(body.professionals || []);
        else setError(body.detail || "Failed to load professionals");
      } catch (e) {
        if (!cancelled) setError("Network error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    const t = getAuthToken();
    if (!t) {
      navigate(
        `/login?redirect=${encodeURIComponent("/professionals")}`
      );
      return;
    }
    if (!chosen || !assessmentType) return;
    setSending(true);
    try {
      const r = await fetch(
        `${API}/professionals/${chosen.professional_id}/send-alignment-code`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${t}`,
          },
          body: JSON.stringify({
            assessment_type: assessmentType,
            parent_message: parentMessage || null,
          }),
        }
      );
      const body = await r.json();
      if (r.ok) {
        setSent(body);
        if (body.delivered)
          toast.success(`Alignment code sent to ${chosen.name}`);
        else toast.warning(body.delivered_error || "Code minted — email delivery not confirmed");
      } else if (r.status === 429) {
        toast.error(body.detail);
      } else {
        toast.error(body.detail || "Could not send code");
      }
    } catch (e) {
      toast.error("Network error");
    } finally {
      setSending(false);
    }
  };

  const copyCode = async (code) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success("Code copied");
    } catch {
      toast.error("Copy failed");
    }
  };

  return (
    <AppShell>
      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12"
        data-testid="professionals-directory-page"
      >
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="inline-flex items-center gap-2 text-sm text-[#3D1A78] hover:text-[#2A0F5F] mb-6"
        >
          <ArrowLeft size={14} /> Back to dashboard
        </button>

        <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
          Send my alignment code to a professional
        </div>
        <h1
          className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight"
          data-testid="professionals-directory-title"
        >
          Pick a professional to prepare your Joint Alignment Report
        </h1>
        <p className="text-[#4B4567] mt-3 max-w-2xl leading-relaxed">
          We&rsquo;ll email them a fresh Alignment Code. Individual
          responses remain private — the professional prepares the joint
          report only after both parents have completed the same
          assessment.
        </p>

        {!sent && (
          <>
            {professionals === null && !error && (
              <div className="mt-8 flex items-center gap-2 text-[#4B4567] text-sm">
                <Loader2 className="animate-spin" size={16} />
                Loading directory…
              </div>
            )}
            {error && (
              <div className="mt-8 text-[13px] text-[#8F1D24]">{error}</div>
            )}
            {professionals && professionals.length > 0 && (
              <div
                className="mt-8 grid grid-cols-1 gap-4"
                data-testid="professionals-list"
              >
                {professionals.map((p) => (
                  <ProfessionalCard
                    key={p.professional_id}
                    professional={p}
                    selected={chosen?.professional_id === p.professional_id}
                    onSelect={() => setChosen(p)}
                  />
                ))}
              </div>
            )}

            {chosen && (
              <form
                onSubmit={submit}
                className="mt-8 rounded-3xl border-2 border-[#3D1A78] bg-white p-5 sm:p-6"
                data-testid="professionals-send-form"
              >
                <h2 className="font-serif text-2xl text-[#1A1330] leading-tight">
                  Send to <span className="text-[#3D1A78]">{chosen.name}</span>
                </h2>

                <label className="block mt-5">
                  <span className="text-[11px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
                    Which assessment?
                  </span>
                  <select
                    value={assessmentType}
                    onChange={(e) => setAssessmentType(e.target.value)}
                    required
                    className="mt-1 block w-full rounded-xl border-2 border-[#E5E0EE] focus:border-[#3D1A78] px-4 py-2.5 text-sm outline-none transition"
                    data-testid="professionals-assessment-select"
                  >
                    <option value="">Select an assessment…</option>
                    {ASSESSMENT_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block mt-5">
                  <span className="text-[11px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
                    Optional short message to the professional
                  </span>
                  <textarea
                    value={parentMessage}
                    onChange={(e) => setParentMessage(e.target.value)}
                    rows={3}
                    maxLength={1000}
                    placeholder="Anything they should know before opening the case…"
                    className="mt-1 block w-full rounded-xl border-2 border-[#E5E0EE] focus:border-[#3D1A78] px-4 py-2.5 text-sm outline-none transition resize-none"
                    data-testid="professionals-parent-message"
                  />
                </label>

                <div className="mt-4 rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-4 flex gap-3 items-start text-[13px] text-[#4B4567] leading-relaxed">
                  <ShieldCheck
                    size={16}
                    className="text-[#3D1A78] flex-shrink-0 mt-0.5"
                  />
                  <p className="!m-0">
                    Your individual answers stay private. The professional
                    receives only the Alignment Code, your name, and any
                    message you type above. They must open a Joint Alignment
                    Case on their side to see the assessment payload — and
                    then only after your co-parent has completed the same
                    assessment.
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={sending || !assessmentType}
                  className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-6 py-3 text-sm font-semibold hover:bg-[#2A0F5F] transition disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="professionals-send-submit"
                >
                  {sending && <Loader2 className="animate-spin" size={16} />}
                  <Send size={14} />
                  Send alignment code
                </button>
              </form>
            )}
          </>
        )}

        {sent && (
          <div
            className="mt-8 rounded-3xl border-2 border-[#1E7A55] bg-[#F1F9F4] p-5 sm:p-6"
            data-testid="professionals-sent-confirmation"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] flex items-center gap-2">
              <CheckCircle2 size={20} className="text-[#1E7A55]" />
              {sent.delivered
                ? `Code sent to ${sent.professional.name}`
                : `Code minted for ${sent.professional.name}`}
            </h2>
            {!sent.delivered && (
              <div className="mt-3 rounded-xl border border-[#F1D9B7] bg-[#FFF6EA] p-3 flex items-start gap-2 text-[13px] text-[#8A4610]">
                <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                <span>
                  {sent.delivered_error ||
                    "We couldn't confirm email delivery. Please copy the code below and share it directly."}
                </span>
              </div>
            )}
            <p className="text-[13.5px] text-[#4B4567] mt-3 leading-relaxed">
              Backup — share this Alignment Code with{" "}
              <strong>{sent.professional.name}</strong> in case the email
              didn&rsquo;t land in their inbox. It expires 15 minutes after
              minting.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <code
                className="text-2xl font-mono tracking-widest text-[#3D1A78] bg-white border border-[#E5E0EE] rounded-xl px-4 py-2"
                data-testid="professionals-sent-code"
              >
                {sent.code}
              </code>
              <button
                type="button"
                onClick={() => copyCode(sent.code)}
                className="inline-flex items-center gap-2 rounded-full border border-[#E5E0EE] text-[#3D1A78] px-4 py-2 text-[13px] font-semibold hover:border-[#3D1A78] transition"
                data-testid="professionals-copy-code"
              >
                <Copy size={13} />
                Copy code
              </button>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => {
                  setSent(null);
                  setChosen(null);
                  setAssessmentType("");
                  setParentMessage("");
                }}
                className="rounded-full border border-[#E5E0EE] text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:border-[#3D1A78] transition"
              >
                Send to another professional
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
              >
                Back to dashboard
              </button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function ProfessionalCard({ professional, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`text-left rounded-3xl border-2 bg-white p-5 transition ${
        selected
          ? "border-[#3D1A78] shadow-lg"
          : "border-[#E5E0EE] hover:border-[#3D1A78] hover:shadow-md"
      }`}
      data-testid={`professionals-card-${professional.professional_id}`}
    >
      <div className="flex flex-wrap items-start gap-4">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#5A2FA0] text-white grid place-items-center text-lg font-serif flex-shrink-0">
          {(professional.name || "?")
            .split(" ")
            .map((w) => w[0])
            .filter(Boolean)
            .slice(0, 2)
            .join("")
            .toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-serif text-xl text-[#1A1330] leading-tight">
            {professional.name}
          </div>
          <div className="text-[13px] text-[#4B4567] mt-1 leading-snug">
            {professional.credentials}
          </div>
          {professional.license && (
            <div className="text-[12px] text-[#857E9C] italic mt-0.5 leading-snug">
              {professional.license}
            </div>
          )}
          {professional.bio && (
            <p className="text-[13px] text-[#4B4567] mt-2 leading-relaxed">
              {professional.bio}
            </p>
          )}
          <div className="mt-3 flex flex-col gap-1 text-[12.5px] text-[#4B4567]">
            {professional.email && (
              <div className="flex items-center gap-1.5">
                <Mail size={12} className="text-[#3D1A78]" />
                <span>{professional.email}</span>
              </div>
            )}
            {professional.address_lines?.length > 0 && (
              <div className="flex items-start gap-1.5">
                <MapPin size={12} className="text-[#3D1A78] mt-0.5" />
                <span>
                  {professional.address_lines.join(", ")}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
