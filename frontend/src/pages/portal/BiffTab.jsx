import React from "react";

/**
 * BiffTab — Section II of the Parent Journey. Renders the BIFF
 * Communication Builder, communication history, milestones with kudos
 * loop, and the Weekly Progress PDF actions.
 */
export function BiffTab({
  // Composer
  rawInput,
  onRawInputChange,
  applyPreset,
  riskLabel,
  flagList,
  biffOutput,
  biffLoading,
  biffError,
  // Composer actions
  copyBiffOutput,
  copyToneSafe,
  logCommunication,
  // History
  biffLogs,
  // Milestones
  milestones,
  successCount,
  frictionCount,
  addMilestoneLog,
  advocateReviewCount = 0,
  // Weekly PDF
  downloadWeeklyProgressPdf,
  onShareWeekly,
  shareStatus,
  // Grey-rock coach chip (fires when the parent's Quick Safety
  // Check returned a coercion / device / physical-safety flag).
  safetyFlagged = false,
}) {
  return (
    <div className="space-y-4" data-testid="hub-section-biff">
      {/* BIFF Builder */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
        <div className="border-b border-slate-100 pb-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
              De-escalation Engine
            </span>
            {safetyFlagged && (
              <span
                data-testid="biff-greyrock-chip"
                title="Because your Quick Safety Check flagged coercion or safety concerns, the coach is producing shorter, more neutral replies."
                className="inline-flex items-center gap-1 bg-slate-900 text-amber-300 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
              >
                <span aria-hidden>🪨</span>
                <span>Grey-rock coach on</span>
              </span>
            )}
          </div>
          <h3 className="font-bold text-slate-800 text-sm mt-1">
            BIFF Communication Builder
          </h3>
          <p className="text-[11px] text-slate-500">
            {safetyFlagged
              ? "Grey-rock BIFF: short, factual, neutral. Safer to send to a coercive co-parent."
              : "Brief, Informative, Friendly, and Firm messaging."}
          </p>
        </div>

        <div className="no-print space-y-1.5">
          <label className="text-[10px] font-bold text-slate-400 uppercase">
            Scenario Presets:
          </label>
          <div className="flex flex-wrap gap-1.5 text-[11px]">
            <button
              onClick={() => applyPreset("late_handoff")}
              data-testid="preset-late-handoff"
              className="bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 font-medium"
            >
              Late Handoff
            </button>
            <button
              onClick={() => applyPreset("expense_request")}
              data-testid="preset-expense-request"
              className="bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 font-medium"
            >
              Reimbursement
            </button>
            <button
              onClick={() => applyPreset("schedule_change")}
              data-testid="preset-schedule-change"
              className="bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 font-medium"
            >
              Schedule Swap
            </button>
            <button
              onClick={() => applyPreset("medical_update")}
              data-testid="preset-medical-update"
              className="bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 font-medium"
            >
              Medical Update
            </button>
          </div>
        </div>

        <div className="space-y-2">
          <textarea
            data-testid="raw-input"
            value={rawInput}
            onChange={(e) => onRawInputChange(e.target.value)}
            rows={4}
            className="w-full p-3 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-600 focus:outline-none"
            placeholder="Type draft message here..."
          />

          <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
            <div className="flex justify-between items-center font-bold">
              <span className="text-slate-600">Tone Risk Analysis:</span>
              <span
                data-testid="risk-badge"
                className={
                  riskLabel === "Escalation Flag"
                    ? "text-[10px] px-2 py-0.5 rounded bg-rose-100 text-rose-700 font-bold"
                    : riskLabel === "Low Risk"
                    ? "text-[10px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 font-bold"
                    : "text-[10px] px-2 py-0.5 rounded bg-slate-200 text-slate-600"
                }
              >
                {riskLabel}
              </span>
            </div>
            <div data-testid="flag-list" className="text-slate-500 text-[11px]">
              {rawInput.trim() === "" ? (
                "Type above to run analysis..."
              ) : flagList.length > 0 ? (
                flagList.map((f, i) => (
                  <span key={i} className="text-rose-600 font-medium mr-2">
                    • {f}
                  </span>
                ))
              ) : (
                <span className="text-emerald-600 font-medium">
                  • Factual structure detected
                </span>
              )}
            </div>
            {(biffLoading || biffError) && (
              <div
                data-testid="biff-loading"
                className="text-[10px] text-purple-700 font-semibold pt-1 flex items-center gap-1"
              >
                {biffLoading ? (
                  <>
                    <i className="fa-solid fa-wand-magic-sparkles"></i>
                    Coach refining…
                  </>
                ) : (
                  <span className="text-amber-700">{biffError}</span>
                )}
              </div>
            )}
          </div>

          <div
            data-testid="biff-output"
            className="p-3 bg-purple-50/70 border border-purple-200 rounded-xl text-xs text-slate-800 font-medium min-h-[80px]"
          >
            {biffOutput ? (
              <p className="font-semibold text-purple-950">{biffOutput}</p>
            ) : (
              <p className="text-slate-400 italic">
                Reformulated BIFF message appears here...
              </p>
            )}
          </div>

          <div className="flex gap-2 no-print">
            <button
              data-testid="copy-biff-btn"
              onClick={copyBiffOutput}
              className="flex-1 bg-purple-800 hover:bg-purple-900 text-white font-bold py-2 rounded-xl text-xs transition shadow"
            >
              Copy BIFF
            </button>
            <button
              data-testid="copy-tone-safe-btn"
              onClick={copyToneSafe}
              title="Copy BIFF + a date/case audit stamp — safe to share with attorneys or mediators"
              className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-3 py-2 rounded-xl text-xs shadow"
            >
              <i className="fa-solid fa-shield-halved mr-1"></i>Tone-Safe
            </button>
            <button
              data-testid="archive-biff-btn"
              onClick={logCommunication}
              className="bg-slate-800 text-white font-bold px-3 py-2 rounded-xl text-xs"
            >
              Archive
            </button>
          </div>
        </div>
      </div>

      <BiffHistory biffLogs={biffLogs} />
      <BiffMilestones
        safetyFlagged={safetyFlagged}
        milestones={milestones}
        successCount={successCount}
        frictionCount={frictionCount}
        addMilestoneLog={addMilestoneLog}
        advocateReviewCount={advocateReviewCount}
        downloadWeeklyProgressPdf={downloadWeeklyProgressPdf}
        onShareWeekly={onShareWeekly}
        shareStatus={shareStatus}
      />
    </div>
  );
}

export function BiffHistory({ biffLogs }) {
  return (
    <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
      <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
        <i className="fa-solid fa-clock-rotate-left text-purple-700"></i>{" "}
        History of Communications
      </h3>
      <div className="space-y-2 text-xs" data-testid="biff-history-list">
        {biffLogs.length === 0 ? (
          <p className="text-slate-400 text-center py-2">
            No archived messages yet.
          </p>
        ) : (
          biffLogs.map((item) => (
            <div
              key={item.id}
              className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1"
              data-testid={`biff-history-${item.id}`}
            >
              <div className="flex justify-between items-center text-[10px]">
                <span className="font-bold text-purple-800">
                  {item.timestamp}
                </span>
                <span className="bg-purple-100 text-purple-900 px-1.5 py-0.5 rounded font-bold">
                  {item.category}
                </span>
              </div>
              <div className="text-[11px] text-slate-800 font-medium">
                {item.biff}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function BiffMilestones({
  safetyFlagged = false,
  milestones,
  successCount,
  frictionCount,
  addMilestoneLog,
  advocateReviewCount = 0,
  downloadWeeklyProgressPdf,
  onShareWeekly,
  shareStatus,
}) {
  return (
    <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
      <div className="flex justify-between items-center">
        <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
          {safetyFlagged ? (
            <>
              <i className="fa-solid fa-clipboard-list text-purple-800"></i>{" "}
              Advocate Review Log
            </>
          ) : (
            <>
              <i className="fa-solid fa-chart-line text-emerald-600"></i>{" "}
              History of Successes & Failures
            </>
          )}
        </h3>
        <button
          data-testid="add-milestone-btn"
          onClick={addMilestoneLog}
          className={
            safetyFlagged
              ? "no-print text-[10px] bg-purple-800 text-white px-2 py-1 rounded-lg"
              : "no-print text-[10px] bg-slate-800 text-white px-2 py-1 rounded-lg"
          }
        >
          {safetyFlagged ? "+ Log for advocate" : "+ Log Milestone"}
        </button>
      </div>

      {safetyFlagged ? (
        <div
          className="p-3 bg-purple-50 border border-purple-200 rounded-xl text-center"
          data-testid="advocate-review-tile"
        >
          <div
            data-testid="advocate-review-count"
            className="text-purple-900 font-bold text-lg"
          >
            {advocateReviewCount}
          </div>
          <div className="text-[10px] text-purple-800 font-semibold">
            Events logged for advocate / attorney review
          </div>
          <p className="text-[10px] text-slate-500 mt-1 leading-snug">
            The collaborative "Successful Resolution / Friction Point"
            framing doesn't fit the safety context you flagged. Each
            entry here goes into your Weekly Progress PDF for your
            advocate.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl">
            <div
              data-testid="success-count"
              className="text-emerald-700 font-bold text-lg"
            >
              {successCount}
            </div>
            <div className="text-[10px] text-emerald-800 font-semibold">
              Successful Resolutions
            </div>
          </div>
          <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-xl">
            <div
              data-testid="friction-count"
              className="text-rose-700 font-bold text-lg"
            >
              {frictionCount}
            </div>
            <div className="text-[10px] text-rose-800 font-semibold">
              Friction Points
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2 text-xs pt-1" data-testid="milestone-history-list">
        {milestones.length === 0 ? (
          <p className="text-slate-400 text-center py-1">
            No milestone events logged.
          </p>
        ) : (
          milestones.map((m) => {
            const isAdvocate = m.source === "advocate_review";
            const tagClass = isAdvocate
              ? "text-[9px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-900"
              : m.type === "success"
              ? "text-[9px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800"
              : "text-[9px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800";
            const tagLabel = isAdvocate ? "ADVOCATE" : m.type.toUpperCase();
            return (
              <div
                key={m.id}
                className="p-2 bg-slate-50 border border-slate-200 rounded-lg flex justify-between items-center text-xs"
                data-testid={`milestone-${m.id}`}
              >
                <div>
                  <span className="font-bold text-slate-800">{m.title}</span>
                  <div className="text-[10px] text-slate-500">{m.note}</div>
                </div>
                <span className={tagClass} data-testid={`milestone-tag-${m.id}`}>
                  {tagLabel}
                </span>
              </div>
            );
          })
        )}
      </div>

      <div className="flex gap-2 no-print">
        <button
          data-testid="export-weekly-progress-pdf-btn"
          onClick={downloadWeeklyProgressPdf}
          className="flex-1 bg-purple-900 hover:bg-purple-950 text-white font-bold py-2 rounded-xl text-xs shadow"
        >
          <i className="fa-solid fa-file-pdf mr-1"></i>
          Export Weekly Progress PDF
        </button>
        <button
          data-testid="share-weekly-btn"
          onClick={onShareWeekly}
          title="Copy a 30-day share link"
          className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-3 py-2 rounded-xl text-xs shadow disabled:opacity-60"
          disabled={shareStatus.weekly === "loading"}
        >
          <i className="fa-solid fa-link"></i>{" "}
          {shareStatus.weekly === "loading"
            ? "…"
            : shareStatus.weekly === "copied"
            ? "Copied!"
            : "Share"}
        </button>
      </div>
      <p className="text-[10px] text-slate-400 text-center no-print">
        One-page snapshot to share with your pediatrician, mediator, or attorney.
      </p>
    </div>
  );
}
