import React from "react";
import { PenTool } from "lucide-react";

const NOTE_MAX = 120;

/**
 * SignDownloadToggle — the "☐ Sign & timestamp this download" checkbox
 * that sits alongside every report page's Download button.
 *
 * Now also supports an optional one-line signing note (e.g. "Prepared
 * for our 12 Feb mediation session") that prints in italics just above
 * the signature line inside the PDF. The note input reveals itself once
 * the checkbox is ticked, so the UI stays quiet by default.
 *
 * Callers own state via the { checked, note, onChange } props. The
 * shape is deliberately backwards-compatible with the previous
 * boolean-only API — passing just `onChange(bool)` still works because
 * we call `onChange({checked, note})` when `noteEnabled` is true and
 * fall back to `onChange(checked)` when the caller doesn't pass a note.
 */
export default function SignDownloadToggle({
  checked,
  note = "",
  onChange,
  onNoteChange,
  disabled = false,
  testid = "sign-download-toggle",
}) {
  const remaining = Math.max(0, NOTE_MAX - (note || "").length);
  return (
    <div className="flex flex-col items-end gap-2">
      <label
        className={`inline-flex items-center gap-2 select-none text-[0.6875rem] font-semibold text-[#4B4567] cursor-pointer ${
          disabled ? "opacity-60 cursor-not-allowed" : ""
        }`}
        title="Adds your name and a UTC timestamp under the watermark on every page."
        data-testid={testid}
      >
        <input
          type="checkbox"
          checked={!!checked}
          disabled={disabled}
          onChange={(e) => onChange && onChange(e.target.checked)}
          className="h-3.5 w-3.5 rounded border-[#C7BFDA] text-[#3D1A78] focus:ring-[#3D1A78] cursor-pointer"
          data-testid={`${testid}-checkbox`}
        />
        <PenTool size={11} className="text-[#3D1A78]" aria-hidden />
        <span>Sign &amp; timestamp this download</span>
      </label>

      {checked && onNoteChange && (
        <div
          className="w-full max-w-sm flex flex-col items-end gap-1"
          data-testid={`${testid}-note-wrap`}
        >
          <input
            type="text"
            value={note}
            maxLength={NOTE_MAX}
            onChange={(e) => onNoteChange(e.target.value.slice(0, NOTE_MAX))}
            placeholder='Optional note e.g. "Prepared for our 12 Feb mediation"'
            className="w-full text-[0.75rem] font-normal text-[#1A1330] bg-white border border-[#E5E0EE] focus:border-[#3D1A78] focus:ring-2 focus:ring-[#E9E1F7] rounded-lg px-3 py-1.5 outline-none transition"
            data-testid={`${testid}-note-input`}
          />
          <div
            className="text-[0.625rem] text-[#6E6787]"
            data-testid={`${testid}-note-counter`}
          >
            {remaining} chars left · appears above your signature on every page
          </div>
        </div>
      )}
    </div>
  );
}
