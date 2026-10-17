/**
 * ShareWithProfessional — 5-step wizard for inviting a professional
 * to review the parent's SELECTED reports on sacoparentsalign.com.
 *
 * Steps:
 *   1. Select the professional (name / email / role / etc.)
 *   2. Select reports (multi-check from the caller's completed set)
 *   3. Set access (view-only vs download, notify toggles, expiration)
 *   4. Review consent (two explicit unchecked boxes with verbatim copy)
 *   5. Confirmation with next-step CTAs
 *
 * Backed by:
 *   GET  /api/parent/report-catalog
 *   POST /api/parent/professional-invitations
 */
import { useEffect, useMemo, useState } from "react";
import { ProSeeLink } from "../components/privacy/ProSeeLink";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, ShieldCheck, Loader2, CheckCircle2,
  Send, Users, FileText, Calendar, MessageSquare, AlertCircle, Eye,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const ROLES = [
  { value: "mediator",                 label: "Mediator" },
  { value: "attorney",                 label: "Attorney" },
  { value: "therapist",                label: "Therapist / Counselor" },
  { value: "counselor",                label: "Counselor" },
  { value: "parenting-facilitator",    label: "Parenting Facilitator / Coordinator" },
  { value: "amicus-attorney",          label: "Amicus Attorney" },
  { value: "child-advocate",           label: "Child Advocate" },
  { value: "educational-professional", label: "Educational Professional" },
  { value: "medical-professional",     label: "Medical Professional" },
  { value: "other",                    label: "Other approved professional" },
];

const ACCESS_OPTIONS = [
  { days: 7,  label: "7 days" },
  { days: 30, label: "30 days · Recommended" },
  { days: 60, label: "60 days" },
  { days: 90, label: "90 days" },
];

const EMPTY_FORM = {
  professional_first_name: "",
  professional_last_name: "",
  professional_email: "",
  professional_email_confirm: "",
  professional_role: "mediator",
  organization: "",
  professional_phone: "",
  reference_number: "",
  personal_message: "",
  report_ids: [],
  view_permission: true,
  download_permission: false,
  notify_on_view: true,
  notify_on_download: true,
  future_versions: false,
  access_days: 30,
  consent_authorised: false,
  consent_relationship_acknowledged: false,
};

function Stepper({ step }) {
  const steps = ["Professional", "Reports", "Access", "Consent", "Sent"];
  return (
    <ol className="flex items-center gap-1 flex-wrap mb-8" data-testid="wizard-stepper" aria-label="Progress">
      {steps.map((label, i) => {
        const idx = i + 1;
        const done = idx < step;
        const active = idx === step;
        return (
          <li key={label} className="flex items-center gap-1">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-semibold ${
                active
                  ? "bg-[#3D1A78] text-white"
                  : done
                  ? "bg-[#E6F4EC] text-[#1F5C3B]"
                  : "bg-[#F1EEF7] text-[#6E6787]"
              }`}
              aria-current={active ? "step" : undefined}
              data-testid={`wizard-step-${idx}`}
              data-active={active ? "true" : "false"}
              data-done={done ? "true" : "false"}
            >
              {done ? <CheckCircle2 size={11} /> : <span className="font-mono">{idx}</span>}
              {label}
            </span>
            {idx < steps.length && <span className="text-[#D6CFE8] px-0.5">→</span>}
          </li>
        );
      })}
    </ol>
  );
}

function Field({ label, htmlFor, required, hint, children, testid }) {
  return (
    <div data-testid={testid}>
      <label
        htmlFor={htmlFor}
        className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] block"
      >
        {label}{required && <span className="text-[#9A3A23] ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1 text-[11px] text-[#6E6787]">{hint}</p>}
    </div>
  );
}

const inputCls =
  "mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]";

export default function ShareWithProfessional() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(EMPTY_FORM);
  const [catalog, setCatalog] = useState(null);   // null=loading, []=empty
  const [catalogError, setCatalogError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const update = (patch) => setForm((f) => ({ ...f, ...patch }));

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get("/parent/report-catalog");
        if (!cancelled) setCatalog(r.data?.reports || []);
      } catch (err) {
        logError("parent report catalog fetch failed", err);
        if (!cancelled) {
          setCatalogError("Couldn't load your completed reports.");
          setCatalog([]);
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const stepErrors = useMemo(() => {
    if (step === 1) {
      if (!form.professional_first_name.trim()) return "First name is required.";
      if (!form.professional_last_name.trim())  return "Last name is required.";
      if (!form.professional_email.trim())      return "Email is required.";
      if (form.professional_email.trim().toLowerCase() !== form.professional_email_confirm.trim().toLowerCase()) {
        return "Email addresses don't match.";
      }
      if (!form.professional_role)              return "Please pick a role.";
    }
    if (step === 2) {
      if (form.report_ids.length === 0) return "Pick at least one report to share.";
    }
    if (step === 4) {
      if (!form.consent_authorised)
        return "Please review and check the authorization box.";
      if (!form.consent_relationship_acknowledged)
        return "Please check the professional-relationship acknowledgement.";
    }
    return null;
  }, [form, step]);

  const goNext = () => {
    if (stepErrors) {
      toast.error(stepErrors);
      return;
    }
    if (step < 4) setStep(step + 1);
  };
  const goBack = () => setStep(Math.max(1, step - 1));

  const handleSubmit = async () => {
    if (stepErrors) { toast.error(stepErrors); return; }
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        professional_email: form.professional_email.trim().toLowerCase(),
        professional_email_confirm: form.professional_email_confirm.trim().toLowerCase(),
        professional_first_name: form.professional_first_name.trim(),
        professional_last_name: form.professional_last_name.trim(),
        organization: form.organization.trim() || undefined,
        professional_phone: form.professional_phone.trim() || undefined,
        reference_number: form.reference_number.trim() || undefined,
        personal_message: form.personal_message.trim() || undefined,
      };
      const r = await api.post("/parent/professional-invitations", payload);
      setResult(r.data);
      setStep(5);
      toast.success("Your invitation has been sent.");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Couldn't send the invitation.";
      logError("parent-pro invite submit failed", err);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleReport = (report_id) => {
    setForm((f) => {
      const has = f.report_ids.includes(report_id);
      return {
        ...f,
        report_ids: has
          ? f.report_ids.filter((x) => x !== report_id)
          : [...f.report_ids, report_id],
      };
    });
  };

  const selectedReports = useMemo(() => {
    const c = catalog || [];
    return c.filter((r) => form.report_ids.includes(r.report_id));
  }, [catalog, form.report_ids]);

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10" data-testid="share-with-professional-page">
        <Link
          to="/shared-with-professionals"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="share-with-pro-back-link"
        >
          <ArrowLeft size={14} /> Back
        </Link>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
          <ShieldCheck size={12} /> Share with purpose. Stay in control.
        </div>
        <h1
          className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-1"
          data-testid="share-with-pro-title"
        >
          Invite a professional
        </h1>
        <p className="text-[#4B4567] mt-3 leading-relaxed">
          Securely share the SA CoParents reports <em>you choose</em> with your
          mediator, attorney, therapist, or other family professional. Your
          raw answers, journal, AI Coach conversations, and unselected reports
          stay private.
        </p>
        <ProSeeLink testid="share-with-pro-pros-see-link" className="text-sm mt-2" />

        <Stepper step={step} />

        {/* ---------- Step 1: Professional ---------- */}
        {step === 1 && (
          <section
            className="rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
            data-testid="share-step-professional"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-4 flex items-center gap-2">
              <Users size={18} className="text-[#3D1A78]" /> Who are you inviting?
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="First name" htmlFor="pro-first" required testid="field-pro-first">
                <input id="pro-first" type="text" className={inputCls}
                  value={form.professional_first_name}
                  onChange={(e) => update({ professional_first_name: e.target.value })}
                  maxLength={80}
                  data-testid="pro-first-input" />
              </Field>
              <Field label="Last name" htmlFor="pro-last" required testid="field-pro-last">
                <input id="pro-last" type="text" className={inputCls}
                  value={form.professional_last_name}
                  onChange={(e) => update({ professional_last_name: e.target.value })}
                  maxLength={80}
                  data-testid="pro-last-input" />
              </Field>
              <Field label="Email" htmlFor="pro-email" required testid="field-pro-email">
                <input id="pro-email" type="email" className={inputCls}
                  value={form.professional_email}
                  onChange={(e) => update({ professional_email: e.target.value })}
                  maxLength={160}
                  autoComplete="off"
                  data-testid="pro-email-input" />
              </Field>
              <Field label="Confirm email" htmlFor="pro-email-confirm" required testid="field-pro-email-confirm"
                hint="The secure link will be tied to this email.">
                <input id="pro-email-confirm" type="email" className={inputCls}
                  value={form.professional_email_confirm}
                  onChange={(e) => update({ professional_email_confirm: e.target.value })}
                  maxLength={160}
                  autoComplete="off"
                  onPaste={(e) => e.preventDefault()}
                  data-testid="pro-email-confirm-input" />
              </Field>
              <Field label="Role" htmlFor="pro-role" required testid="field-pro-role">
                <select id="pro-role" className={inputCls}
                  value={form.professional_role}
                  onChange={(e) => update({ professional_role: e.target.value })}
                  data-testid="pro-role-select">
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </Field>
              <Field label="Organization / Practice" htmlFor="pro-org" testid="field-pro-org">
                <input id="pro-org" type="text" className={inputCls}
                  value={form.organization}
                  onChange={(e) => update({ organization: e.target.value })}
                  maxLength={160}
                  data-testid="pro-org-input" />
              </Field>
              <Field label="Phone (optional)" htmlFor="pro-phone" testid="field-pro-phone">
                <input id="pro-phone" type="tel" className={inputCls}
                  value={form.professional_phone}
                  onChange={(e) => update({ professional_phone: e.target.value })}
                  maxLength={40}
                  data-testid="pro-phone-input" />
              </Field>
              <Field label="Case / reference number (optional)" htmlFor="pro-ref" testid="field-pro-ref">
                <input id="pro-ref" type="text" className={inputCls}
                  value={form.reference_number}
                  onChange={(e) => update({ reference_number: e.target.value })}
                  maxLength={80}
                  data-testid="pro-ref-input" />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Personal message (optional)" htmlFor="pro-msg" testid="field-pro-msg"
                  hint="Included in the invitation email — never contains report content.">
                  <textarea id="pro-msg" rows={3} className={inputCls}
                    value={form.personal_message}
                    onChange={(e) => update({ personal_message: e.target.value })}
                    maxLength={1000}
                    data-testid="pro-msg-input" />
                </Field>
              </div>
            </div>
          </section>
        )}

        {/* ---------- Step 2: Reports ---------- */}
        {step === 2 && (
          <section
            className="rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
            data-testid="share-step-reports"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-2 flex items-center gap-2">
              <FileText size={18} className="text-[#3D1A78]" /> Which reports?
            </h2>
            <p className="text-sm text-[#4B4567] mb-4">
              Only completed reports appear here. Each report must be selected
              individually — there&rsquo;s no "share everything" default.
            </p>
            {catalog === null && (
              <div className="text-center text-[#6E6787] text-sm py-8" data-testid="reports-loading">
                <Loader2 size={16} className="inline animate-spin mr-2" />
                Loading your completed reports…
              </div>
            )}
            {catalogError && (
              <div role="alert" className="rounded-xl bg-[#FCE3DC] border border-[#F5D0C5] text-[#9A3A23] px-3 py-2 text-sm">
                {catalogError}
              </div>
            )}
            {catalog !== null && catalog.length === 0 && !catalogError && (
              <div className="rounded-2xl border border-[#E5E0EE] bg-[#FBF9FE] p-6 text-center" data-testid="reports-empty">
                <AlertCircle size={20} className="mx-auto text-[#6E6787] mb-2" />
                <p className="text-sm text-[#4B4567]">
                  You haven&rsquo;t completed any shareable reports yet. Finish
                  a reflection first — then come back here.
                </p>
              </div>
            )}
            {catalog !== null && catalog.length > 0 && (
              <ul className="space-y-2">
                {catalog.map((r) => {
                  const checked = form.report_ids.includes(r.report_id);
                  return (
                    <li key={r.report_id}>
                      <label
                        className={`flex items-start gap-3 rounded-2xl border p-4 cursor-pointer transition-colors ${
                          checked
                            ? "border-[#3D1A78] bg-[#F5F1FB]"
                            : "border-[#E5E0EE] bg-white hover:bg-[#FAF8FD]"
                        }`}
                        data-testid={`report-card-${r.lane}`}
                      >
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 accent-[#3D1A78]"
                          checked={checked}
                          onChange={() => toggleReport(r.report_id)}
                          data-testid={`report-check-${r.lane}`}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-semibold text-[#1A1330]">{r.title}</div>
                          <p className="text-[12px] text-[#4B4567] mt-1 leading-snug">{r.blurb}</p>
                          <div className="text-[11px] text-[#6E6787] mt-1.5">
                            Completed {r.completed_at ? new Date(r.completed_at).toLocaleDateString() : "—"}
                            {" · "}v{r.version}
                          </div>
                        </div>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
            <div className="mt-4 rounded-xl bg-[#F5F1FB] border border-[#D6CFE8] px-3 py-2 text-[11px] text-[#3D1A78]">
              <strong>Never shared through this flow:</strong> raw answers,
              journal entries, AI Coach conversations, unfinished drafts,
              safety-screen answers, your account credentials, or the other
              parent&rsquo;s reports.
            </div>
          </section>
        )}

        {/* ---------- Step 3: Access ---------- */}
        {step === 3 && (
          <section
            className="rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
            data-testid="share-step-access"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-4 flex items-center gap-2">
              <Calendar size={18} className="text-[#3D1A78]" /> How much access?
            </h2>

            <fieldset className="space-y-2 mb-5">
              <legend className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-2">
                Permission level
              </legend>
              <label className="flex items-start gap-3 rounded-xl border border-[#E5E0EE] p-3 cursor-pointer hover:bg-[#FAF8FD]">
                <input type="radio" name="access-mode" className="mt-1 accent-[#3D1A78]"
                  checked={!form.download_permission}
                  onChange={() => update({ download_permission: false })}
                  data-testid="access-view-only" />
                <div>
                  <div className="text-sm font-semibold text-[#1A1330]">View in secure portal only</div>
                  <div className="text-[11px] text-[#4B4567] mt-0.5">Recommended. No offline copy leaves the app.</div>
                </div>
              </label>
              <label className="flex items-start gap-3 rounded-xl border border-[#E5E0EE] p-3 cursor-pointer hover:bg-[#FAF8FD]">
                <input type="radio" name="access-mode" className="mt-1 accent-[#3D1A78]"
                  checked={form.download_permission}
                  onChange={() => update({ download_permission: true })}
                  data-testid="access-download" />
                <div>
                  <div className="text-sm font-semibold text-[#1A1330]">View and download</div>
                  <div className="text-[11px] text-[#4B4567] mt-0.5">
                    Once downloaded, SA CoParents can&rsquo;t recall the copy.
                    Revoking prevents future portal access.
                  </div>
                </div>
              </label>
            </fieldset>

            <fieldset className="space-y-2 mb-5">
              <legend className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-2">
                Notifications
              </legend>
              <label className="flex items-center gap-2 text-sm text-[#1A1330]">
                <input type="checkbox" className="accent-[#3D1A78]"
                  checked={form.notify_on_view}
                  onChange={(e) => update({ notify_on_view: e.target.checked })}
                  data-testid="notify-view" />
                Notify me when first viewed
              </label>
              {form.download_permission && (
                <label className="flex items-center gap-2 text-sm text-[#1A1330]">
                  <input type="checkbox" className="accent-[#3D1A78]"
                    checked={form.notify_on_download}
                    onChange={(e) => update({ notify_on_download: e.target.checked })}
                    data-testid="notify-download" />
                  Notify me when downloaded
                </label>
              )}
              <label className="flex items-center gap-2 text-sm text-[#1A1330]">
                <input type="checkbox" className="accent-[#3D1A78]"
                  checked={form.future_versions}
                  onChange={(e) => update({ future_versions: e.target.checked })}
                  data-testid="future-versions" />
                Receive future versions of these selected reports
              </label>
            </fieldset>

            <fieldset className="space-y-2">
              <legend className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-2">
                Access expiration
              </legend>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {ACCESS_OPTIONS.map((o) => (
                  <button
                    key={o.days}
                    type="button"
                    onClick={() => update({ access_days: o.days })}
                    aria-pressed={form.access_days === o.days}
                    data-testid={`access-days-${o.days}`}
                    className={`rounded-full px-3 py-2 text-xs font-semibold border transition-colors ${
                      form.access_days === o.days
                        ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                        : "bg-white text-[#3D1A78] border-[#D6CFE8] hover:bg-[#F5F1FB]"
                    }`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </fieldset>
          </section>
        )}

        {/* ---------- Step 4: Consent ---------- */}
        {step === 4 && (
          <section
            className="rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
            data-testid="share-step-consent"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-4 flex items-center gap-2">
              <ShieldCheck size={18} className="text-[#3D1A78]" /> Review + consent
            </h2>
            <dl className="mb-5 rounded-2xl bg-[#FBF9FE] border border-[#E5E0EE] p-4 text-sm">
              <div className="grid gap-y-2 sm:grid-cols-[160px_1fr] gap-x-4">
                <dt className="text-[#6E6787]">Professional</dt>
                <dd className="text-[#1A1330] font-semibold">
                  {form.professional_first_name} {form.professional_last_name} · {form.professional_email}
                </dd>
                <dt className="text-[#6E6787]">Role</dt>
                <dd className="text-[#1A1330]">
                  {ROLES.find((r) => r.value === form.professional_role)?.label || form.professional_role}
                </dd>
                <dt className="text-[#6E6787]">Reports</dt>
                <dd className="text-[#1A1330]">
                  <ul className="list-disc list-inside">
                    {selectedReports.map((r) => (
                      <li key={r.report_id} className="text-sm">{r.title}</li>
                    ))}
                  </ul>
                </dd>
                <dt className="text-[#6E6787]">Download allowed</dt>
                <dd className="text-[#1A1330]">{form.download_permission ? "Yes" : "No — view-only in portal"}</dd>
                <dt className="text-[#6E6787]">Access expires</dt>
                <dd className="text-[#1A1330]">{form.access_days} days from now</dd>
                {form.personal_message && (
                  <>
                    <dt className="text-[#6E6787]">Your message</dt>
                    <dd className="text-[#1A1330] italic">&ldquo;{form.personal_message}&rdquo;</dd>
                  </>
                )}
              </div>
            </dl>

            <label className="flex items-start gap-2 mb-3 text-[13px] leading-relaxed text-[#1A1330]">
              <input type="checkbox" className="mt-1 accent-[#3D1A78]"
                checked={form.consent_authorised}
                onChange={(e) => update({ consent_authorised: e.target.checked })}
                data-testid="consent-authorised" />
              <span>
                I authorize SA CoParents to make the reports selected above
                available to the identified professional through SA CoParents
                Align. This authorization does not provide access to my entire
                account, raw assessment answers, journals, AI Coach
                conversations, unfinished work, protected safety responses,
                or reports I did not select. I understand that I may revoke
                future access, but previously downloaded copies cannot be
                recalled.
              </span>
            </label>

            <label className="flex items-start gap-2 text-[13px] leading-relaxed text-[#1A1330]">
              <input type="checkbox" className="mt-1 accent-[#3D1A78]"
                checked={form.consent_relationship_acknowledged}
                onChange={(e) => update({ consent_relationship_acknowledged: e.target.checked })}
                data-testid="consent-relationship" />
              <span>
                I understand that accepting this invitation does not by
                itself create an attorney-client, therapist-client,
                physician-patient, mediator, evaluator, or other
                professional relationship.
              </span>
            </label>
          </section>
        )}

        {/* ---------- Step 5: Confirmation ---------- */}
        {step === 5 && result && (
          <section
            className="rounded-3xl border border-[#B5DFC5] bg-[#F1FAF4] p-6"
            data-testid="share-step-confirmation"
          >
            <div className="flex items-center gap-2 text-[#1F5C3B]">
              <CheckCircle2 size={22} />
              <h2 className="font-serif text-2xl">Your invitation has been sent</h2>
            </div>
            <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
              The professional will receive a secure link to verify their
              identity and accept or decline your invitation through SA
              CoParents Align. No report is attached to the email.
            </p>
            <dl className="mt-4 rounded-xl bg-white border border-[#E5E0EE] p-4 text-sm">
              <div className="grid gap-y-2 sm:grid-cols-[160px_1fr] gap-x-4">
                <dt className="text-[#6E6787]">Invited</dt>
                <dd className="text-[#1A1330] font-semibold">
                  {result.invitation?.professional_first_name}{" "}
                  {result.invitation?.professional_last_name} · {result.invitation?.professional_email}
                </dd>
                <dt className="text-[#6E6787]">Reports</dt>
                <dd className="text-[#1A1330]">
                  {(result.invitation?.selected_reports || []).map((r) => r.title).join(", ")}
                </dd>
                <dt className="text-[#6E6787]">Invitation expires</dt>
                <dd className="text-[#1A1330]">
                  {result.invitation?.token_expires_at
                    ? new Date(result.invitation.token_expires_at).toLocaleString()
                    : "—"}
                </dd>
                <dt className="text-[#6E6787]">Access expires</dt>
                <dd className="text-[#1A1330]">
                  {result.invitation?.access_expiration
                    ? new Date(result.invitation.access_expiration).toLocaleDateString()
                    : "—"}
                </dd>
                <dt className="text-[#6E6787]">Email delivery</dt>
                <dd className="text-[#1A1330]">
                  {result.delivered ? "Delivered" : (result.delivery_message || "Not attempted")}
                </dd>
              </div>
            </dl>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link
                to="/shared-with-professionals"
                className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold"
                data-testid="share-confirm-view-invitations"
              >
                <Eye size={13} /> View invitation status
              </Link>
              <button
                type="button"
                onClick={() => { setForm(EMPTY_FORM); setResult(null); setStep(1); }}
                className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-4 py-2 text-sm font-semibold"
                data-testid="share-confirm-invite-another"
              >
                <Send size={13} /> Invite another
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="inline-flex items-center gap-1.5 rounded-full text-[#4B4567] hover:text-[#1A1330] px-4 py-2 text-sm font-semibold"
                data-testid="share-confirm-dashboard"
              >
                Return to dashboard
              </button>
            </div>
          </section>
        )}

        {/* ---------- Nav footer ---------- */}
        {step < 5 && (
          <div className="mt-6 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={goBack}
              disabled={step === 1}
              className="inline-flex items-center gap-1.5 rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-[#F5F1FB] disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2 text-sm font-semibold"
              data-testid="wizard-back"
            >
              <ArrowLeft size={13} /> Back
            </button>
            {step < 4 ? (
              <button
                type="button"
                onClick={goNext}
                className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-5 py-2 text-sm font-semibold"
                data-testid="wizard-next"
              >
                Continue <ArrowRight size={13} />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting || !!stepErrors}
                title={stepErrors || "Send secure invitation"}
                className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] disabled:bg-[#C9C0DC] disabled:cursor-not-allowed text-white px-5 py-2 text-sm font-semibold"
                data-testid="wizard-submit"
              >
                {submitting ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                Send secure invitation
              </button>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
