/**
 * ReminderNoteTemplatePicker — reusable pill row for the reminder-note
 * textarea on `/professional/joint-alignment/new` and `/mine`.
 *
 * Renders below the textarea and offers:
 *   * "Insert template" dropdown that pastes a saved template's body
 *     into the textarea (`onInsert(text)`).
 *   * "Save as template" button that opens a small inline form to
 *     label + save the CURRENT textarea value. Disabled when the
 *     current value is empty.
 *   * "Manage" opens a modal listing saved templates with a Delete
 *     button per row (owner-only, hard cap of 12).
 *
 * Backed by:
 *   GET    /api/professional/reminder-note-templates
 *   POST   /api/professional/reminder-note-templates
 *   DELETE /api/professional/reminder-note-templates/{template_id}
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ChevronDown,
  Bookmark,
  BookmarkPlus,
  Settings,
  Trash2,
  Loader2,
  X,
} from "lucide-react";

import { api } from "../../lib/api";
import { logError } from "../../lib/logger";

export default function ReminderNoteTemplatePicker({
  currentValue,
  onInsert,
  testidPrefix = "reminder-tpl",
  compact = false,
}) {
  const [templates, setTemplates] = useState(null);   // null=loading
  const [pickerOpen, setPickerOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveLabel, setSaveLabel] = useState("");
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const loadTemplates = async () => {
    try {
      const r = await api.get("/professional/reminder-note-templates");
      setTemplates(r.data?.templates || []);
    } catch (err) {
      logError("reminder templates load failed", err);
      setTemplates([]);  // graceful — picker just shows "no templates"
    }
  };

  useEffect(() => { loadTemplates(); }, []);

  const handleInsert = (tpl) => {
    onInsert?.(tpl.body);
    setPickerOpen(false);
    toast.success(`Inserted “${tpl.label}”.`);
  };

  const handleSaveAsTemplate = async () => {
    const body = (currentValue || "").trim();
    const label = saveLabel.trim();
    if (!body || !label) {
      toast.error("Add a label and some text first.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/professional/reminder-note-templates", { label, body });
      toast.success(`Saved template “${label}”.`);
      setSaveOpen(false);
      setSaveLabel("");
      await loadTemplates();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 409) {
        toast.error(typeof detail === "string" ? detail : "Duplicate label.");
      } else {
        logError("reminder template save failed", err);
        toast.error("Couldn't save the template.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (tid) => {
    if (!window.confirm("Delete this template? This can't be undone.")) return;
    setDeletingId(tid);
    try {
      await api.delete(`/professional/reminder-note-templates/${tid}`);
      toast.success("Template deleted.");
      await loadTemplates();
    } catch (err) {
      logError("reminder template delete failed", err);
      toast.error("Couldn't delete the template.");
    } finally {
      setDeletingId(null);
    }
  };

  const currentTrimmed = (currentValue || "").trim();
  const hasTemplates = (templates?.length || 0) > 0;

  return (
    <>
      <div
        className="mt-2 flex items-center gap-2 flex-wrap"
        data-testid={`${testidPrefix}-row`}
      >
        {/* Insert template dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setPickerOpen((v) => !v)}
            disabled={!hasTemplates}
            className="inline-flex items-center gap-1 rounded-full bg-[#EFE9F9] hover:bg-[#E5DAF7] text-[#3D1A78] disabled:bg-[#F5F1FB] disabled:text-[#857E9C] disabled:cursor-not-allowed px-2.5 py-1 text-[11px] font-semibold transition-colors"
            data-testid={`${testidPrefix}-insert`}
            title={hasTemplates ? "Insert a saved template" : "No templates yet"}
          >
            <Bookmark size={11} />
            {compact ? "Insert" : "Insert template"}
            <ChevronDown size={11} />
          </button>
          {pickerOpen && hasTemplates && (
            <div
              className="absolute left-0 top-full mt-1 z-20 min-w-[220px] max-w-[320px] rounded-xl border border-[#E5E0EE] bg-white shadow-lg p-1"
              data-testid={`${testidPrefix}-menu`}
            >
              <ul className="max-h-64 overflow-y-auto">
                {templates.map((tpl) => (
                  <li key={tpl.template_id}>
                    <button
                      type="button"
                      onClick={() => handleInsert(tpl)}
                      className="w-full text-left rounded-lg px-2 py-1.5 hover:bg-[#F5F1FB] transition-colors"
                      data-testid={`${testidPrefix}-menu-item-${tpl.template_id}`}
                    >
                      <div className="text-[12px] font-semibold text-[#1A1330] truncate">
                        {tpl.label}
                      </div>
                      <div className="text-[11px] text-[#857E9C] truncate">
                        {tpl.body}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Save-as-template */}
        <button
          type="button"
          onClick={() => setSaveOpen((v) => !v)}
          disabled={!currentTrimmed}
          className="inline-flex items-center gap-1 rounded-full bg-white border border-[#D6CFE8] hover:bg-[#F5F1FB] text-[#3D1A78] disabled:opacity-50 disabled:cursor-not-allowed px-2.5 py-1 text-[11px] font-semibold transition-colors"
          data-testid={`${testidPrefix}-save`}
          title={currentTrimmed ? "Save current note as a template" : "Type a note first"}
        >
          <BookmarkPlus size={11} />
          {compact ? "Save" : "Save as template"}
        </button>

        <button
          type="button"
          onClick={() => setManageOpen(true)}
          className="inline-flex items-center gap-1 rounded-full text-[#857E9C] hover:text-[#3D1A78] px-2 py-1 text-[11px] font-semibold transition-colors"
          data-testid={`${testidPrefix}-manage`}
          title="Manage saved templates"
        >
          <Settings size={11} />
          Manage
        </button>
      </div>

      {saveOpen && (
        <div
          className="mt-2 rounded-xl border border-[#E5E0EE] bg-[#FBF9FE] p-3"
          data-testid={`${testidPrefix}-save-form`}
        >
          <label
            htmlFor={`${testidPrefix}-save-label`}
            className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78]"
          >
            Template label
          </label>
          <input
            id={`${testidPrefix}-save-label`}
            type="text"
            value={saveLabel}
            onChange={(e) => setSaveLabel(e.target.value)}
            maxLength={60}
            placeholder='e.g. "Thursday intake"'
            className="mt-1 block w-full rounded-lg border border-[#E5E0EE] bg-white text-[#1A1330] text-sm px-2.5 py-1.5 focus:outline-none focus:border-[#3D1A78]"
            data-testid={`${testidPrefix}-save-label-input`}
            autoFocus
          />
          <div className="mt-2 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => { setSaveOpen(false); setSaveLabel(""); }}
              className="rounded-full border border-[#E5E0EE] text-[#4B4567] hover:bg-white px-3 py-1 text-[11px] font-semibold"
              data-testid={`${testidPrefix}-save-cancel`}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveAsTemplate}
              disabled={saving || !saveLabel.trim() || !currentTrimmed}
              className="rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] disabled:bg-[#C9C0DC] text-white px-3 py-1 text-[11px] font-semibold inline-flex items-center gap-1"
              data-testid={`${testidPrefix}-save-confirm`}
            >
              {saving ? <Loader2 size={11} className="animate-spin" /> : <BookmarkPlus size={11} />}
              Save template
            </button>
          </div>
        </div>
      )}

      {manageOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
          onClick={() => setManageOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby={`${testidPrefix}-manage-title`}
          data-testid={`${testidPrefix}-manage-modal`}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-white shadow-xl border border-[#E5E0EE]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#EEE8F7]">
              <h3
                id={`${testidPrefix}-manage-title`}
                className="font-serif text-xl text-[#1A1330]"
              >
                Reminder note templates
              </h3>
              <button
                type="button"
                onClick={() => setManageOpen(false)}
                className="text-[#857E9C] hover:text-[#1A1330]"
                data-testid={`${testidPrefix}-manage-close`}
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-5 max-h-[60vh] overflow-y-auto">
              {templates === null && (
                <div className="text-center text-[#857E9C] text-sm py-6">
                  <Loader2 size={14} className="inline animate-spin mr-1.5" />
                  Loading…
                </div>
              )}
              {templates !== null && templates.length === 0 && (
                <div className="text-center text-[#4B4567] text-sm py-6">
                  You haven&rsquo;t saved any templates yet. Type a note in
                  the textarea, then hit <strong>Save as template</strong>.
                </div>
              )}
              {templates !== null && templates.length > 0 && (
                <ul className="space-y-2">
                  {templates.map((tpl) => (
                    <li
                      key={tpl.template_id}
                      className="rounded-xl border border-[#EEE8F7] bg-[#FAF8FD] p-3 flex items-start justify-between gap-3"
                      data-testid={`${testidPrefix}-manage-row-${tpl.template_id}`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-[12px] font-semibold text-[#1A1330] truncate">
                          {tpl.label}
                        </div>
                        <div className="text-[12px] text-[#4B4567] mt-0.5 whitespace-pre-wrap">
                          {tpl.body}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleDelete(tpl.template_id)}
                        disabled={deletingId === tpl.template_id}
                        className="text-[#9A3A23] hover:bg-[#FCE3DC] rounded-full p-1.5 flex-shrink-0 disabled:opacity-50"
                        data-testid={`${testidPrefix}-manage-delete-${tpl.template_id}`}
                        aria-label={`Delete ${tpl.label}`}
                      >
                        {deletingId === tpl.template_id ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <Trash2 size={13} />
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-[11px] text-[#857E9C] mt-4">
                Up to 12 templates per account. Templates are private to
                your account.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
