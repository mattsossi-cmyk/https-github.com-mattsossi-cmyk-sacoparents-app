/**
 * AdminReviewers — operator-only page to add, edit, and remove reviewer
 * entries on the public methodology "Expert Reviewer Panel". Backs the
 * `reviewer_panel.json` file so the operator does not hand-edit it.
 *
 * Access: gated by `GET /api/reviewer-panel/is-operator`. Non-operators
 * see a friendly "operator-only" placeholder and a link home.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  Loader2, Plus, Pencil, Trash2, Save, X, ShieldCheck, Users,
} from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const EMPTY_FORM = {
  name: "",
  role: "other",
  org: "",
  review_date: "",
  review_scope: "",
  attestation: "",
};

const todayIso = () => {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
};

export default function AdminReviewers() {
  const [loading, setLoading] = useState(true);
  const [isOperator, setIsOperator] = useState(false);
  const [reviewers, setReviewers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [editing, setEditing] = useState(null);   // reviewer id being edited, or "new"
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [panelVersion, setPanelVersion] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const load = async () => {
    try {
      const [op, panel, rolesRes] = await Promise.all([
        api.get("/reviewer-panel/is-operator").catch(() => ({ data: { is_operator: false } })),
        api.get("/reviewer-panel"),
        api.get("/reviewer-panel/reviewers/roles").catch(() => ({ data: { roles: [] } })),
      ]);
      setIsOperator(Boolean(op.data?.is_operator));
      setReviewers(panel.data?.reviewers || []);
      setPanelVersion(panel.data?.review_scope_version || "");
      setLastUpdated(panel.data?.last_updated || "");
      setRoles(rolesRes.data?.roles || []);
    } catch (err) {
      logError("admin reviewers load", err);
      toast.error("Could not load the reviewer panel.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openNew = () => {
    setEditing("new");
    setForm({ ...EMPTY_FORM, review_date: todayIso() });
  };

  const openEdit = (r) => {
    setEditing(r.id);
    setForm({
      name:         r.name || "",
      role:         r.role || "other",
      org:          r.org || "",
      review_date:  r.review_date || "",
      review_scope: r.review_scope || "",
      attestation:  r.attestation || "",
    });
  };

  const cancel = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
  };

  const submit = async () => {
    // Client-side sanity — server enforces the same rules.
    if ((form.name || "").trim().length < 2) {
      toast.error("Please add the reviewer's full name and credentials.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test((form.review_date || "").trim())) {
      toast.error("Review date must be YYYY-MM-DD.");
      return;
    }
    const payload = {
      name: form.name.trim(),
      role: form.role,
      org: (form.org || "").trim() || null,
      review_date: form.review_date.trim(),
      review_scope: (form.review_scope || "").trim() || null,
      attestation: (form.attestation || "").trim() || null,
    };
    setSaving(true);
    try {
      if (editing === "new") {
        const r = await api.post("/reviewer-panel/reviewers", payload);
        toast.success(`Added ${r.data.reviewer.name}.`);
      } else {
        const r = await api.patch(`/reviewer-panel/reviewers/${editing}`, payload);
        toast.success(`Updated ${r.data.reviewer.name}.`);
      }
      cancel();
      await load();
    } catch (err) {
      logError("admin reviewers save", err);
      toast.error(err?.response?.data?.detail || "Couldn't save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (r) => {
    if (!window.confirm(`Remove ${r.name} from the public panel?`)) return;
    setDeleting(r.id);
    try {
      await api.delete(`/reviewer-panel/reviewers/${r.id}`);
      toast.success(`Removed ${r.name}.`);
      await load();
    } catch (err) {
      logError("admin reviewers delete", err);
      toast.error(err?.response?.data?.detail || "Couldn't remove. Please try again.");
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FCFBFE] flex items-center justify-center px-4"
        data-testid="admin-reviewers-loading">
        <div className="text-sm text-[#4B4567] inline-flex items-center gap-2">
          <Loader2 size={14} className="animate-spin" /> Loading reviewer panel…
        </div>
      </div>
    );
  }

  if (!isOperator) {
    return (
      <div className="min-h-screen bg-[#FCFBFE] flex items-center justify-center px-4"
        data-testid="admin-reviewers-not-operator">
        <div className="max-w-md rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm text-center">
          <ShieldCheck size={28} className="mx-auto text-[#3D1A78]" />
          <h1 className="mt-3 font-serif text-2xl text-[#1A1330]">Operator only</h1>
          <p className="mt-2 text-sm text-[#4B4567] leading-relaxed">
            This page manages the public list of independent reviewers.
            Only the site operator can add or edit entries here.
          </p>
          <Link
            to="/methodology"
            className="inline-block mt-4 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-sm font-semibold"
            data-testid="admin-reviewers-back-to-methodology"
          >
            View public methodology
          </Link>
        </div>
      </div>
    );
  }

  const isEditing = editing !== null;

  return (
    <div className="min-h-screen bg-[#FCFBFE] px-4 py-8 sm:py-12"
      data-testid="admin-reviewers-root">
      <div className="max-w-3xl mx-auto">
        <Link to="/methodology"
          className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] underline mb-4">
          ← Back to methodology
        </Link>

        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm">
          <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                Operator tools
              </div>
              <h1 className="mt-1 font-serif text-2xl text-[#1A1330]">
                Manage independent reviewers
              </h1>
              <p className="mt-1 text-sm text-[#4B4567] leading-relaxed">
                Every entry you save here appears publicly on the
                Methodology page. Only add a reviewer after they have
                signed off in writing and agreed to be listed.
              </p>
            </div>
            {!isEditing && (
              <button
                type="button"
                onClick={openNew}
                data-testid="admin-reviewers-add-btn"
                className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-2 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
              >
                <Plus size={14} /> Add reviewer
              </button>
            )}
          </div>

          <div className="text-[11px] text-[#6A5799] mb-6">
            Screen version: <strong>{panelVersion || "v1.0"}</strong>
            {lastUpdated ? ` · Last updated ${lastUpdated}` : ""}
          </div>

          {isEditing && (
            <ReviewerForm
              form={form}
              setForm={setForm}
              roles={roles}
              onCancel={cancel}
              onSubmit={submit}
              saving={saving}
              isNew={editing === "new"}
            />
          )}

          {reviewers.length === 0 ? (
            <div className="rounded-2xl border-2 border-dashed border-[#E5E0EE] bg-[#FAF8FE] p-5 text-center"
              data-testid="admin-reviewers-empty">
              <Users size={20} className="mx-auto text-[#3D1A78] mb-1" />
              <div className="font-bold text-[#1A1330]">
                No reviewers on the panel yet.
              </div>
              <p className="text-sm text-[#4B4567] mt-1">
                Click <em>Add reviewer</em> once one has signed off in writing.
              </p>
            </div>
          ) : (
            <ul className="space-y-3" data-testid="admin-reviewers-list">
              {reviewers.map((r) => (
                <li key={r.id}
                  className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
                  data-testid={`admin-reviewer-item-${r.id}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="min-w-0 flex-1">
                      <div className="font-bold text-[#1A1330]">{r.name}</div>
                      <div className="text-[11px] uppercase tracking-[0.15em] text-[#3D1A78] font-bold mt-0.5">
                        {(roles.find((x) => x.key === r.role) || {}).label || r.role}
                        {r.org ? ` · ${r.org}` : ""}
                      </div>
                      <div className="text-xs text-[#4B4567] mt-1">
                        Reviewed {r.review_date}
                      </div>
                      {r.review_scope && (
                        <div className="mt-1 text-[12px] text-[#4B4567]">
                          <strong>Scope:</strong> {r.review_scope}
                        </div>
                      )}
                      {r.attestation && (
                        <blockquote className="mt-1 pl-3 border-l-2 border-[#3D1A78]/30 text-sm text-[#1A1330] italic">
                          "{r.attestation}"
                        </blockquote>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button type="button"
                        onClick={() => openEdit(r)}
                        disabled={isEditing}
                        data-testid={`admin-reviewer-edit-${r.id}`}
                        className="inline-flex items-center gap-1 rounded-full border border-[#E5E0EE] px-3 py-1 text-xs text-[#3D1A78] font-semibold hover:bg-[#F4F0FB] disabled:opacity-50">
                        <Pencil size={11} /> Edit
                      </button>
                      <button type="button"
                        onClick={() => remove(r)}
                        disabled={deleting === r.id || isEditing}
                        data-testid={`admin-reviewer-delete-${r.id}`}
                        className="inline-flex items-center gap-1 rounded-full border border-[#EFB4B4] text-[#B02A2A] px-3 py-1 text-xs font-semibold hover:bg-[#F8D7D7] disabled:opacity-50">
                        {deleting === r.id ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
                        Remove
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}


function ReviewerForm({ form, setForm, roles, onCancel, onSubmit, saving, isNew }) {
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="rounded-2xl border-2 border-[#3D1A78]/20 bg-[#FAF8FE] p-4 sm:p-5 mb-6"
      data-testid="admin-reviewers-form">
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-3">
        {isNew ? "Add a new reviewer" : "Edit reviewer"}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="text-xs text-[#4B4567] sm:col-span-2">
          Name &amp; credentials <span className="text-[#B02A2A]">*</span>
          <input type="text" value={form.name} onChange={(e) => set("name", e.target.value)}
            data-testid="admin-reviewers-form-name"
            placeholder="e.g. Dr. Alex Reviewer, LPC-S"
            className="mt-1 w-full rounded-lg border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330]" />
        </label>
        <label className="text-xs text-[#4B4567]">
          Role <span className="text-[#B02A2A]">*</span>
          <select value={form.role} onChange={(e) => set("role", e.target.value)}
            data-testid="admin-reviewers-form-role"
            className="mt-1 w-full rounded-lg border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330]">
            {roles.map((r) => (
              <option key={r.key} value={r.key}>{r.label}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-[#4B4567]">
          Review date (UTC) <span className="text-[#B02A2A]">*</span>
          <input type="date" value={form.review_date}
            onChange={(e) => set("review_date", e.target.value)}
            data-testid="admin-reviewers-form-date"
            className="mt-1 w-full rounded-lg border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330]" />
        </label>
        <label className="text-xs text-[#4B4567] sm:col-span-2">
          Organisation (optional)
          <input type="text" value={form.org} onChange={(e) => set("org", e.target.value)}
            data-testid="admin-reviewers-form-org"
            placeholder="e.g. Family Violence Prevention Services"
            className="mt-1 w-full rounded-lg border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330]" />
        </label>
        <label className="text-xs text-[#4B4567] sm:col-span-2">
          Review scope (optional)
          <input type="text" value={form.review_scope} onChange={(e) => set("review_scope", e.target.value)}
            data-testid="admin-reviewers-form-scope"
            placeholder="Which parts of the screen were reviewed"
            className="mt-1 w-full rounded-lg border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330]" />
        </label>
        <label className="text-xs text-[#4B4567] sm:col-span-2">
          Public attestation (optional)
          <textarea rows={3} value={form.attestation}
            onChange={(e) => set("attestation", e.target.value)}
            data-testid="admin-reviewers-form-attestation"
            placeholder="Short public quote — appears in italics beneath the reviewer's name."
            className="mt-1 w-full rounded-lg border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330]" />
        </label>
      </div>
      <div className="flex items-center gap-2 justify-end mt-4">
        <button type="button" onClick={onCancel} disabled={saving}
          data-testid="admin-reviewers-form-cancel"
          className="inline-flex items-center gap-1 rounded-full border border-[#E5E0EE] px-4 py-2 text-sm text-[#4B4567] font-semibold hover:bg-[#F4F0FB] disabled:opacity-50">
          <X size={12} /> Cancel
        </button>
        <button type="button" onClick={onSubmit} disabled={saving}
          data-testid="admin-reviewers-form-save"
          className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-2 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50">
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          {isNew ? "Add reviewer" : "Save changes"}
        </button>
      </div>
    </div>
  );
}
