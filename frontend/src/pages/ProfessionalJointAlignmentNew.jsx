/**
 * `/professional/joint-alignment/new` — In-app Joint Alignment case
 * creation. Lets a mediator, attorney, or paralegal spin up a
 * two-parent case from inside the parent app without having to
 * bounce to `sacoparentsalign.com`.
 *
 * Flow:
 *   1. Authenticated caller fills the form (assessment_type + 2
 *      parents).
 *   2. Submit → App mints an `SA-XXXXXX` case_id, generates two
 *      invitation URLs, and shows them on-screen with one-tap
 *      copy-to-clipboard.
 *   3. Caller emails/DMs each parent their link — parents complete
 *      their private assessment on this same app.
 *
 * The list of cases the caller minted is available at
 * `/professional/joint-alignment/mine` (link surfaced after success).
 */
import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Copy,
  Loader2,
  CheckCircle2,
  Users,
  Sparkles,
  Send,
  AlertTriangle,
  ShieldCheck,
  Bookmark,
  Trash2,
  Plus,
} from "lucide-react";

import AppShell from "../components/AppShell";
import ReminderNoteTemplatePicker from "../components/professional/ReminderNoteTemplatePicker";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const ASSESSMENT_OPTIONS = [
  { value: "co-parenting", label: "Co-Parenting Reflection" },
  { value: "communication", label: "Communication Alignment" },
  { value: "educational", label: "Educational Deep-Dive" },
  { value: "medical", label: "Medical Deep-Dive" },
  { value: "psychological", label: "Psychological Deep-Dive" },
  { value: "special-needs", label: "Special Needs (broad)" },
];

const EMPTY_FORM = {
  assessment_type: "co-parenting",
  parent1_email: "",
  parent1_name: "",
  parent2_email: "",
  parent2_name: "",
  align_case_reference: "",
  reminder_note: "",
  // Iter196 · optional bundle of ADDITIONAL assessments to assign
  // beyond the primary `assessment_type`. Shape:
  //   { assessment_type: string, required: boolean }
  // The primary lane is always required on the backend, so it's
  // never repeated here.
  additional_steps: [],
};

/**
 * BundleTemplatesPanel (iter197) — one-click reuse of a saved
 * assessment bundle. Lists the caller's templates with an Apply
 * button and a small delete icon. Hidden when there are no
 * templates and nothing is loading — a professional who never
 * saves a bundle should never see empty state.
 */
function BundleTemplatesPanel({ templates, loading, onApply, onDelete }) {
  if (!loading && (!templates || templates.length === 0)) return null;
  return (
    <div
      className="rounded-2xl border border-[#B7E0E0] bg-[#F0FBFB] p-3"
      data-testid="pj-bundle-templates-panel"
    >
      <div className="flex items-center gap-2 mb-2">
        <Bookmark size={13} className="text-[#0E7A7A]" />
        <span className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#0E7A7A]">
          Apply a saved bundle
        </span>
        {loading && (
          <Loader2 size={12} className="animate-spin text-[#0E7A7A] ml-1" />
        )}
      </div>
      {templates && templates.length > 0 && (
        <ul
          className="space-y-2"
          data-testid="pj-bundle-templates-list"
        >
          {templates.map((tpl) => {
            const stepCount = 1 + (tpl.extra_steps?.length || 0);
            const reqCount = 1 + (tpl.extra_steps?.filter((s) => s.required).length || 0);
            return (
              <li
                key={tpl.id}
                className="rounded-xl border border-[#B7E0E0] bg-white px-3 py-2 flex items-center justify-between gap-3 flex-wrap"
                data-testid={`pj-bundle-template-${tpl.id}`}
              >
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-sm text-[#1A1330] truncate">
                    {tpl.name}
                  </div>
                  <div className="text-[11px] text-[#4B4567] mt-0.5">
                    {stepCount} step{stepCount !== 1 ? "s" : ""} · {reqCount} required
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => onApply(tpl)}
                    data-testid={`pj-bundle-template-${tpl.id}-apply`}
                    className="inline-flex items-center gap-1 rounded-full bg-[#0E7A7A] hover:bg-[#0B5F5F] text-white px-3 py-1 text-xs font-semibold"
                  >
                    Apply
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm(`Delete bundle "${tpl.name}"?`)) {
                        onDelete(tpl.id);
                      }
                    }}
                    data-testid={`pj-bundle-template-${tpl.id}-delete`}
                    aria-label="Delete bundle"
                    className="w-7 h-7 rounded-full text-[#0E7A7A] hover:bg-[#E4F3F3] grid place-items-center"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}


function AdditionalStepsPicker({ primary, steps, onChange }) {
  const [open, setOpen] = React.useState((steps || []).length > 0);
  const available = ASSESSMENT_OPTIONS.filter((o) => o.value !== primary);
  // Map from assessment_type → { required } for O(1) lookup + easy
  // toggling. The picker is the single source of truth for the
  // ordering — we keep the ASSESSMENT_OPTIONS order stable.
  const selected = React.useMemo(() => {
    const m = new Map();
    (steps || []).forEach((s) => {
      if (s?.assessment_type) m.set(s.assessment_type, { required: !!s.required });
    });
    return m;
  }, [steps]);

  const toggle = (assessment_type) => {
    const next = new Map(selected);
    if (next.has(assessment_type)) {
      next.delete(assessment_type);
    } else {
      next.set(assessment_type, { required: true });
    }
    onChange(
      Array.from(next.entries()).map(([at, v]) => ({
        assessment_type: at,
        required: !!v.required,
      })),
    );
  };

  const setRequired = (assessment_type, required) => {
    if (!selected.has(assessment_type)) return;
    const next = new Map(selected);
    next.set(assessment_type, { required });
    onChange(
      Array.from(next.entries()).map(([at, v]) => ({
        assessment_type: at,
        required: !!v.required,
      })),
    );
  };

  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-[#FAF8FD] p-3"
      data-testid="pj-additional-steps"
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        data-testid="pj-additional-steps-toggle"
        className="w-full flex items-center justify-between gap-2 text-left"
      >
        <div>
          <div className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]">
            Additional assessments (optional)
          </div>
          <div className="text-xs text-[#4B4567] mt-0.5">
            Bundle extra assessments — mark each as Required or Optional
            for the parents.{" "}
            {selected.size > 0 && (
              <strong className="text-[#3D1A78]">
                {selected.size} added
              </strong>
            )}
          </div>
        </div>
        <span className="text-[#3D1A78] text-sm font-bold">
          {open ? "Hide" : "Add"}
        </span>
      </button>
      {open && (
        <ul
          className="mt-3 space-y-2"
          data-testid="pj-additional-steps-list"
        >
          {available.map((opt) => {
            const isSelected = selected.has(opt.value);
            const required = isSelected ? selected.get(opt.value).required : true;
            return (
              <li
                key={opt.value}
                className={`rounded-xl border ${isSelected ? "border-[#3D1A78] bg-white" : "border-[#E5E0EE] bg-white"} px-3 py-2 flex items-center justify-between gap-3 flex-wrap`}
                data-testid={`pj-additional-step-${opt.value}`}
              >
                <label className="flex items-center gap-2 text-sm text-[#1A1330] min-w-0 flex-1">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggle(opt.value)}
                    data-testid={`pj-additional-step-${opt.value}-toggle`}
                    className="accent-[#3D1A78]"
                  />
                  <span className="truncate">{opt.label}</span>
                </label>
                {isSelected && (
                  <div className="flex items-center gap-1 shrink-0" data-testid={`pj-additional-step-${opt.value}-required-group`}>
                    <button
                      type="button"
                      onClick={() => setRequired(opt.value, true)}
                      data-testid={`pj-additional-step-${opt.value}-required`}
                      className={`text-xs font-semibold px-2.5 py-1 rounded-full border transition ${
                        required
                          ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                          : "text-[#3D1A78] border-[#D6CFE8] hover:border-[#3D1A78]"
                      }`}
                    >
                      Required
                    </button>
                    <button
                      type="button"
                      onClick={() => setRequired(opt.value, false)}
                      data-testid={`pj-additional-step-${opt.value}-optional`}
                      className={`text-xs font-semibold px-2.5 py-1 rounded-full border transition ${
                        !required
                          ? "bg-[#0E7A7A] text-white border-[#0E7A7A]"
                          : "text-[#0E7A7A] border-[#B7E0E0] hover:border-[#0E7A7A]"
                      }`}
                    >
                      Optional
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default function ProfessionalJointAlignmentNew() {
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [myCases, setMyCases] = useState(null);
  // Iter197 · Bundle templates — saved by this professional.
  const [templates, setTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);

  const refreshTemplates = React.useCallback(() => {
    setTemplatesLoading(true);
    api
      .get("/professional/bundle-templates")
      .then((r) => setTemplates(r.data?.templates || []))
      .catch((err) => logError("Failed to list bundle templates:", err))
      .finally(() => setTemplatesLoading(false));
  }, []);

  useEffect(() => {
    // Prefetch the caller's earlier in-app cases so the sidebar
    // "Cases you've created" hint is immediate on page load.
    api.get("/professional/joint-alignment/cases-i-created")
      .then((r) => setMyCases(r.data?.cases || []))
      .catch((err) => logError("Failed to list cases-i-created:", err));
    refreshTemplates();
  }, [refreshTemplates]);

  // Apply a saved bundle: replaces the primary lane + additional_steps
  // wholesale so the professional sees exactly the bundle they saved.
  const applyTemplate = (tpl) => {
    if (!tpl) return;
    update({
      assessment_type: tpl.primary_assessment_type,
      additional_steps: (tpl.extra_steps || []).map((s) => ({
        assessment_type: s.assessment_type,
        required: !!s.required,
      })),
    });
    toast.success(`Applied bundle: ${tpl.name}`);
  };

  const saveCurrentAsTemplate = async () => {
    const name = window.prompt(
      "Name this bundle so you can apply it later:",
      "",
    );
    if (!name || !name.trim()) return;
    const primary = form.assessment_type;
    const extras = (form.additional_steps || [])
      .filter((s) => s.assessment_type && s.assessment_type !== primary)
      .map((s) => ({
        assessment_type: s.assessment_type,
        required: !!s.required,
      }));
    try {
      await api.post("/professional/bundle-templates", {
        name: name.trim().slice(0, 120),
        primary_assessment_type: primary,
        extra_steps: extras,
      });
      toast.success("Bundle saved");
      refreshTemplates();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || "Save failed";
      toast.error(String(detail));
    }
  };

  const deleteTemplate = async (id) => {
    try {
      await api.delete(`/professional/bundle-templates/${encodeURIComponent(id)}`);
      toast.success("Bundle deleted");
      refreshTemplates();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || "Delete failed";
      toast.error(String(detail));
    }
  };

  const update = (patch) => setForm((f) => ({ ...f, ...patch }));

  const validEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((e || "").trim());
  const canSubmit =
    validEmail(form.parent1_email) &&
    validEmail(form.parent2_email) &&
    form.parent1_email.trim().toLowerCase() !== form.parent2_email.trim().toLowerCase() &&
    !submitting;

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        assessment_type: form.assessment_type,
        parents: [
          { email: form.parent1_email.trim(), name: form.parent1_name.trim() || null },
          { email: form.parent2_email.trim(), name: form.parent2_name.trim() || null },
        ],
      };
      if (form.align_case_reference.trim()) {
        payload.align_case_reference = form.align_case_reference.trim();
      }
      if (form.reminder_note.trim()) {
        payload.reminder_note = form.reminder_note.trim();
      }
      // Iter196 · surface any additional-step selections. Skip
      // rows that duplicate the primary lane — the backend already
      // dedupes, but no reason to send noise.
      const primary = form.assessment_type;
      const cleanAdditional = (form.additional_steps || [])
        .filter((s) => s.assessment_type && s.assessment_type !== primary)
        .map((s) => ({
          assessment_type: s.assessment_type,
          required: !!s.required,
        }));
      if (cleanAdditional.length) {
        payload.assigned_steps = cleanAdditional;
      }
      const r = await api.post("/professional/joint-alignment/cases", payload);
      setResult(r.data);
      // Refresh the sidebar list so the freshly-minted case shows up.
      api.get("/professional/joint-alignment/cases-i-created")
        .then((rr) => setMyCases(rr.data?.cases || []))
        .catch((err) => logError("Refresh cases failed:", err));
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || "Something went wrong";
      setError(String(detail));
      toast.error(String(detail));
    } finally {
      setSubmitting(false);
    }
  };

  const copyToClipboard = (text, label) => {
    try {
      navigator.clipboard.writeText(text);
      toast.success(`${label} copied`);
    } catch (err) {
      logError("clipboard failed:", err);
      toast.error("Copy failed — long-press the link to copy manually");
    }
  };

  const startAnother = () => {
    setForm(EMPTY_FORM);
    setResult(null);
    setError(null);
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto" data-testid="professional-joint-alignment-new">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-sm text-[#4B4567] hover:text-[#1A1330] mb-4"
          data-testid="pj-back"
        >
          <ArrowLeft size={14} /> Back
        </button>

        <div className="rounded-3xl bg-gradient-to-br from-[#3D1A78] to-[#5A2FA0] text-white p-6 sm:p-8 mb-6 shadow-sm">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 mb-4">
            <Sparkles size={12} />
            <span className="text-[10px] uppercase tracking-[0.22em] font-bold">
              For mediators &amp; family attorneys
            </span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl leading-tight" data-testid="pj-headline">
            Create a Joint Alignment Case
          </h1>
          <p className="mt-3 text-sm sm:text-base text-[#E4D8F5] max-w-2xl leading-relaxed">
            Invite two parents to complete their private assessments on
            SA CoParents. When both are done, a data-minimised joint
            report is available. No back-and-forth with sacoparentsalign.com
            — everything happens right here.
          </p>
        </div>

        {result ? (
          <div
            className="rounded-3xl border-2 border-[#B5DFC5] bg-[#F1F9F4] p-6 sm:p-8 shadow-sm"
            data-testid="pj-result-panel"
          >
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#1F5C3B] text-white grid place-items-center shrink-0">
                <CheckCircle2 size={20} />
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.2em] font-bold text-[#1F5C3B]">
                  Case created
                </div>
                <h2 className="font-serif text-2xl text-[#1A1330] mt-1 leading-tight" data-testid="pj-result-caseid">
                  {result.case_id}
                </h2>
                <p className="text-xs text-[#1F5C3B] mt-1">
                  {result.email_deliveries && result.email_deliveries.every((e) => e.delivered)
                    ? "Invitation emails sent to both parents."
                    : result.email_deliveries && result.email_deliveries.some((e) => e.delivered)
                      ? "One invitation email sent — the other bounced. Copy the failed link manually."
                      : "Copy each parent's invitation link and send it via email, SMS, or your preferred channel."}{" "}
                  Links expire {new Date(result.parents[0].token_expires_at).toLocaleDateString()}.
                </p>
              </div>
            </div>

            <div className="space-y-4 mt-6">
              {result.parents.map((p, i) => {
                const delivery = (result.email_deliveries || []).find((d) => d.email === p.email);
                return (
                <div
                  key={p.email}
                  className="rounded-2xl border border-[#B5DFC5] bg-white p-4"
                  data-testid={`pj-result-parent-${i}`}
                >
                  <div className="flex items-baseline justify-between flex-wrap gap-2">
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#1F5C3B]">
                        Parent {i + 1}
                      </div>
                      <div className="text-sm font-semibold text-[#1A1330]">{p.email}</div>
                      {delivery && (
                        <div
                          className={`mt-1 text-[11px] font-semibold inline-flex items-center gap-1 ${delivery.delivered ? "text-[#1F5C3B]" : "text-[#8A4610]"}`}
                          data-testid={`pj-result-parent-${i}-delivery`}
                          data-delivered={delivery.delivered ? "true" : "false"}
                        >
                          {delivery.delivered ? "✓ Invitation email sent" : "! Email did not send — share the link below manually"}
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(p.invitation_url, `Parent ${i + 1} link`)}
                      className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1.5 text-xs font-semibold transition-colors"
                      data-testid={`pj-copy-parent-${i}`}
                    >
                      <Copy size={12} /> Copy link
                    </button>
                  </div>
                  <div
                    className="mt-3 font-mono text-[11px] text-[#4B4567] bg-[#F5F9F4] border border-[#DDEDE0] rounded-lg px-3 py-2 break-all"
                    data-testid={`pj-invitation-url-${i}`}
                  >
                    {p.invitation_url}
                  </div>
                </div>
              );})}
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={startAnother}
                className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-4 py-2 text-sm font-semibold transition-colors"
                data-testid="pj-start-another"
              >
                <Send size={14} /> Create another case
              </button>
              <Link
                to="/professional/joint-alignment/mine"
                className="text-sm text-[#3D1A78] hover:underline"
                data-testid="pj-visit-mine"
              >
                See all my cases →
              </Link>
              <Link
                to="/for-professionals"
                className="text-sm text-[#3D1A78] hover:underline"
                data-testid="pj-visit-for-pros"
              >
                Back to For Professionals
              </Link>
            </div>
          </div>
        ) : (
          <form
            onSubmit={submit}
            className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm"
            data-testid="pj-form"
          >
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]" htmlFor="pj-assessment">
                  Assessment lane
                </label>
                <select
                  id="pj-assessment"
                  className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                  value={form.assessment_type}
                  onChange={(e) => update({ assessment_type: e.target.value })}
                  data-testid="pj-assessment-select"
                >
                  {ASSESSMENT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              {/* Iter197 · Bundle templates — apply/manage saved bundles. */}
              <div className="sm:col-span-2">
                <BundleTemplatesPanel
                  templates={templates}
                  loading={templatesLoading}
                  onApply={applyTemplate}
                  onDelete={deleteTemplate}
                />
              </div>

              {/* Iter196 · additional assessment bundle. Optional — a
                  professional can tag extra lanes as required or
                  optional and the parent's /case/:caseId view will
                  render them under the correct section. */}
              <div className="sm:col-span-2">
                <AdditionalStepsPicker
                  primary={form.assessment_type}
                  steps={form.additional_steps}
                  onChange={(next) => update({ additional_steps: next })}
                />
                {/* Iter197 · Save current selection as a reusable
                    bundle. Only surfaced when the professional has
                    added at least one extra step — a bundle of just
                    the primary lane provides no reuse value. */}
                {(form.additional_steps || []).length > 0 && (
                  <div className="mt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={saveCurrentAsTemplate}
                      data-testid="pj-save-bundle-btn"
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] hover:underline"
                    >
                      <Bookmark size={12} />
                      Save this bundle for reuse
                    </button>
                  </div>
                )}
              </div>

              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]" htmlFor="pj-p1-name">
                  Parent 1 · Name (optional)
                </label>
                <input
                  id="pj-p1-name"
                  type="text"
                  autoComplete="off"
                  className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                  value={form.parent1_name}
                  onChange={(e) => update({ parent1_name: e.target.value })}
                  placeholder="Alex Rivera"
                  data-testid="pj-parent1-name"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]" htmlFor="pj-p1-email">
                  Parent 1 · Email <span className="text-[#C05621]">*</span>
                </label>
                <input
                  id="pj-p1-email"
                  type="email"
                  required
                  autoComplete="off"
                  className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                  value={form.parent1_email}
                  onChange={(e) => update({ parent1_email: e.target.value })}
                  placeholder="alex@example.com"
                  data-testid="pj-parent1-email"
                />
              </div>

              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]" htmlFor="pj-p2-name">
                  Parent 2 · Name (optional)
                </label>
                <input
                  id="pj-p2-name"
                  type="text"
                  autoComplete="off"
                  className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                  value={form.parent2_name}
                  onChange={(e) => update({ parent2_name: e.target.value })}
                  placeholder="Bailey Chen"
                  data-testid="pj-parent2-name"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]" htmlFor="pj-p2-email">
                  Parent 2 · Email <span className="text-[#C05621]">*</span>
                </label>
                <input
                  id="pj-p2-email"
                  type="email"
                  required
                  autoComplete="off"
                  className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                  value={form.parent2_email}
                  onChange={(e) => update({ parent2_email: e.target.value })}
                  placeholder="bailey@example.com"
                  data-testid="pj-parent2-email"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]" htmlFor="pj-ref">
                  Your reference number (optional)
                </label>
                <input
                  id="pj-ref"
                  type="text"
                  autoComplete="off"
                  className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
                  value={form.align_case_reference}
                  onChange={(e) => update({ align_case_reference: e.target.value })}
                  placeholder="Your firm's file / matter number"
                  data-testid="pj-reference"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-[11px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]" htmlFor="pj-note">
                  Personal reminder note (optional)
                </label>
                <textarea
                  id="pj-note"
                  rows={2}
                  maxLength={240}
                  autoComplete="off"
                  className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78] resize-none"
                  value={form.reminder_note}
                  onChange={(e) => update({ reminder_note: e.target.value })}
                  placeholder='e.g. "Looking forward to Thursday — this takes ~15 minutes."'
                  data-testid="pj-reminder-note"
                />
                <div className="mt-1 flex items-center justify-between text-[11px] text-[#857E9C]">
                  <span>Shown to the parent if we send the 5-day gentle nudge.</span>
                  <span data-testid="pj-reminder-note-count">{form.reminder_note.length}/240</span>
                </div>
                <ReminderNoteTemplatePicker
                  currentValue={form.reminder_note}
                  onInsert={(text) => update({ reminder_note: text.slice(0, 240) })}
                  testidPrefix="pj-new-tpl"
                />
              </div>
            </div>

            <div
              className="mt-6 flex items-start gap-3 rounded-2xl bg-[#F5F1FB] border border-[#D6CFE8] px-4 py-3 text-[13px] text-[#3D1A78]"
              data-testid="pj-privacy-strip"
            >
              <ShieldCheck size={16} className="flex-shrink-0 mt-0.5" />
              <p className="!m-0 leading-relaxed text-[#1A1330]">
                Each parent completes their assessment privately. Individual
                answers stay with the parent who wrote them — this app never
                shares one parent's raw responses with the other, only the
                joint neutral summary once both are complete.
              </p>
            </div>

            {error && (
              <div
                className="mt-4 flex items-start gap-3 rounded-2xl bg-[#FEE4E2] border border-[#F1B0A9] px-4 py-3 text-[13px] text-[#8A2C1E]"
                role="alert"
                aria-live="polite"
                data-testid="pj-error"
              >
                <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
                <p className="!m-0 leading-relaxed">{error}</p>
              </div>
            )}

            <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-[#4B4567]">
                Invitation links live 7 days · Case lives 60 days.
              </div>
              <button
                type="submit"
                disabled={!canSubmit}
                className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] disabled:bg-[#C9C0DC] disabled:cursor-not-allowed text-white px-5 py-2.5 text-sm font-semibold transition-colors"
                data-testid="pj-submit"
              >
                {submitting ? <><Loader2 size={14} className="animate-spin" /> Creating…</> : <><Send size={14} /> Create case &amp; get links</>}
              </button>
            </div>
          </form>
        )}

        {myCases && myCases.length > 0 && !result && (
          <div className="mt-8" data-testid="pj-mine-list">
            <div className="flex items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-2">
                <Users size={14} className="text-[#3D1A78]" />
                <div className="text-[11px] uppercase tracking-[0.2em] font-bold text-[#3D1A78]">
                  Cases you&rsquo;ve created
                </div>
              </div>
              <Link
                to="/professional/joint-alignment/mine"
                className="text-xs font-semibold text-[#3D1A78] hover:underline"
                data-testid="pj-see-all-cases"
              >
                See all my cases →
              </Link>
            </div>
            <ul className="space-y-2">
              {myCases.slice(0, 6).map((c) => (
                <li
                  key={c.case_id}
                  className="rounded-2xl border border-[#E5E0EE] bg-white p-4 flex flex-wrap items-center justify-between gap-3"
                  data-testid={`pj-mine-${c.case_id}`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-[#1A1330]">{c.case_id}</div>
                    <div className="text-xs text-[#4B4567]">
                      {c.assessment_type} · {c.parents.length} parents · {c.status}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {c.parents.map((p, pi) => (
                      p.invitation_url ? (
                        <button
                          key={p.email}
                          type="button"
                          onClick={() => copyToClipboard(p.invitation_url, `${c.case_id} · P${pi + 1}`)}
                          className="text-xs font-semibold text-[#3D1A78] hover:underline inline-flex items-center gap-1"
                          data-testid={`pj-mine-${c.case_id}-copy-${pi}`}
                        >
                          <Copy size={11} /> Copy P{pi + 1}
                        </button>
                      ) : null
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </AppShell>
  );
}
