/**
 * AdminBridgeCopy — Iter199.
 *
 * Admin-only editor for the Individual→Joint bridge two-variant copy
 * (cleared vs concerned). Also surfaces the CTR analytics per variant
 * so ops can compare whether the new "no concerns / safe paths" copy
 * lifts CTA click-through vs the baseline.
 *
 * Reads / writes:
 *   * GET  /api/public/nudge-copy/individual-to-joint-bridge
 *   * POST /api/admin/nudge-copy/individual-to-joint-bridge
 *   * GET  /api/admin/nudge-copy/individual-to-joint-bridge/analytics
 *
 * Kept intentionally simple — a single "Save both" action that submits
 * whatever the form currently has. History logging happens server-side
 * per variant.
 */
import React, { useEffect, useState } from "react";
import { Navigate, Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { toast } from "sonner";
import {
  Save,
  ShieldCheck,
  TrendingUp,
  Loader2,
  ArrowLeft,
  Eye,
  MousePointerClick,
} from "lucide-react";

const VARIANTS = [
  {
    key: "cleared",
    label: "Cleared · No concerns about family violence",
    tone: "purple",
  },
  {
    key: "concerned",
    label: "Concerned · Safe paths for when family violence is present",
    tone: "amber",
  },
];

const EMPTY_VARIANT = {
  eyebrow: "",
  headline: "",
  body: "",
  cta_label: "",
  cta_route: "",
};

export default function AdminBridgeCopy() {
  const { user, loading } = useAuth();
  const [form, setForm] = useState({
    cleared: { ...EMPTY_VARIANT },
    concerned: { ...EMPTY_VARIANT },
  });
  const [isDefault, setIsDefault] = useState(true);
  const [saving, setSaving] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!user) return;
    api
      .get("/public/nudge-copy/individual-to-joint-bridge")
      .then((r) => {
        setForm({
          cleared: { ...r.data.cleared },
          concerned: { ...r.data.concerned },
        });
        setIsDefault(!!r.data.is_default);
      })
      .catch((err) => logError("bridge copy load failed", err));
    api
      .get("/admin/nudge-copy/individual-to-joint-bridge/analytics")
      .then((r) => setAnalytics(r.data?.variants || null))
      .catch((err) => logError("bridge analytics load failed", err));
  }, [user]);

  if (loading) return null;
  if (!user || user.is_guest) return <Navigate to="/login" replace />;

  const updateField = (variantKey, field, value) => {
    setForm((prev) => ({
      ...prev,
      [variantKey]: { ...prev[variantKey], [field]: value },
    }));
  };

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.post(
        "/admin/nudge-copy/individual-to-joint-bridge",
        {
          cleared: form.cleared,
          concerned: form.concerned,
          note: note.trim() || null,
        },
      );
      setIsDefault(!!r.data.is_default);
      setNote("");
      toast.success("Bridge copy saved.");
    } catch (err) {
      const detail = err?.response?.data?.detail || "Save failed";
      toast.error(String(detail));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <div
        className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12"
        data-testid="admin-bridge-copy-page"
      >
        <Link
          to="/admin"
          className="inline-flex items-center gap-1.5 text-sm text-[#4B4567] hover:text-[#3D1A78] mb-6"
          data-testid="admin-bridge-copy-back"
        >
          <ArrowLeft size={14} />
          Back to admin dashboard
        </Link>
        <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
          Configurable copy · Individual → Joint bridge
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-2">
          Two variants — one per safety-screen outcome
        </h1>
        <p className="text-sm text-[#4B4567] mt-2 leading-relaxed max-w-2xl">
          The Landing bridge section and the Safety Assessment cleared-CTA
          switch client-side based on the parent&rsquo;s most recent Safety
          level. Edit each variant separately. Impressions and clicks are
          tracked so you can compare CTR without an external analytics tool.
        </p>
        {isDefault && (
          <div
            className="mt-4 rounded-2xl border border-[#F1D9B7] bg-[#FFF6EA] px-4 py-3 text-[13px] text-[#5A3C10] flex items-start gap-2"
            data-testid="admin-bridge-copy-default-banner"
          >
            <ShieldCheck size={14} className="text-[#904B0E] mt-0.5" />
            <span>
              You&rsquo;re currently seeing the baked-in defaults. Save any
              edit to switch this key onto the admin override.
            </span>
          </div>
        )}

        {/* Analytics tile — CTR per variant. */}
        <section
          className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-7"
          data-testid="admin-bridge-copy-analytics"
        >
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={14} className="text-[#3D1A78]" />
            <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              CTR analytics · Per variant
            </div>
          </div>
          {!analytics ? (
            <div className="text-sm text-[#4B4567] flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Loading…
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {VARIANTS.map((v) => {
                const row = analytics[v.key] || {
                  impressions: 0,
                  clicks: 0,
                  ctr: 0.0,
                };
                return (
                  <div
                    key={v.key}
                    className={`rounded-2xl border p-4 ${
                      v.tone === "purple"
                        ? "border-[#D6CFE8] bg-[#FBF6FF]"
                        : "border-[#F1D9B7] bg-[#FFF6EA]"
                    }`}
                    data-testid={`admin-bridge-copy-analytics-${v.key}`}
                  >
                    <div
                      className={`text-[10px] uppercase tracking-[0.16em] font-bold ${
                        v.tone === "purple"
                          ? "text-[#3D1A78]"
                          : "text-[#904B0E]"
                      } mb-1`}
                    >
                      {v.label}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center mt-3">
                      <Metric
                        icon={Eye}
                        label="Impressions"
                        value={row.impressions}
                        testid={`admin-bridge-copy-analytics-${v.key}-impressions`}
                      />
                      <Metric
                        icon={MousePointerClick}
                        label="Clicks"
                        value={row.clicks}
                        testid={`admin-bridge-copy-analytics-${v.key}-clicks`}
                      />
                      <Metric
                        icon={TrendingUp}
                        label="CTR"
                        value={`${row.ctr}%`}
                        testid={`admin-bridge-copy-analytics-${v.key}-ctr`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Editors — one per variant. */}
        <div className="mt-8 space-y-6">
          {VARIANTS.map((v) => (
            <VariantEditor
              key={v.key}
              tone={v.tone}
              variantKey={v.key}
              label={v.label}
              values={form[v.key]}
              onChange={(field, value) => updateField(v.key, field, value)}
            />
          ))}
        </div>

        {/* Save controls. */}
        <div className="mt-6 rounded-2xl border border-[#E5E0EE] bg-white p-4 flex items-center gap-3 flex-wrap">
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={200}
            placeholder="Optional note for the audit log (e.g. 'tightened cleared headline for A/B iter199')"
            data-testid="admin-bridge-copy-note"
            className="flex-1 min-w-[240px] rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330] focus:outline-none focus:border-[#3D1A78]"
          />
          <button
            type="button"
            onClick={save}
            disabled={saving}
            data-testid="admin-bridge-copy-save"
            className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] disabled:opacity-50 transition"
          >
            {saving ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Save size={14} />
            )}
            Save both variants
          </button>
        </div>
      </div>
    </AppShell>
  );
}

function Metric({ icon: Icon, label, value, testid }) {
  return (
    <div className="rounded-xl bg-white border border-[#E5E0EE] p-2">
      <div className="text-[9px] uppercase tracking-[0.14em] font-bold text-[#6E6787] flex items-center justify-center gap-1">
        <Icon size={10} />
        {label}
      </div>
      <div
        className="font-serif text-lg text-[#1A1330] leading-none mt-1"
        data-testid={testid}
      >
        {value}
      </div>
    </div>
  );
}

function VariantEditor({ tone, variantKey, label, values, onChange }) {
  const chip = tone === "purple" ? "bg-[#EFE9F9] text-[#3D1A78]" : "bg-[#FFEEDA] text-[#904B0E]";
  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-6"
      data-testid={`admin-bridge-copy-editor-${variantKey}`}
    >
      <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.22em] font-bold ${chip}`}>
        {label}
      </div>
      <div className="mt-4 grid gap-3">
        <TextField
          label="Eyebrow (small caps above headline)"
          value={values.eyebrow}
          onChange={(v) => onChange("eyebrow", v)}
          testid={`admin-bridge-copy-eyebrow-${variantKey}`}
          maxLength={180}
        />
        <TextField
          label="Headline"
          value={values.headline}
          onChange={(v) => onChange("headline", v)}
          testid={`admin-bridge-copy-headline-${variantKey}`}
          maxLength={180}
        />
        <TextField
          label="Body"
          value={values.body}
          onChange={(v) => onChange("body", v)}
          testid={`admin-bridge-copy-body-${variantKey}`}
          maxLength={600}
          textarea
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField
            label="CTA label (button text)"
            value={values.cta_label}
            onChange={(v) => onChange("cta_label", v)}
            testid={`admin-bridge-copy-cta-label-${variantKey}`}
            maxLength={80}
          />
          <TextField
            label="CTA route (same-origin path e.g. /samples)"
            value={values.cta_route}
            onChange={(v) => onChange("cta_route", v)}
            testid={`admin-bridge-copy-cta-route-${variantKey}`}
            maxLength={120}
          />
        </div>
      </div>
    </section>
  );
}

function TextField({ label, value, onChange, testid, maxLength, textarea = false }) {
  const Tag = textarea ? "textarea" : "input";
  return (
    <label className="block">
      <span className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]">
        {label}
      </span>
      <Tag
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={maxLength}
        rows={textarea ? 3 : undefined}
        data-testid={testid}
        className="mt-1 block w-full rounded-xl border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-3 py-2 focus:outline-none focus:border-[#3D1A78]"
      />
      <span className="text-[10px] text-[#6E6787] mt-0.5 block">
        {(value || "").length}/{maxLength}
      </span>
    </label>
  );
}
