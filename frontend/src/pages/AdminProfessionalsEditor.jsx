/**
 * `/admin/professionals` — Admin-only editor for the professionals
 * directory.
 *
 * Access is gated at the API layer (`require_admin` on every
 * `/api/admin/professionals*` route) via ADMIN_EMAILS. A
 * non-admin who navigates here gets a friendly explanation
 * because every API call returns 403.
 *
 * Explicitly *not* a public sign-up form — the founder's
 * requirement is "professionals have to be added with
 * permission". Only an authenticated admin can add or deactivate
 * entries.
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  Loader2,
  Save,
  Eye,
  EyeOff,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

function toApiPayload(form) {
  return {
    name: form.name.trim(),
    credentials: form.credentials.trim(),
    license: form.license.trim() || null,
    email: form.email.trim(),
    phone: form.phone.trim() || null,
    website: form.website.trim() || null,
    address_lines: form.address_lines_text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean),
    city: form.city.trim() || null,
    state: form.state.trim() || null,
    bio: form.bio.trim() || null,
    sort_order: Number.isFinite(+form.sort_order) ? +form.sort_order : 100,
    active: !!form.active,
  };
}

const EMPTY_FORM = {
  name: "",
  credentials: "",
  license: "",
  email: "",
  phone: "",
  website: "",
  address_lines_text: "",
  city: "",
  state: "",
  bio: "",
  sort_order: 100,
  active: true,
};

export default function AdminProfessionalsEditor() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [professionals, setProfessionals] = useState(null);
  const [authError, setAuthError] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const isSignedIn = !!user;

  const load = async () => {
    if (!isSignedIn) {
      setAuthError("Sign in with an admin account to manage professionals.");
      return;
    }
    try {
      const r = await api.get("/admin/professionals");
      setProfessionals(r.data?.professionals || []);
      setAuthError(null);
    } catch (err) {
      const status = err?.response?.status ?? 0;
      if (status === 403) {
        setAuthError(
          "This dashboard is only available to authorized admins. If you should have access, contact mattsossi@bsossi.com."
        );
      } else if (status) {
        setAuthError("Failed to load the directory.");
      } else {
        setAuthError("Network error.");
      }
    }
  };

  useEffect(() => {
    if (authLoading) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isSignedIn]);

  const create = async (e) => {
    e.preventDefault();
    if (!isSignedIn) return;
    setSaving(true);
    try {
      const r = await api.post("/admin/professionals", toApiPayload(form));
      toast.success(`Added ${r.data?.name || "professional"}`);
      setForm(EMPTY_FORM);
      setAddOpen(false);
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail || "";
      toast.error(detail || "Could not add");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (professional) => {
    if (!isSignedIn) return;
    try {
      const r = await api.patch(
        `/admin/professionals/${professional.professional_id}`,
        { active: !professional.active }
      );
      const data = r.data || {};
      toast.success(
        data.active ? `${data.name} visible in directory` : `${data.name} hidden`
      );
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail || "";
      toast.error(detail || "Could not update");
    }
  };

  if (authError) {
    return (
      <AppShell>
        <div
          className="max-w-2xl mx-auto px-4 sm:px-6 py-14"
          data-testid="admin-professionals-auth-error"
        >
          <div className="rounded-3xl border border-[#F1D9B7] bg-[#FFF6EA] p-6 text-[#5A3C10]">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} />
              <h1 className="font-serif text-2xl">Admin access required</h1>
            </div>
            <p className="mt-3 text-[13.5px] leading-relaxed">{authError}</p>
            <button
              type="button"
              onClick={() => navigate("/dashboard")}
              className="mt-4 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
            >
              Back to dashboard
            </button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12"
        data-testid="admin-professionals-page"
      >
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="inline-flex items-center gap-2 text-sm text-[#3D1A78] hover:text-[#2A0F5F] mb-6"
        >
          <ArrowLeft size={14} /> Back to dashboard
        </button>

        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[0.6875rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
              Admin · Professionals directory
            </div>
            <h1
              className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1"
              data-testid="admin-professionals-title"
            >
              Manage professionals
            </h1>
          </div>
          <button
            type="button"
            onClick={() => setAddOpen((s) => !s)}
            className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
            data-testid="admin-professionals-add-toggle"
          >
            <Plus size={14} />
            {addOpen ? "Cancel" : "Add professional"}
          </button>
        </div>

        <div className="mt-4 rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-3 flex gap-2 items-start text-[0.8125rem] text-[#4B4567] leading-relaxed">
          <ShieldCheck size={16} className="text-[#3D1A78] flex-shrink-0 mt-0.5" />
          <p className="!m-0">
            Professionals cannot self-sign-up. Every entry is added
            <strong className="text-[#1A1330]"> with permission</strong> from
            here and can be deactivated at any time — deactivated rows stay
            in the audit log but disappear from the parent-facing
            directory.
          </p>
        </div>

        {addOpen && (
          <form
            onSubmit={create}
            className="mt-6 rounded-3xl border-2 border-[#3D1A78] bg-white p-5 sm:p-6"
            data-testid="admin-professionals-add-form"
          >
            <h2 className="font-serif text-xl text-[#1A1330]">
              New professional
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <FormField
                label="Name"
                value={form.name}
                onChange={(v) => setForm({ ...form, name: v })}
                required
                testid="admin-form-name"
              />
              <FormField
                label="Email"
                type="email"
                value={form.email}
                onChange={(v) => setForm({ ...form, email: v })}
                required
                testid="admin-form-email"
              />
              <FormField
                label="Credentials"
                value={form.credentials}
                onChange={(v) => setForm({ ...form, credentials: v })}
                placeholder="e.g. San Antonio Attorney, Family Law Mediator"
                required
                testid="admin-form-credentials"
                className="sm:col-span-2"
              />
              <FormField
                label="License"
                value={form.license}
                onChange={(v) => setForm({ ...form, license: v })}
                placeholder="Licensed to Practice in the State of Texas"
                testid="admin-form-license"
                className="sm:col-span-2"
              />
              <FormField
                label="Phone"
                value={form.phone}
                onChange={(v) => setForm({ ...form, phone: v })}
                testid="admin-form-phone"
              />
              <FormField
                label="Website"
                value={form.website}
                onChange={(v) => setForm({ ...form, website: v })}
                placeholder="https://…"
                testid="admin-form-website"
              />
              <FormField
                label="City"
                value={form.city}
                onChange={(v) => setForm({ ...form, city: v })}
                testid="admin-form-city"
              />
              <FormField
                label="State"
                value={form.state}
                onChange={(v) => setForm({ ...form, state: v })}
                testid="admin-form-state"
              />
              <label className="block sm:col-span-2">
                <span className="text-[0.6875rem] uppercase tracking-[0.14em] font-bold text-[#6E6787]">
                  Address (one line per row)
                </span>
                <textarea
                  value={form.address_lines_text}
                  onChange={(e) =>
                    setForm({ ...form, address_lines_text: e.target.value })
                  }
                  rows={3}
                  placeholder={"16607 Blanco #703\nSan Antonio, Texas 78232"}
                  className="mt-1 block w-full rounded-xl border-2 border-[#E5E0EE] focus:border-[#3D1A78] px-4 py-2.5 text-sm outline-none transition resize-none"
                  data-testid="admin-form-address"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="text-[0.6875rem] uppercase tracking-[0.14em] font-bold text-[#6E6787]">
                  Bio
                </span>
                <textarea
                  value={form.bio}
                  onChange={(e) => setForm({ ...form, bio: e.target.value })}
                  rows={3}
                  className="mt-1 block w-full rounded-xl border-2 border-[#E5E0EE] focus:border-[#3D1A78] px-4 py-2.5 text-sm outline-none transition resize-none"
                  data-testid="admin-form-bio"
                />
              </label>
              <FormField
                label="Sort order (lower = higher in list)"
                type="number"
                value={form.sort_order}
                onChange={(v) => setForm({ ...form, sort_order: v })}
                testid="admin-form-sort"
              />
              <label className="flex items-center gap-2 mt-6 text-sm">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                  data-testid="admin-form-active"
                />
                <span>Visible in the public directory</span>
              </label>
            </div>
            <button
              type="submit"
              disabled={saving || !form.name || !form.credentials || !form.email}
              className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-6 py-3 text-sm font-semibold hover:bg-[#2A0F5F] transition disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="admin-form-submit"
            >
              {saving && <Loader2 className="animate-spin" size={16} />}
              <Save size={14} />
              Save professional
            </button>
          </form>
        )}

        <section className="mt-8">
          <h2 className="font-serif text-xl text-[#1A1330] mb-4">
            Current directory
          </h2>
          {professionals === null && (
            <div className="flex items-center gap-2 text-[#4B4567] text-sm">
              <Loader2 className="animate-spin" size={16} />
              Loading…
            </div>
          )}
          {professionals && professionals.length === 0 && (
            <p className="text-[#4B4567] text-sm">No professionals yet.</p>
          )}
          <ul
            className="space-y-3"
            data-testid="admin-professionals-list"
          >
            {(professionals || []).map((p) => (
              <li
                key={p.professional_id}
                className={`rounded-2xl border p-4 flex flex-wrap items-start justify-between gap-3 ${
                  p.active
                    ? "border-[#E5E0EE] bg-white"
                    : "border-[#DED8E5] bg-[#F5F3F9] opacity-70"
                }`}
                data-testid={`admin-row-${p.professional_id}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="font-serif text-lg text-[#1A1330] flex items-center gap-2">
                    {p.name}
                    {!p.active && (
                      <span className="text-[0.625rem] uppercase tracking-[0.1em] font-bold text-[#8F1D24] border border-[#8F1D24]/30 rounded-full px-2 py-0.5">
                        Hidden
                      </span>
                    )}
                  </div>
                  <div className="text-[0.8125rem] text-[#4B4567] leading-snug mt-0.5">
                    {p.credentials}
                  </div>
                  <div className="text-[0.75rem] text-[#6E6787] mt-1">
                    {p.email} · sort #{p.sort_order}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => toggleActive(p)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-[#E5E0EE] text-[#3D1A78] px-3 py-1.5 text-[0.8125rem] font-semibold hover:border-[#3D1A78] transition"
                  data-testid={`admin-toggle-${p.professional_id}`}
                >
                  {p.active ? <EyeOff size={13} /> : <Eye size={13} />}
                  {p.active ? "Hide" : "Show"}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </AppShell>
  );
}

function FormField({
  label,
  value,
  onChange,
  type = "text",
  required,
  placeholder,
  testid,
  className,
}) {
  return (
    <label className={`block ${className || ""}`}>
      <span className="text-[0.6875rem] uppercase tracking-[0.14em] font-bold text-[#6E6787]">
        {label}
        {required && " *"}
      </span>
      <input
        type={type}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className="mt-1 block w-full rounded-xl border-2 border-[#E5E0EE] focus:border-[#3D1A78] px-4 py-2.5 text-sm outline-none transition"
        data-testid={testid}
      />
    </label>
  );
}
