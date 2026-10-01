import React from "react";
import { Link } from "react-router-dom";

import { SnapshotStrip } from "./SnapshotStrip";
import { TrendSparkline } from "./TrendSparkline";
import { AssessmentGuideChatInline } from "./AssessmentGuideChat";
import { CpProgressTile } from "./CpProgressTile";

/**
 * AlignmentHub — Section I of the Parent Journey. Shows:
 *   - (Only when a Court Key is verified) Official Legal Conflict
 *     Resolution Report (Health Index sliders + Dispute Matrix +
 *     Signatures + Save/PDF/Share).
 *   - (Only on the Parent Journey Door — no court key) a Toolkit tile
 *     grid that links out to the app's parent-facing pages: Co-parent
 *     Assessment, Safety Screen, Mediation Prep, Alignment Before
 *     Agreement, and Joint Reports sharing.
 *   - Align Before Agreement Records (Medical / Educational /
 *     Psychological folders with counts + filter + add).
 *   - Foundation Statement (anchor text + Save/PDF/Share).
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
  // Court-only gating: hide the Legal Report module when there is no
  // verified Court Key (Parent Journey door). Toolkit tile-grid takes
  // its place with links to the app's parent-facing pages.
  hideCourtOnly = false,
  // Toolkit tile → scroll+filter the assessment records section by
  // category (Medical / Educational / Psychological).
  openAssessmentFolder = () => {},
  // Complete Coparenting Report bundle (iter218) — download + share.
  downloadCompleteReportPdf = () => {},
  onShareCompleteReport = () => {},
  // Email Foundation Statement to co-parent (iter219). Gated by
  // safetyFlagged: when the parent's Safety Check flagged coercion,
  // we HIDE the CTA and surface a soft-block warning instead so we
  // never help facilitate contact with an unsafe co-parent.
  safetyFlagged = false,
  onEmailFoundationToCoparent = () => {},
  // Guided-journey chat wizard (iter220). Toolkit tiles and the
  // Foundation Statement panel both invoke this with a topic key.
  openGuidedJourney = () => {},
  // Snapshot Library (iter227). Last-N committed Guided Journey runs
  // + a callback to re-download in any variant (standard / fridge /
  // fridge_pair) without re-running the wizard.
  snapshotHistory = [],
  onSnapshotRedownload = () => {},
  onSnapshotDelete = () => {},
  onSnapshotRename = () => {},
  onSnapshotPin = () => {},
  // iter233 — inline Assessment Guide chatbot lives on this page
  // (Alignment & Tools) at the top of the Coparenting Journey Toolkit.
  // Routing target: same onStartAssessment used by the modal instance
  // in SacoparentsPortal, so both surfaces stay in exact lockstep.
  onStartAssessment = () => {},
}) {
  return (
    <div className="space-y-4" data-testid="hub-section-alignment">
      {/* PARENT JOURNEY TOOLKIT — only for the self-guided Door (no
          Court Key). Legal Report is a court/mediator artefact, so a
          parent flying solo shouldn't see it. Instead point them at
          the app's own parent-facing pages. */}
      {hideCourtOnly && (
        <div
          className="bg-white rounded-2xl shadow-sm border border-purple-200 p-4 space-y-3 card-box"
          data-testid="parent-journey-toolkit"
        >
          <div className="flex justify-between items-start">
            <div>
              <span className="bg-purple-100 text-purple-800 text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                Coparenting Journey Toolkit
              </span>
              <h3 className="font-bold text-slate-800 text-sm mt-1">
                Assessments, Alignment & Joint Reports
              </h3>
              <p className="text-[11px] text-slate-500 leading-snug">
                Open a full-featured tool. Your work saves to your
                account — you can share the finished report with your
                co-parent, a mediator, or an attorney.
              </p>
            </div>
          </div>

          <SnapshotStrip
            history={snapshotHistory}
            onDownload={onSnapshotRedownload}
            onDelete={onSnapshotDelete}
            onRename={onSnapshotRename}
            onPin={onSnapshotPin}
            limit={3}
          />

          {/* iter233 — inline Assessment Guide chatbot. Same triage
              flow that used to open as a modal, now living directly
              above the toolkit tiles so it's always in view. */}
          <AssessmentGuideChatInline
            onStartAssessment={onStartAssessment}
            safetyFlagged={safetyFlagged}
          />

          {/* iter234 — Co-Parenting Assessment progress tile with
              sparkline, section movers, radar, and the 60-day
              retake nudge. Hides itself cleanly when there's no
              history yet (empty state surfaces the sample link). */}
          <CpProgressTile
            onRetake={() => onStartAssessment("coparenting")}
          />

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="relative">
              <Link
                to="/nd-risk-assessment"
                data-testid="toolkit-link-assessment"
                className="block p-3 pb-8 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl text-slate-800 transition"
              >
                <i className="fa-solid fa-clipboard-question text-purple-800 text-base"></i>
                <div className="font-bold text-[11px] mt-1.5 leading-snug">
                  Co-parenting Assessment
                </div>
                <div className="text-[10px] text-slate-500 leading-snug">
                  Take the risk-and-strengths self-assessment
                </div>
                <a
                  href={`${process.env.REACT_APP_BACKEND_URL}/api/insights/samples/coparenting-self-assessment.pdf`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  data-testid="toolkit-coparenting-sample-link"
                  className="inline-flex items-center gap-1 mt-1 text-[9px] font-bold text-purple-800 hover:underline"
                >
                  <i className="fa-solid fa-file-pdf"></i>
                  See a sample
                </a>
              </Link>
              <button
                type="button"
                data-testid="toolkit-guided-coparenting"
                onClick={() => openGuidedJourney("coparenting")}
                className="absolute bottom-1.5 right-1.5 text-[9px] font-bold text-purple-800 bg-white/80 hover:bg-white px-2 py-0.5 rounded-full border border-purple-300"
              >
                <i className="fa-solid fa-comments mr-1"></i>Guided chat
              </button>
            </div>

            <div className="relative">
              <Link
                to="/safety-assessment"
                data-testid="toolkit-link-safety"
                className="block p-3 pb-8 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-xl text-slate-800 transition"
              >
                <i className="fa-solid fa-shield-heart text-rose-700 text-base"></i>
                <div className="font-bold text-[11px] mt-1.5 leading-snug">
                  Safety Screen
                </div>
                <div className="text-[10px] text-slate-500 leading-snug">
                  Full clinical Safety Assessment
                </div>
              </Link>
              <button
                type="button"
                data-testid="toolkit-guided-safety"
                onClick={() => openGuidedJourney("safety")}
                className="absolute bottom-1.5 right-1.5 text-[9px] font-bold text-rose-700 bg-white/80 hover:bg-white px-2 py-0.5 rounded-full border border-rose-300"
              >
                <i className="fa-solid fa-comments mr-1"></i>Guided chat
              </button>
            </div>

            <div className="relative">
              <Link
                to="/prep/child-goals"
                data-testid="toolkit-link-mediation"
                className="block p-3 pb-8 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-xl text-slate-800 transition"
              >
                <i className="fa-solid fa-file-signature text-amber-700 text-base"></i>
                <div className="font-bold text-[11px] mt-1.5 leading-snug">
                  Mediation Prep & Report
                </div>
                <div className="text-[10px] text-slate-500 leading-snug">
                  Build your Foundation Statement + summary
                </div>
              </Link>
              <button
                type="button"
                data-testid="toolkit-guided-foundation"
                onClick={() => openGuidedJourney("foundation")}
                className="absolute bottom-1.5 right-1.5 text-[9px] font-bold text-amber-800 bg-white/80 hover:bg-white px-2 py-0.5 rounded-full border border-amber-300"
              >
                <i className="fa-solid fa-comments mr-1"></i>Guided chat
              </button>
            </div>

            <div className="relative">
              <button
                type="button"
                data-testid="toolkit-link-foundation"
                onClick={downloadFoundationPdf}
                className="w-full p-3 pb-8 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl text-slate-800 text-left transition"
              >
                <i className="fa-solid fa-file-lines text-purple-800 text-base"></i>
                <div className="font-bold text-[11px] mt-1.5 leading-snug">
                  Foundation Statement PDF
                </div>
                <div className="text-[10px] text-slate-500 leading-snug">
                  Download your child-first anchor as PDF
                </div>
              </button>
              <button
                type="button"
                data-testid="toolkit-guided-foundation-pdf"
                onClick={() => openGuidedJourney("foundation")}
                className="absolute bottom-1.5 right-1.5 text-[9px] font-bold text-purple-800 bg-white/80 hover:bg-white px-2 py-0.5 rounded-full border border-purple-300"
              >
                <i className="fa-solid fa-comments mr-1"></i>Guided chat
              </button>
            </div>

            <div className="relative">
              <button
                type="button"
                data-testid="toolkit-link-medical"
                onClick={() => openAssessmentFolder("Medical")}
                className="w-full p-3 pb-8 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-xl text-slate-800 text-left transition"
              >
                <i className="fa-solid fa-stethoscope text-sky-700 text-base"></i>
                <div className="font-bold text-[11px] mt-1.5 leading-snug">
                  Medical Needs Assessment
                </div>
                <div className="text-[10px] text-slate-500 leading-snug">
                  Log providers, meds, appointments
                </div>
              </button>
              <button
                type="button"
                data-testid="toolkit-guided-medical"
                onClick={() => openGuidedJourney("medical")}
                className="absolute bottom-1.5 right-1.5 text-[9px] font-bold text-sky-800 bg-white/80 hover:bg-white px-2 py-0.5 rounded-full border border-sky-300"
              >
                <i className="fa-solid fa-comments mr-1"></i>Guided chat
              </button>
            </div>

            <div className="relative">
              <button
                type="button"
                data-testid="toolkit-link-educational"
                onClick={() => openAssessmentFolder("Educational")}
                className="w-full p-3 pb-8 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-xl text-slate-800 text-left transition"
              >
                <i className="fa-solid fa-graduation-cap text-amber-700 text-base"></i>
                <div className="font-bold text-[11px] mt-1.5 leading-snug">
                  Educational Assessment
                </div>
                <div className="text-[10px] text-slate-500 leading-snug">
                  Log IEPs, tutoring, teacher notes
                </div>
              </button>
              <button
                type="button"
                data-testid="toolkit-guided-educational"
                onClick={() => openGuidedJourney("educational")}
                className="absolute bottom-1.5 right-1.5 text-[9px] font-bold text-amber-800 bg-white/80 hover:bg-white px-2 py-0.5 rounded-full border border-amber-300"
              >
                <i className="fa-solid fa-comments mr-1"></i>Guided chat
              </button>
            </div>

            <div className="relative">
              <button
                type="button"
                data-testid="toolkit-link-psychological"
                onClick={() => openAssessmentFolder("Psychological")}
                className="w-full p-3 pb-8 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl text-slate-800 text-left transition"
              >
                <i className="fa-solid fa-brain text-indigo-700 text-base"></i>
                <div className="font-bold text-[11px] mt-1.5 leading-snug">
                  Psychological Assessment
                </div>
                <div className="text-[10px] text-slate-500 leading-snug">
                  Log therapists, evals, behavioural notes
                </div>
              </button>
              <button
                type="button"
                data-testid="toolkit-guided-psychological"
                onClick={() => openGuidedJourney("psychological")}
                className="absolute bottom-1.5 right-1.5 text-[9px] font-bold text-indigo-800 bg-white/80 hover:bg-white px-2 py-0.5 rounded-full border border-indigo-300"
              >
                <i className="fa-solid fa-comments mr-1"></i>Guided chat
              </button>
            </div>

            <Link
              to="/joint-reports"
              data-testid="toolkit-link-share-joint"
              className="p-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-slate-800 transition"
            >
              <i className="fa-solid fa-share-nodes text-slate-700 text-base"></i>
              <div className="font-bold text-[11px] mt-1.5 leading-snug">
                Share Joint Reports
              </div>
              <div className="text-[10px] text-slate-500 leading-snug">
                Send a joint report to a professional
              </div>
            </Link>
          </div>

          {/* Full-width Complete Coparenting Report CTA — assembles
              every artefact above (Safety Check + Co-parenting
              Assessment + Individual & Joint Align-Before-Agreement +
              Foundation Statement) into a single PDF. Sections the
              parent hasn't filled in yet render as empty-state stubs
              so a mediator/attorney sees exactly what's next. */}
          <div className="pt-1">
            <button
              type="button"
              data-testid="download-complete-report-btn"
              onClick={downloadCompleteReportPdf}
              className="w-full p-3 bg-purple-800 hover:bg-purple-900 text-white rounded-xl font-bold text-xs shadow-sm transition flex items-center justify-center gap-2"
            >
              <i className="fa-solid fa-file-invoice"></i>
              Download Complete Coparenting Report PDF
            </button>
            <button
              type="button"
              data-testid="share-complete-report-btn"
              onClick={onShareCompleteReport}
              className="w-full mt-2 p-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-xl font-bold text-[11px] transition flex items-center justify-center gap-2 disabled:opacity-40"
              disabled={shareStatus?.complete === "loading"}
            >
              <i className="fa-solid fa-link"></i>
              {shareStatus?.complete === "copied"
                ? "Share link copied!"
                : shareStatus?.complete === "loading"
                ? "Creating share link..."
                : "Share the Complete Report (link + passphrase)"}
            </button>
            <p className="text-[10px] text-slate-500 leading-snug mt-1.5 text-center">
              Includes: Family Violence Assessment · Co-parenting
              Assessment · Individual + Joint Align Before Agreement
              (Medical / Educational / Psychological) · Foundation
              Statement.
            </p>
          </div>
        </div>
      )}

      {/* OFFICIAL LEGAL REPORT MODULE — only when a Court Key is
          verified. Parent Journey (self-guided) hides this entirely
          per clinical guardrail (Legal Report is a court artefact). */}
      {!hideCourtOnly && (
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
      )}

      {/* ASSESSMENTS (formerly Align Before Agreement Records) */}
      <div
        id="assessment-records-section"
        data-testid="assessment-records-section"
        className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box"
      >
        <div className="flex justify-between items-center border-b border-slate-100 pb-2">
          <div>
            <span className="text-[10px] font-bold text-emerald-600 uppercase">
              Assessments
            </span>
            <h3 className="font-bold text-slate-800 text-sm">
              Medical, Educational & Psychological
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
            <div
              className="p-4 bg-emerald-50 border border-dashed border-emerald-300 rounded-xl text-center space-y-2"
              data-testid={`assessment-empty-${folderFilter.toLowerCase()}`}
            >
              <i className="fa-solid fa-folder-open text-emerald-600 text-lg"></i>
              <div className="font-bold text-slate-800 text-xs">
                {folderFilter === "All"
                  ? "You have 0 assessment records yet"
                  : `You have 0 ${folderFilter.toLowerCase()} records yet`}
              </div>
              <p className="text-[10px] text-slate-500 leading-snug">
                {folderFilter === "All"
                  ? "Add your first record — a provider name, a date, a short note. It saves privately to this device."
                  : folderFilter === "Medical"
                  ? "Log a provider, a diagnosis, a medication, or an upcoming appointment."
                  : folderFilter === "Educational"
                  ? "Log an IEP review, a teacher note, tutoring hours, or a school observation."
                  : "Log a therapist, an evaluation, a behavioural note, or a treatment plan."}
              </p>
              <button
                type="button"
                data-testid={`assessment-empty-add-${folderFilter.toLowerCase()}`}
                onClick={onAddAlignment}
                className="mt-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-[11px]"
              >
                <i className="fa-solid fa-plus mr-1"></i>Add your first{" "}
                {folderFilter === "All" ? "record" : folderFilter.toLowerCase() + " record"}
              </button>
            </div>
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

        {/* Email to Co-parent — iter219 replaces the generic
            "share with pediatrician" copy. Blocked when the parent's
            Safety Check flagged coercion / device / physical-safety
            risk (defense-in-depth: never facilitate outbound contact
            when the parent's own signal says it isn't safe). */}
        {safetyFlagged ? (
          <div
            data-testid="foundation-email-coparent-blocked"
            className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-[11px] no-print"
          >
            <div className="flex items-start gap-2">
              <i className="fa-solid fa-shield-heart text-rose-700 mt-0.5"></i>
              <div>
                <div className="font-bold text-rose-900">
                  Email to co-parent blocked
                </div>
                <p className="text-rose-800 leading-snug mt-0.5">
                  You flagged safety concerns on your Quick Safety
                  Check, so we won't help send your Foundation
                  Statement directly to your co-parent. Route through
                  your attorney or mediator instead.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <button
            type="button"
            data-testid="email-foundation-coparent-btn"
            onClick={onEmailFoundationToCoparent}
            disabled={shareStatus.foundation_email === "loading"}
            className="w-full p-2 bg-white hover:bg-purple-50 border border-purple-300 text-purple-800 rounded-xl font-bold text-[11px] transition flex items-center justify-center gap-2 disabled:opacity-40 no-print"
          >
            <i className="fa-solid fa-envelope"></i>
            {shareStatus.foundation_email === "loading"
              ? "Preparing email…"
              : "Email my Foundation Statement to my co-parent"}
          </button>
        )}
      </div>
    </div>
  );
}
