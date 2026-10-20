import React from "react";

import { AiGuardFrame, useAiGuard } from "../../components/aiNotice/AiGuard";
import { SuggestUnavailable } from "./commBuilder/SuggestUnavailable";

const PRESET_CHIPS = [
  ["late_handoff", "preset-late-handoff", "Late Handoff"],
  ["expense_request", "preset-expense-request", "Reimbursement"],
  ["schedule_change", "preset-schedule-change", "Schedule Swap"],
  ["medical_update", "preset-medical-update", "Medical Update"],
];

// Tone label only after AI has actually reviewed the draft.
function ToneRow({ status, riskLabel, flagList }) {
  const checked = status === "ai";
  const badge = checked ? riskLabel : status === "loading" ? "Checking…" : "Not checked yet";
  const tone = !checked
    ? "bg-slate-200 text-slate-600"
    : riskLabel === "Escalation Flag"
    ? "bg-rose-100 text-rose-700 font-bold"
    : "bg-emerald-100 text-emerald-700 font-bold";
  return (
    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
      <div className="flex justify-between items-center font-bold">
        <span className="text-slate-600">AI tone check:</span>
        <span data-testid="risk-badge" data-status={status} className={`text-[0.625rem] px-2 py-0.5 rounded ${tone}`}>
          {badge}
        </span>
      </div>
      <div data-testid="flag-list" className="text-slate-500 text-[0.6875rem]">
        {!checked ? (
          "Tap Get suggested wording to have AI check the tone."
        ) : flagList.length > 0 ? (
          flagList.map((f, i) => (
            <span key={i} className="text-rose-600 font-medium mr-2">
              • {f}
            </span>
          ))
        ) : (
          <span className="text-emerald-800 font-medium">• AI found no friction cues</span>
        )}
      </div>
    </div>
  );
}

/**
 * BiffTab — BIFF Communication Builder drawer content: composer,
 * communication history and milestones with the Weekly Progress PDF actions.
 */
export function BiffTab({
  rawInput,
  onRawInputChange,
  applyPreset,
  riskLabel,
  flagList,
  biffOutput,
  biffLoading,
  biffStatus = "idle",
  onSuggest,
  copyBiffOutput,
  copyToneSafe,
  logCommunication,
  biffLogs,
  milestones,
  successCount,
  frictionCount,
  addMilestoneLog,
  advocateReviewCount = 0,
  downloadWeeklyProgressPdf,
  onShareWeekly,
  shareStatus,
  safetyFlagged = false,
}) {
  const ready = biffStatus === "ai" && !!biffOutput;
  const guard = useAiGuard("biff", rawInput);
  const suggest = async () => (await guard.confirmSend(rawInput)) && onSuggest();
  const preset = async (key) => (await guard.confirmSend("")) && applyPreset(key);
  return (
    <div className="space-y-4" data-testid="hub-section-biff">
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
        <div className="border-b border-slate-100 pb-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="bg-amber-100 text-amber-800 text-[0.625rem] font-bold px-2 py-0.5 rounded uppercase">
              De-escalation Engine
            </span>
            {safetyFlagged && (
              <span
                data-testid="biff-greyrock-chip"
                className="inline-flex items-center gap-1 bg-slate-900 text-amber-300 text-[0.625rem] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
              >
                <i className="fa-solid fa-sliders" aria-hidden="true"></i>
                <span>Grey-rock tone on</span>
              </span>
            )}
          </div>
          <h3 className="font-bold text-slate-800 text-sm mt-1">
            BIFF Communication Builder
          </h3>
          <p className="text-[0.6875rem] text-slate-500">
            {safetyFlagged
              ? "Grey-rock BIFF: short, factual and neutral."
              : "Brief, Informative, Friendly, and Firm messaging."}
          </p>
        </div>

        <div className="no-print space-y-1.5">
          <label className="text-[0.625rem] font-bold text-slate-600 uppercase">
            Scenario Presets:
          </label>
          <div className="flex flex-wrap gap-1.5 text-[0.6875rem]">
            {PRESET_CHIPS.map(([key, testid, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => preset(key)}
                data-testid={testid}
                className="bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 font-medium"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <AiGuardFrame tp="biff" guard={guard}>
            <textarea
              {...guard.inputProps}
              data-testid="raw-input"
              aria-label="Draft message"
              value={rawInput}
              onChange={(e) => onRawInputChange(e.target.value)}
              rows={4}
              className="w-full p-3 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-600 focus:outline-none"
              placeholder="Type draft message here..."
            />
          </AiGuardFrame>
          <button
            type="button"
            data-testid="biff-suggest-btn"
            onClick={suggest}
            disabled={biffLoading || !rawInput.trim()}
            className="w-full bg-purple-700 hover:bg-purple-800 disabled:opacity-60 text-white font-bold py-2 rounded-xl text-xs transition shadow"
          >
            <i className={`fa-solid ${biffLoading ? "fa-spinner fa-spin" : "fa-wand-magic-sparkles"} mr-1.5`} aria-hidden="true"></i>
            {biffLoading ? "Getting suggested wording…" : "Get suggested wording"}
          </button>

          <ToneRow status={biffStatus} riskLabel={riskLabel} flagList={flagList} />

          <div
            data-testid="biff-output"
            data-status={biffStatus}
            className="p-3 bg-purple-50/70 border border-purple-200 rounded-xl text-xs text-slate-800 font-medium min-h-[80px]"
          >
            <p className="text-[0.625rem] font-bold uppercase tracking-wider text-purple-700 mb-1">Suggested wording</p>
            {biffStatus === "unavailable" ? (
              <SuggestUnavailable tp="biff" raw={rawInput} greyRock={safetyFlagged} onRetry={suggest} onUseTemplate={onRawInputChange} busy={biffLoading} />
            ) : biffStatus === "loading" ? (
              <p data-testid="biff-loading" className="text-purple-700">Getting suggested wording…</p>
            ) : ready ? (
              <p className="font-semibold text-purple-950 whitespace-pre-wrap">{biffOutput}</p>
            ) : (
              <p className="text-slate-600 italic">Suggested wording appears here after you tap Get suggested wording.</p>
            )}
          </div>

          <div className="flex gap-2 no-print">
            <button
              data-testid="copy-biff-btn"
              onClick={copyBiffOutput}
              disabled={!ready}
              className="flex-1 bg-purple-800 hover:bg-purple-900 disabled:opacity-50 text-white font-bold py-2 rounded-xl text-xs transition shadow"
            >
              Copy
            </button>
            <button
              data-testid="copy-tone-safe-btn"
              onClick={copyToneSafe}
              disabled={!ready}
              title="Copy with a date stamp for your own records"
              className="bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white font-bold px-3 py-2 rounded-xl text-xs shadow"
            >
              <i className="fa-regular fa-calendar-check mr-1"></i>Date stamp
            </button>
            <button
              data-testid="archive-biff-btn"
              onClick={logCommunication}
              disabled={!ready}
              className="bg-slate-800 disabled:opacity-50 text-white font-bold px-3 py-2 rounded-xl text-xs"
            >
              Save
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
          <p className="text-slate-600 text-center py-2">
            No archived messages yet.
          </p>
        ) : (
          biffLogs.map((item) => (
            <div
              key={item.id}
              className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1"
              data-testid={`biff-history-${item.id}`}
            >
              <div className="flex justify-between items-center text-[0.625rem]">
                <span className="font-bold text-purple-800">
                  {item.timestamp}
                </span>
                <span className="bg-purple-100 text-purple-900 px-1.5 py-0.5 rounded font-bold">
                  {item.category}
                </span>
              </div>
              <div className="text-[0.6875rem] text-slate-800 font-medium">
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
          <i className="fa-solid fa-chart-line text-emerald-600" aria-hidden="true"></i>{" "}
          History of Successes & Failures
        </h3>
        <button
          data-testid="add-milestone-btn"
          onClick={addMilestoneLog}
          className="no-print text-[0.625rem] bg-slate-800 text-white px-2 py-1 min-h-6 rounded-lg"
        >
          + Log Milestone
        </button>
      </div>

      {(
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl">
            <div
              data-testid="success-count"
              className="text-emerald-700 font-bold text-lg"
            >
              {successCount}
            </div>
            <div className="text-[0.625rem] text-emerald-800 font-semibold">
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
            <div className="text-[0.625rem] text-rose-800 font-semibold">
              Friction Points
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2 text-xs pt-1" data-testid="milestone-history-list">
        {milestones.length === 0 ? (
          <p className="text-slate-600 text-center py-1">
            No milestone events logged.
          </p>
        ) : (
          milestones.map((m) => {
            const isAdvocate = m.source === "advocate_review";
            const tagClass = isAdvocate
              ? "text-[0.5625rem] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-900"
              : m.type === "success"
              ? "text-[0.5625rem] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800"
              : m.type === "friction"
              ? "text-[0.5625rem] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800"
              : "text-[0.5625rem] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700";
            const tagLabel = isAdvocate ? "NOTE" : String(m.type || "note").toUpperCase();
            return (
              <div
                key={m.id}
                className="p-2 bg-slate-50 border border-slate-200 rounded-lg flex justify-between items-center text-xs"
                data-testid={`milestone-${m.id}`}
              >
                <div>
                  <span className="font-bold text-slate-800">{m.title}</span>
                  <div className="text-[0.625rem] text-slate-500">{m.note}</div>
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
      <p className="text-[0.625rem] text-slate-600 text-center no-print">
        One-page snapshot to share with your pediatrician, mediator, or attorney.
      </p>
    </div>
  );
}
