import React from "react";
import { PenTool } from "lucide-react";

/**
 * SignDownloadToggle — a small "☐ Sign & timestamp this download" checkbox
 * that sits alongside every report page's Download button.
 *
 * When checked, the caller should append `?sign=true` to the PDF endpoint
 * so the backend embeds the parent's name + a UTC timestamp under the
 * "REVIEW BEFORE SHARING" watermark on every page.
 *
 * Deliberately zero-state — parent owns `checked` + `onChange` so this
 * component can be dropped into any report page without wiring API calls.
 */
export default function SignDownloadToggle({
  checked,
  onChange,
  disabled = false,
  testid = "sign-download-toggle",
}) {
  return (
    <label
      className={`inline-flex items-center gap-2 select-none text-[11px] font-semibold text-[#4B4567] cursor-pointer ${
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
  );
}
