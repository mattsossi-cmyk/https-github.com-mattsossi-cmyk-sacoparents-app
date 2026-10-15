import React from "react";

import { AiDraftNotice } from "./commBuilder/AiDraftNotice";
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
        <span data-testid="risk-badge" data-status={status} className={`text-[10px] px-2 py-0.5 rounded ${tone}`}>
          {badge}
        </span>
      </div>
      <div data-testid="flag-list" className="text-slate-500 text-[11px]">
        {!checked ? (
          "Tap Get suggested wording to have AI check the tone."
        ) : flagList.length > 0 ? (
          flagList.map((f, i) => (
            <span key={i} className="text-rose-600 font-medium mr-2">
              • {f}
            </span>
          ))
        ) : (
          <span className="text-emerald-600 font-medium">• AI found no friction cues</span>
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
  return (
    <div className="space-y-4" data-testid="hub-section-biff">
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
                <i className="fa-solid fa-shield-halved" aria-hidden="true"></i>
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
            {PRESET_CHIPS.map(([key, testid, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => applyPreset(key)}
                data-testid={testid}
                className="bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 font-medium"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <AiDraftNotice testid="biff-ai-notice" />
          <textarea
            data-testid="raw-input"
            aria-label="Draft message"
            value={rawInput}
            onChange={(e) => onRawInputChange(e.target.value)}
            rows={4}
            className="w-full p-3 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-600 focus:outline-none"
            placeholder="Type draft message here..."
          />
          <button
            type="button"
            data-testid="biff-suggest-btn"
            onClick={onSuggest}
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
            <p className="text-[10px] font-bold uppercase tracking-wider text-purple-700 mb-1">Suggested wording</p>
            {biffStatus === "unavailable" ? (
              <SuggestUnavailable tp="biff" raw={rawInput} greyRock={safetyFlagged} onRetry={onSuggest} onUseTemplate={onRawInputChange} busy={biffLoading} />
            ) : biffStatus === "loading" ? (
              <p data-testid="biff-loading" className="text-purple-700">Getting suggested wording…</p>
            ) : ready ? (
              <p className="font-semibold text-purple-950 whitespace-pre-wrap">{biffOutput}</p>
            ) : (
              <p className="text-slate-400 italic">Suggested wording appears here after you tap Get suggested wording.</p>
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
