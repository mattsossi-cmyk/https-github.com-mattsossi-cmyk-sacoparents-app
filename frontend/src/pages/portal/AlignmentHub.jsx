import React from "react";

import { TrendSparkline } from "./TrendSparkline";

/**
 * AlignmentHub — Section I of the Parent Journey. Shows:
 *   - Official Legal Conflict Resolution Report (Health Index sliders +
 *     Dispute Matrix + Signatures + Save/PDF/Share)
 *   - Align Before Agreement Records (Medical / Educational /
 *     Psychological folders with counts + filter + add)
 *   - Foundation Statement (anchor text + Save/PDF/Share)
 */
export function AlignmentHub({
  // Health Index
  healthIndex,
  setHealthScore,
  healthAvg,
  healthLabel,
  trendSeries,
  onLogReassessment,
  // Legal Report
  legalReport,
  setLegalReport,
  saveLegalReport,
  downloadLegalPdf,
  onShareLegal,
  shareStatus,
  // Alignment records
  alignmentCounts,
  folderFilter,
  setFolderFilter,
  filteredRecords,
  onAddAlignment,
  // Foundation Statement
  foundationText,
  setFoundationText,
  saveFoundationText,
  downloadFoundationPdf,
  onShareFoundation,
}) {
  return (
    <div className="space-y-4" data-testid="hub-section-alignment">
      {/* OFFICIAL LEGAL REPORT MODULE */}
      <div className="bg-white rounded-2xl shadow-sm border-2 border-purple-800 overflow-hidden card-box">
        <div className="bg-purple-900 text-white p-4">
          <div className="flex justify-between items-start">
            <div>
              <span className="bg-purple-800 text-purple-200 text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                Official Legal Module
              </span>
              <h3 className="font-bold text-base mt-1">
                Official Legal Conflict Resolution Report
              </h3>
            </div>
            <span className="bg-emerald-500 text-white text-[9px] font-bold px-2 py-0.5 rounded">
              Matt Sossi Methodology
            </span>
          </div>
          <p className="text-[11px] text-purple-200 mt-1">
            San Antonio, TX Court & Mediation Standard Document
          </p>
        </div>

        <div className="p-4 space-y-4 text-xs">
          {/* Health Index Diagnostic */}
          <div className="bg-purple-50/60 p-3 rounded-xl border border-purple-200 space-y-2">
            <span className="text-[10px] font-bold text-purple-900 uppercase tracking-wider block">
              1. Conflict Escalation & Compliance Diagnostic
            </span>

            {[
              { key: "s1", label: "Info Sharing & Transparency" },
              { key: "s2", label: "Handoff & Transition Predictability" },
              { key: "s3", label: "Decision-Making Collaboration" },
            ].map(({ key, label }, idx) => (
              <div className="space-y-1" key={key}>
                <div className="flex justify-between font-semibold">
                  <span className="text-slate-700">{label}</span>
                  <span
                    data-testid={`score-val-${idx + 1}`}
                    className="text-purple-800 font-bold"
                  >
                    {healthIndex[key]} / 10
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={healthIndex[key]}
                  data-testid={`score-slider-${idx + 1}`}
                  onChange={(e) => setHealthScore(key, e.target.value)}
                  className="w-full accent-purple-800"
                />
              </div>
            ))}

            <div className="p-2.5 bg-white rounded-lg border border-purple-200 flex justify-between items-center mt-2">
              <div>
                <span className="text-[9px] font-bold text-purple-800 uppercase block">
                  Overall Co-Parenting Health Index
                </span>
                <span
                  data-testid="overall-health-label"
                  className="text-xs font-bold text-purple-950"
                >
                  {healthAvg} / 10 — {healthLabel}
                </span>
              </div>
              <button
                data-testid="log-reassessment-btn"
                onClick={onLogReassessment}
                className="no-print bg-purple-800 text-white text-[10px] font-bold px-2 py-1 rounded"
              >
                Log Reassessment
              </button>
            </div>

            <TrendSparkline
              series={trendSeries}
              currentAvg={Number(healthAvg)}
            />
          </div>

          {/* Dispute Resolution Matrix */}
          <div className="space-y-2">
            <span className="text-[10px] font-bold text-purple-900 uppercase tracking-wider block">
              2. Legal Dispute Resolution Matrix
            </span>
            <div className="border border-slate-200 rounded-xl overflow-hidden text-[11px]">
              <table className="w-full text-left">
                <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="p-2">Dispute Area</th>
                    <th className="p-2">Default Resolution Protocol</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-600">
                  <tr>
                    <td className="p-2 font-semibold text-slate-800">
                      Schedule Changes
                    </td>
                    <td className="p-2">24-Hr Advance Notice + Cooling Off</td>
                  </tr>
                  <tr>
                    <td className="p-2 font-semibold text-slate-800">
                      Child Handoffs
                    </td>
                    <td className="p-2">Neutral Public Location Default</td>
                  </tr>
                  <tr>
                    <td className="p-2 font-semibold text-slate-800">
                      Medical Decision Impasse
                    </td>
                    <td className="p-2">Referral to Primary Pediatrician</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Signatures */}
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-2">
            <span className="text-[10px] font-bold text-purple-900 uppercase tracking-wider block">
              3. Digital Affirmation & Certification
            </span>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="font-semibold text-slate-700 text-[10px] block">
                  Parent A Signature
                </label>
                <input
                  data-testid="sig-parent-a"
                  type="text"
                  value={legalReport.sigA}
                  onChange={(e) =>
                    setLegalReport((prev) => ({ ...prev, sigA: e.target.value }))
                  }
                  className="w-full p-2 border border-slate-300 rounded text-xs bg-white"
                  placeholder="Type full legal name"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700 text-[10px] block">
                  Parent B Signature
                </label>
                <input
                  data-testid="sig-parent-b"
                  type="text"
                  value={legalReport.sigB}
                  onChange={(e) =>
                    setLegalReport((prev) => ({ ...prev, sigB: e.target.value }))
                  }
                  className="w-full p-2 border border-slate-300 rounded text-xs bg-white"
                  placeholder="Type full legal name"
                />
              </div>
            </div>
            <div>
              <label className="font-semibold text-slate-700 text-[10px] block">
                Certified Mediator / Attorney
              </label>
              <input
                data-testid="sig-mediator"
                type="text"
                value={legalReport.sigMed}
                onChange={(e) =>
                  setLegalReport((prev) => ({ ...prev, sigMed: e.target.value }))
                }
                className="w-full p-2 border border-slate-300 rounded text-xs bg-white"
              />
            </div>
          </div>

          <div className="flex gap-2 no-print pt-1">
            <button
              data-testid="save-legal-report-btn"
              onClick={saveLegalReport}
              className="flex-1 bg-purple-900 hover:bg-purple-800 text-white font-bold py-2 rounded-xl text-xs transition shadow"
            >
              <i className="fa-solid fa-floppy-disk"></i> Save Legal Report
            </button>
            <button
              data-testid="export-legal-pdf-btn"
              onClick={downloadLegalPdf}
              className="bg-slate-800 text-white font-bold px-3 py-2 rounded-xl text-xs"
            >
              <i className="fa-solid fa-file-pdf"></i> PDF
            </button>
            <button
              data-testid="share-legal-btn"
              onClick={onShareLegal}
              title="Share with an optional passphrase and duration"
              className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-3 py-2 rounded-xl text-xs shadow disabled:opacity-60"
              disabled={shareStatus.legal === "loading"}
            >
              <i className="fa-solid fa-link"></i>{" "}
              {shareStatus.legal === "loading"
                ? "…"
                : shareStatus.legal === "copied"
                ? "Copied!"
                : "Share"}
            </button>
          </div>
        </div>
      </div>

      {/* ALIGNMENT RECORDS */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
        <div className="flex justify-between items-center border-b border-slate-100 pb-2">
          <div>
            <span className="text-[10px] font-bold text-emerald-600 uppercase">
              Step 5 Sub-Folders
            </span>
            <h3 className="font-bold text-slate-800 text-sm">
              Align Before Agreement Records
            </h3>
          </div>
          <button
            data-testid="add-alignment-btn"
            onClick={onAddAlignment}
            className="no-print bg-emerald-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-lg"
          >
            + Add Record
          </button>
        </div>

        <div className="space-y-2 text-xs">
          <div
            className="p-3 bg-emerald-50 rounded-xl border border-emerald-100 flex justify-between items-center cursor-pointer"
            onClick={() => setFolderFilter("Medical")}
            data-testid="folder-medical"
          >
            <div className="flex items-center space-x-2">
              <i className="fa-solid fa-notes-medical text-emerald-600"></i>
              <span className="font-bold text-slate-800">
                Child's Medical Folder
              </span>
            </div>
            <span
              data-testid="count-medical"
              className="bg-white text-emerald-800 font-bold px-2 py-0.5 rounded-full text-[10px]"
            >
              {alignmentCounts.Medical} Records
            </span>
          </div>

          <div
            className="p-3 bg-blue-50 rounded-xl border border-blue-100 flex justify-between items-center cursor-pointer"
            onClick={() => setFolderFilter("Educational")}
            data-testid="folder-educational"
          >
            <div className="flex items-center space-x-2">
              <i className="fa-solid fa-graduation-cap text-blue-600"></i>
              <span className="font-bold text-slate-800">
                Educational Assessment Folder
              </span>
            </div>
            <span
              data-testid="count-educational"
              className="bg-white text-blue-800 font-bold px-2 py-0.5 rounded-full text-[10px]"
            >
              {alignmentCounts.Educational} Records
            </span>
          </div>

          <div
            className="p-3 bg-purple-50 rounded-xl border border-purple-100 flex justify-between items-center cursor-pointer"
            onClick={() => setFolderFilter("Psychological")}
            data-testid="folder-psychological"
          >
            <div className="flex items-center space-x-2">
              <i className="fa-solid fa-brain text-purple-600"></i>
              <span className="font-bold text-slate-800">
                Psychological Assessment Folder
              </span>
            </div>
            <span
              data-testid="count-psychological"
              className="bg-white text-purple-800 font-bold px-2 py-0.5 rounded-full text-[10px]"
            >
              {alignmentCounts.Psychological} Records
            </span>
          </div>
        </div>

        {folderFilter !== "All" && (
          <button
            onClick={() => setFolderFilter("All")}
            data-testid="clear-folder-filter"
            className="no-print text-[10px] text-purple-700 font-bold underline"
          >
            Show all records
          </button>
        )}

        <div className="space-y-2 pt-2" data-testid="alignment-records-grid">
          {filteredRecords.length === 0 ? (
            <p className="text-slate-400 text-center text-xs py-2">
              No assessment records found in this folder.
            </p>
          ) : (
            filteredRecords.map((item) => (
              <div
                key={item.id}
                className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1"
                data-testid={`alignment-record-${item.id}`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-bold text-slate-800">{item.title}</span>
                  <span className="text-[10px] text-slate-400 font-medium">
                    {item.date}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 font-medium">
                  Specialist: {item.provider}
                </div>
                <div className="text-[11px] text-slate-600 bg-white p-2 rounded-lg border border-slate-100">
                  {item.summary}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* FOUNDATION STATEMENT */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
        <div className="flex justify-between items-start border-b border-slate-100 pb-2">
          <div>
            <span className="text-[10px] font-bold text-purple-700 uppercase">
              Step 4 PDF Statement
            </span>
            <h3 className="font-bold text-slate-800 text-sm">
              Foundation Statement
            </h3>
          </div>
          <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2 py-0.5 rounded">
            Anchor PDF
          </span>
        </div>
        <p className="text-xs text-slate-500">
          Your one-page child-focused anchor statement to return to whenever
          emotions get hot.
        </p>
        <textarea
          data-testid="foundation-text"
          rows={3}
          value={foundationText}
          onChange={(e) => setFoundationText(e.target.value)}
          className="w-full p-3 bg-purple-50/50 border border-purple-200 rounded-xl text-xs text-purple-950 font-medium focus:outline-none"
          placeholder="Enter your foundation statement commitment..."
        />
        <div className="flex gap-2 no-print">
          <button
            data-testid="save-foundation-btn"
            onClick={saveFoundationText}
            className="flex-1 bg-purple-800 hover:bg-purple-900 text-white font-bold py-2 rounded-xl text-xs transition"
          >
            <i className="fa-solid fa-floppy-disk"></i> Save Foundation Text
          </button>
          <button
            data-testid="export-foundation-pdf-btn"
            onClick={downloadFoundationPdf}
            className="bg-slate-100 text-slate-700 font-bold px-3 py-2 rounded-xl text-xs border border-slate-200"
          >
            <i className="fa-solid fa-file-pdf"></i> PDF
          </button>
          <button
            data-testid="share-foundation-btn"
            onClick={onShareFoundation}
            title="Copy a 30-day share link"
            className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-3 py-2 rounded-xl text-xs shadow disabled:opacity-60"
            disabled={shareStatus.foundation === "loading"}
          >
            <i className="fa-solid fa-link"></i>{" "}
            {shareStatus.foundation === "loading"
              ? "…"
              : shareStatus.foundation === "copied"
              ? "Copied!"
              : "Share"}
          </button>
        </div>
      </div>
    </div>
  );
}
