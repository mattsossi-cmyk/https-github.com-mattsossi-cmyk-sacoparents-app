import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

/**
 * sacoparentsapp.online — Child-Centered Co-Parenting Portal (Full Rewrite)
 *
 * Mobile-first single-page portal implemented as a React conversion of the
 * user-provided HTML/Tailwind mockup. Uses localStorage as the sole data store
 * (per mockup design). No backend calls. Backend code is intentionally left
 * intact server-side to continue serving the sibling sacoparentsalign.com app.
 */

const BIFF_LOG_KEY = "sacoparents_biff_logs";
const ALIGN_RECORDS_KEY = "sacoparents_align_records";
const MILESTONE_KEY = "sacoparents_milestone_logs";
const FOUNDATION_KEY = "sacoparents_foundation_statement";
const LEGAL_REPORT_KEY = "sacoparents_legal_report";
const HEALTH_INDEX_KEY = "sacoparents_health_index";
const COURT_KEY_KEY = "sacoparents_court_key";
const REASSESSMENT_KEY = "sacoparents_reassessments";
const SYNC_PENDING_KEY = "sacoparents_sync_pending"; // '1' if a PUT is queued

const PRESETS = {
  late_handoff: {
    raw: "You were late again by 20 minutes! You have zero respect for my time or the schedule.",
    biff:
      "Thank you for letting me know. I ran into unexpected traffic and arrived at 4:20 PM. I will plan for extra transit time for our next pickup on Friday.",
    flags: ["Hostile tone", "Accusatory phrase ('zero respect')"],
  },
  expense_request: {
    raw: "I bought the required school uniforms and you need to pay me back half right now. Stop ignoring your duties!",
    biff:
      "The total for the required school uniforms came to $80. Attached is the receipt for your half ($40). Please let me know if you can send reimbursement by the end of the month. Thanks.",
    flags: ["Demanding tone", "Blame language"],
  },
  schedule_change: {
    raw: "I need to switch next weekend because I have a work event. You always refuse to help out.",
    biff:
      "I have a mandatory work event next weekend (Oct 12-14). I would like to request swapping for the following weekend (Oct 19-21). Please let me know if that works for your calendar by Thursday. Thank you.",
    flags: ["Passive aggressive comment"],
  },
  medical_update: {
    raw: "I took Alex to the doctor. You never check in on his asthma symptoms as usual.",
    biff:
      "Alex had his regular pediatric checkup today. The doctor updated his asthma inhaler prescription. I have uploaded the visit summary to the Medical folder for your review.",
    flags: ["Personal attack ('You never check in')"],
  },
};

const DEFAULT_ALIGNMENTS = [
  {
    id: 1,
    category: "Medical",
    title: "Pediatric Asthma Management Plan",
    provider: "Dr. Evelyn Vance",
    date: "2026-08-14",
    summary:
      "Daily preventative inhaler approved. Emergency inhaler remains in backpack.",
  },
  {
    id: 2,
    category: "Educational",
    title: "Q1 Reading Progress Assessment",
    provider: "Oakridge Elementary",
    date: "2026-09-10",
    summary:
      "Reading at grade level. Recommended 20 minutes quiet reading nightly.",
  },
  {
    id: 3,
    category: "Psychological",
    title: "Child Transition Consultation",
    provider: "Dr. Marcus Thorne",
    date: "2026-07-22",
    summary:
      "Child benefits from visual calendar checklists in both bedrooms.",
  },
];

const DEFAULT_MILESTONES = [
  {
    id: 1,
    type: "success",
    title: "On-Time Handoff Completed",
    date: "2026-09-22",
    note: "Exchanged at neutral drop-off point without friction.",
  },
  {
    id: 2,
    type: "friction",
    title: "Schedule Request Delay",
    date: "2026-09-18",
    note: "Required 24-hr reminder before confirmation.",
  },
];

const DEFAULT_FOUNDATION =
  "Our primary goal remains the emotional wellbeing, stability, and health of our child. We commit to clear, low-conflict BIFF communication, respecting schedule boundaries, and sharing vital medical, educational, and psychological records promptly.";

const DEFAULT_LEGAL_REPORT = {
  sigA: "",
  sigB: "",
  sigMed: "Matt Sossi, Licensed Mediator (San Antonio, TX)",
};

const DEFAULT_HEALTH_INDEX = { s1: 7, s2: 6, s3: 5 };

const DEFAULT_BIFF_LOGS = [
  {
    id: 1,
    timestamp: "2026-09-20 14:30",
    category: "Handoff Delay",
    original: "You are late again.",
    biff:
      "Thank you for checking in. Arrived at 4:15 PM due to traffic.",
  },
];

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (raw == null) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore quota */
  }
}

function readString(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw == null ? fallback : raw;
  } catch {
    return fallback;
  }
}

function writeString(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore quota */
  }
}

function computeHealthLabel(avg) {
  if (avg >= 7.5) return "High Alignment";
  if (avg >= 5.5) return "Moderate Alignment";
  return "Low Alignment";
}

/**
 * TrendSparkline — tiny SVG line chart showing the last N reassessment
 * averages plus the current one. Renders a helpful hint if fewer than 2
 * data points exist so the parent knows what to do next.
 */
function TrendSparkline({ series, currentAvg }) {
  const points = React.useMemo(() => {
    const base = Array.isArray(series) ? [...series] : [];
    if (Number.isFinite(currentAvg)) base.push(Number(currentAvg));
    return base.filter((v) => Number.isFinite(v));
  }, [series, currentAvg]);

  if (points.length < 2) {
    return (
      <div
        data-testid="trend-sparkline-empty"
        className="text-[10px] text-slate-500 italic mt-2 flex items-center gap-1"
      >
        <i className="fa-solid fa-chart-line text-purple-700"></i>
        Log at least one Reassessment above to unlock your trend line.
      </div>
    );
  }

  const width = 240;
  const height = 40;
  const step = points.length > 1 ? width / (points.length - 1) : width;
  const toY = (v) => height - (Math.max(0, Math.min(10, v)) / 10) * height;
  const path = points
    .map((v, i) => `${i === 0 ? "M" : "L"} ${(i * step).toFixed(1)} ${toY(v).toFixed(1)}`)
    .join(" ");

  const first = points[0];
  const last = points[points.length - 1];
  const delta = last - first;
  const deltaLabel =
    delta > 0.05
      ? `▲ +${delta.toFixed(1)} vs first point`
      : delta < -0.05
      ? `▼ ${delta.toFixed(1)} vs first point`
      : "◆ Flat";
  const deltaColor =
    delta > 0.05 ? "text-emerald-700" : delta < -0.05 ? "text-rose-700" : "text-slate-500";

  return (
    <div
      className="mt-2 p-2.5 bg-white rounded-lg border border-purple-200"
      data-testid="trend-sparkline"
    >
      <div className="flex justify-between items-center mb-1">
        <span className="text-[9px] font-bold text-purple-800 uppercase">
          Trend (last {points.length - 1} reassessment{points.length - 1 === 1 ? "" : "s"} + now)
        </span>
        <span
          data-testid="trend-delta"
          className={`text-[10px] font-bold ${deltaColor}`}
        >
          {deltaLabel}
        </span>
      </div>
      <svg
        viewBox={`-2 -2 ${width + 4} ${height + 4}`}
        preserveAspectRatio="none"
        className="w-full h-10"
        aria-label="Trend line of reassessment scores"
      >
        {/* mid line */}
        <line
          x1="0"
          y1={toY(5)}
          x2={width}
          y2={toY(5)}
          stroke="#E9DFF6"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        <path d={path} fill="none" stroke="#6D28D9" strokeWidth="2" strokeLinejoin="round" />
        {points.map((v, i) => (
          <circle
            key={i}
            cx={(i * step).toFixed(1)}
            cy={toY(v).toFixed(1)}
            r="2.5"
            fill={i === points.length - 1 ? "#4A1A6E" : "#6D28D9"}
          />
        ))}
      </svg>
      <div className="text-[9px] text-slate-400 text-center mt-1">
        {points.map((v) => v.toFixed(1)).join(" → ")}
      </div>
    </div>
  );
}

export default function SacoparentsPortal() {
  const { user } = useAuth();
  // Screen state: 'gateway' | 'court-key' | 'parent-journey'
  const [screen, setScreen] = useState("gateway");
  const [hubSection, setHubSection] = useState("alignment"); // 'alignment' | 'biff'

  // Persistent data
  const [alignRecords, setAlignRecords] = useState([]);
  const [biffLogs, setBiffLogs] = useState([]);
  const [milestones, setMilestones] = useState([]);
  const [reassessments, setReassessments] = useState([]);
  const [foundationText, setFoundationText] = useState(DEFAULT_FOUNDATION);
  const [legalReport, setLegalReport] = useState(DEFAULT_LEGAL_REPORT);
  const [healthIndex, setHealthIndex] = useState(DEFAULT_HEALTH_INDEX);
  const [courtKey, setCourtKey] = useState("");

  // Court-key screen state
  const [courtKeyInput, setCourtKeyInput] = useState("");

  // Alignment filter
  const [folderFilter, setFolderFilter] = useState("All");

  // BIFF composer state
  const [rawInput, setRawInput] = useState("");
  const [biffOutput, setBiffOutput] = useState("");
  const [flagList, setFlagList] = useState([]);
  const [riskLabel, setRiskLabel] = useState("Neutral");

  // Modal state
  const [reassessOpen, setReassessOpen] = useState(false);
  const [alignmentOpen, setAlignmentOpen] = useState(false);

  // Reassessment form state
  const [reassStage, setReassStage] = useState("30-Day Progress Review");
  const [reassNotes, setReassNotes] = useState("");

  // Alignment form state
  const [alignCategory, setAlignCategory] = useState("Medical");
  const [alignTitle, setAlignTitle] = useState("");
  const [alignProvider, setAlignProvider] = useState("");
  const [alignDate, setAlignDate] = useState("");
  const [alignSummary, setAlignSummary] = useState("");

  const initialisedRef = useRef(false);
  const printDate = useMemo(() => new Date().toLocaleDateString(), []);

  // BIFF live-refine state
  const [biffLoading, setBiffLoading] = useState(false);
  const [biffError, setBiffError] = useState("");
  const biffAbortRef = useRef(null);
  const biffDebounceRef = useRef(null);

  // Court key verify state
  const [courtKeyError, setCourtKeyError] = useState("");
  const [courtKeyLoading, setCourtKeyLoading] = useState(false);
  const [verifiedMediator, setVerifiedMediator] = useState("");

  // Sync state
  const [syncStatus, setSyncStatus] = useState("idle"); // 'idle'|'syncing'|'synced'|'error'
  const syncDebounceRef = useRef(null);
  const hasHydratedFromServerRef = useRef(false);

  // Hydrate from localStorage on mount (idempotent seed)
  useEffect(() => {
    if (initialisedRef.current) return;
    initialisedRef.current = true;

    const seededAlignments = readJson(ALIGN_RECORDS_KEY, null);
    if (seededAlignments == null) writeJson(ALIGN_RECORDS_KEY, DEFAULT_ALIGNMENTS);
    setAlignRecords(seededAlignments ?? DEFAULT_ALIGNMENTS);

    const seededMilestones = readJson(MILESTONE_KEY, null);
    if (seededMilestones == null) writeJson(MILESTONE_KEY, DEFAULT_MILESTONES);
    setMilestones(seededMilestones ?? DEFAULT_MILESTONES);

    const seededFoundation = readString(FOUNDATION_KEY, null);
    if (seededFoundation == null) writeString(FOUNDATION_KEY, DEFAULT_FOUNDATION);
    setFoundationText(seededFoundation ?? DEFAULT_FOUNDATION);

    const seededLegal = readJson(LEGAL_REPORT_KEY, null);
    setLegalReport({ ...DEFAULT_LEGAL_REPORT, ...(seededLegal || {}) });

    const seededHealth = readJson(HEALTH_INDEX_KEY, null);
    setHealthIndex({ ...DEFAULT_HEALTH_INDEX, ...(seededHealth || {}) });

    const seededLogs = readJson(BIFF_LOG_KEY, null);
    if (seededLogs == null) writeJson(BIFF_LOG_KEY, DEFAULT_BIFF_LOGS);
    setBiffLogs(seededLogs ?? DEFAULT_BIFF_LOGS);

    const seededReassessments = readJson(REASSESSMENT_KEY, null);
    setReassessments(seededReassessments ?? []);

    const seededCourtKey = readString(COURT_KEY_KEY, "");
    setCourtKey(seededCourtKey);
  }, []);

  // Cross-device sync: if the user is signed in, pull server state on mount
  // (server wins over localStorage — that's the whole point of cross-device
  // sync) then push any subsequent mutation back to the server.
  useEffect(() => {
    if (!user) {
      hasHydratedFromServerRef.current = false;
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/portal/state");
        if (cancelled || !data?.exists) {
          // No server state yet — first sync will be a push, not a pull.
          hasHydratedFromServerRef.current = true;
          return;
        }
        const s = data.state || {};
        if (Array.isArray(s.align_records)) {
          setAlignRecords(s.align_records);
          writeJson(ALIGN_RECORDS_KEY, s.align_records);
        }
        if (Array.isArray(s.milestones)) {
          setMilestones(s.milestones);
          writeJson(MILESTONE_KEY, s.milestones);
        }
        if (Array.isArray(s.biff_logs)) {
          setBiffLogs(s.biff_logs);
          writeJson(BIFF_LOG_KEY, s.biff_logs);
        }
        if (Array.isArray(s.reassessments)) {
          setReassessments(s.reassessments);
          writeJson(REASSESSMENT_KEY, s.reassessments);
        }
        if (typeof s.foundation_text === "string") {
          setFoundationText(s.foundation_text);
          writeString(FOUNDATION_KEY, s.foundation_text);
        }
        if (s.legal_report && typeof s.legal_report === "object") {
          setLegalReport({ ...DEFAULT_LEGAL_REPORT, ...s.legal_report });
          writeJson(LEGAL_REPORT_KEY, s.legal_report);
        }
        if (s.health_index && typeof s.health_index === "object") {
          setHealthIndex({ ...DEFAULT_HEALTH_INDEX, ...s.health_index });
          writeJson(HEALTH_INDEX_KEY, s.health_index);
        }
        if (typeof s.court_key === "string") {
          setCourtKey(s.court_key);
          writeString(COURT_KEY_KEY, s.court_key);
        }
        hasHydratedFromServerRef.current = true;
      } catch {
        // Silent: sync is best-effort; localStorage still works.
        hasHydratedFromServerRef.current = true;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  // Debounced server push. Waits for the initial pull to complete so we
  // don't clobber server state with our defaults on the very first render.
  // Also handles offline / transient failure by marking a "pending" flag in
  // localStorage — the next successful hydrate + effect firing will re-push
  // the current state, so nothing is ever silently dropped.
  useEffect(() => {
    if (!user) return;
    if (!hasHydratedFromServerRef.current) return;
    if (syncDebounceRef.current) clearTimeout(syncDebounceRef.current);
    syncDebounceRef.current = setTimeout(async () => {
      if (typeof navigator !== "undefined" && navigator.onLine === false) {
        writeString(SYNC_PENDING_KEY, "1");
        setSyncStatus("offline");
        return;
      }
      setSyncStatus("syncing");
      try {
        await api.put("/portal/state", {
          align_records: alignRecords,
          milestones,
          biff_logs: biffLogs,
          foundation_text: foundationText,
          legal_report: legalReport,
          health_index: healthIndex,
          court_key: courtKey,
          reassessments,
        });
        writeString(SYNC_PENDING_KEY, "");
        setSyncStatus("synced");
      } catch {
        writeString(SYNC_PENDING_KEY, "1");
        setSyncStatus("error");
      }
    }, 700);
    return () => {
      if (syncDebounceRef.current) clearTimeout(syncDebounceRef.current);
    };
  }, [
    user,
    alignRecords,
    milestones,
    biffLogs,
    foundationText,
    legalReport,
    healthIndex,
    courtKey,
    reassessments,
  ]);

  // Flush queued PUT when we come back online (or on mount if a pending
  // flush was left over from last session). Re-uses the same debounced
  // effect above by bumping a state var, so we don't duplicate logic.
  const [onlineTick, setOnlineTick] = useState(0);
  useEffect(() => {
    if (!user) return;
    // On mount: if a queued flush is pending, trigger a re-sync.
    const pending = readString(SYNC_PENDING_KEY, "");
    if (pending === "1" && typeof navigator !== "undefined" && navigator.onLine !== false) {
      setOnlineTick((t) => t + 1);
    }
    const onOnline = () => {
      setOnlineTick((t) => t + 1);
    };
    if (typeof window !== "undefined") {
      window.addEventListener("online", onOnline);
      return () => window.removeEventListener("online", onOnline);
    }
    return undefined;
  }, [user]);

  // When onlineTick bumps, force the debounced PUT effect above to re-run
  // by re-writing the health index to itself (no user-visible change).
  useEffect(() => {
    if (onlineTick === 0) return;
    setHealthIndex((prev) => ({ ...prev }));
  }, [onlineTick]);

  // Compute Overall Co-Parenting Health Index (avg)
  const healthAvg = useMemo(() => {
    const s1 = Number(healthIndex.s1) || 0;
    const s2 = Number(healthIndex.s2) || 0;
    const s3 = Number(healthIndex.s3) || 0;
    return ((s1 + s2 + s3) / 3).toFixed(1);
  }, [healthIndex]);

  const healthLabel = useMemo(() => computeHealthLabel(Number(healthAvg)), [healthAvg]);

  // Last 4 reassessment averages (oldest → newest) — powers the sparkline.
  const trendSeries = useMemo(() => {
    if (!reassessments || reassessments.length === 0) return [];
    const ordered = [...reassessments]
      .sort((a, b) => (a.date || "").localeCompare(b.date || ""))
      .slice(-4);
    const out = [];
    for (const rec of ordered) {
      let avg = rec.avg;
      if (avg == null && rec.snapshot) {
        const s1 = Number(rec.snapshot.s1);
        const s2 = Number(rec.snapshot.s2);
        const s3 = Number(rec.snapshot.s3);
        if (Number.isFinite(s1) && Number.isFinite(s2) && Number.isFinite(s3)) {
          avg = (s1 + s2 + s3) / 3;
        }
      }
      if (Number.isFinite(Number(avg))) out.push(Number(avg));
    }
    return out;
  }, [reassessments]);

  const setHealthScore = useCallback((key, value) => {
    setHealthIndex((prev) => {
      const next = { ...prev, [key]: Number(value) };
      writeJson(HEALTH_INDEX_KEY, next);
      return next;
    });
  }, []);

  // Navigation
  const openDoorGateway = useCallback(() => setScreen("gateway"), []);
  const enterParentJourney = useCallback(() => setScreen("parent-journey"), []);
  const enterCourtPath = useCallback(() => setScreen("court-key"), []);

  const verifyProfessionalKey = useCallback(async () => {
    const key = courtKeyInput.trim();
    if (!key) {
      setCourtKeyError("Please enter a key code from sacoparentsalign.com");
      return;
    }
    setCourtKeyLoading(true);
    setCourtKeyError("");
    try {
      const { data } = await api.post("/portal/court-keys/verify", { key });
      if (!data?.verified) {
        const reasonMap = {
          expired: "That key has expired — please request a new one from your mediator.",
          revoked: "That key has been revoked. Contact your mediator for a replacement.",
          unknown_key: "We don't recognise that key. Double-check the code or ask your mediator.",
        };
        setCourtKeyError(
          reasonMap[data?.reason] ||
            "We couldn't verify that key. Please check the code and try again."
        );
        setCourtKeyLoading(false);
        return;
      }
      const caseId = data.case_id || key;
      const mediator =
        data.mediator_name || "Matt Sossi, Licensed Mediator (San Antonio, TX)";
      setCourtKey(caseId);
      setVerifiedMediator(mediator);
      writeString(COURT_KEY_KEY, caseId);
      setScreen("parent-journey");
    } catch {
      setCourtKeyError(
        "Network issue while verifying. Please check your connection and try again."
      );
    } finally {
      setCourtKeyLoading(false);
    }
  }, [courtKeyInput]);

  // Foundation Statement
  const saveFoundationText = useCallback(() => {
    writeString(FOUNDATION_KEY, foundationText);
    alert("Foundation Statement PDF draft saved!");
  }, [foundationText]);

  // Legal Report
  const saveLegalReport = useCallback(() => {
    writeJson(LEGAL_REPORT_KEY, legalReport);
    alert("Official Legal Conflict Resolution Report draft saved!");
  }, [legalReport]);

  // BIFF analysis (local regex — instant, used while typing before AI kicks in)
  const runLocalAnalysis = useCallback((val) => {
    const trimmed = (val || "").trim();
    if (!trimmed) {
      setFlagList([]);
      setBiffOutput("");
      setRiskLabel("Neutral");
      return;
    }
    const flags = [];
    if (/always|never|you do/i.test(trimmed)) flags.push("Accusatory phrasing");
    if (/!{2,}/.test(trimmed)) flags.push("High intensity");
    setFlagList(flags);
    setRiskLabel(flags.length > 0 ? "Escalation Flag" : "Low Risk");
    setBiffOutput(
      `Thank you for your message. ${trimmed.substring(0, 100)}... Let's maintain focus on the child's schedule. Thanks.`
    );
  }, []);

  // Debounced Claude refinement (falls back to local regex if the API errors).
  const runAiRefine = useCallback((val) => {
    if (biffDebounceRef.current) clearTimeout(biffDebounceRef.current);
    if (biffAbortRef.current) {
      try {
        biffAbortRef.current.abort();
      } catch {
        /* noop */
      }
    }
    const trimmed = (val || "").trim();
    if (!trimmed) {
      setBiffLoading(false);
      setBiffError("");
      return;
    }
    biffDebounceRef.current = setTimeout(async () => {
      setBiffLoading(true);
      setBiffError("");
      const controller = new AbortController();
      biffAbortRef.current = controller;
      try {
        const { data } = await api.post(
          "/portal/biff-refine",
          { raw: trimmed },
          { signal: controller.signal }
        );
        if (data?.biff) {
          setBiffOutput(data.biff);
          setFlagList(Array.isArray(data.flags) ? data.flags : []);
          setRiskLabel(
            data.risk === "Escalation Flag" || data.risk === "Low Risk"
              ? data.risk
              : (data.flags || []).length
              ? "Escalation Flag"
              : "Low Risk"
          );
        }
      } catch (err) {
        if (err?.name === "CanceledError" || err?.code === "ERR_CANCELED") return;
        setBiffError("Coach is warming up — using local guidance for now.");
      } finally {
        setBiffLoading(false);
      }
    }, 900);
  }, []);

  const handleRawInputChange = useCallback(
    (val) => {
      setRawInput(val);
      runLocalAnalysis(val);
      runAiRefine(val);
    },
    [runLocalAnalysis, runAiRefine]
  );

  const applyPreset = useCallback((key) => {
    const p = PRESETS[key];
    if (!p) return;
    setRawInput(p.raw);
    setFlagList(p.flags);
    setRiskLabel(p.flags.length > 0 ? "Escalation Flag" : "Low Risk");
    setBiffOutput(p.biff);
    // Also fire the AI refine so the user sees a fresh, tailored rewrite.
    runAiRefine(p.raw);
  }, [runAiRefine]);

  const copyBiffOutput = useCallback(() => {
    if (!biffOutput) return;
    try {
      navigator.clipboard.writeText(biffOutput);
      alert("BIFF message copied!");
    } catch {
      alert("Clipboard unavailable — please copy manually.");
    }
  }, [biffOutput]);

  // Tone-safe copy = BIFF body + a short audit stamp (date + case ref +
  // origin) so attorneys/mediators can see this message went through the
  // BIFF coach on a specific date, not that the parent hand-wrote it.
  // Also fires a "Kudos" success-milestone when the draft was flagged as
  // an Escalation Flag — visible proof the coach kept a hot message safe.
  const copyToneSafe = useCallback(() => {
    if (!biffOutput) return;
    const stamp = [
      "",
      "---",
      "Refined via SA CoParents BIFF Coach",
      `Refined: ${new Date().toISOString().replace("T", " ").substring(0, 16)} UTC`,
      `Case: ${courtKey || "Self-Guided Parent Journey"}`,
      "sacoparentsapp.online",
    ].join("\n");
    try {
      navigator.clipboard.writeText(`${biffOutput}${stamp}`);
      alert("Tone-safe message copied with audit stamp — safe to share with your attorney or mediator.");
    } catch {
      alert("Clipboard unavailable — please copy manually.");
    }

    // Kudos loop: only fires when the tone was actually risky. Otherwise
    // it would clutter the milestone list with false wins.
    if (riskLabel === "Escalation Flag") {
      const kudos = {
        id: Date.now(),
        type: "success",
        title: "Coach kept a hot message tone-safe",
        date: new Date().toISOString().substring(0, 10),
        note:
          "You reformulated an escalation-flagged draft into a BIFF message and copied it via the Tone-Safe stamp.",
        source: "biff_kudos",
      };
      const next = [kudos, ...milestones];
      setMilestones(next);
      writeJson(MILESTONE_KEY, next);
    }
  }, [biffOutput, courtKey, riskLabel, milestones]);

  const logCommunication = useCallback(() => {
    const raw = rawInput.trim();
    if (!raw || !biffOutput) return;
    const timestamp = new Date().toISOString().replace("T", " ").substring(0, 16);
    const entry = {
      id: Date.now(),
      timestamp,
      category: "BIFF Exchange",
      original: raw,
      biff: biffOutput,
    };
    const next = [entry, ...biffLogs];
    setBiffLogs(next);
    writeJson(BIFF_LOG_KEY, next);
    alert("Message archived to Communication History!");
  }, [rawInput, biffOutput, biffLogs]);

  // Alignment records
  const alignmentCounts = useMemo(() => {
    return {
      Medical: alignRecords.filter((r) => r.category === "Medical").length,
      Educational: alignRecords.filter((r) => r.category === "Educational").length,
      Psychological: alignRecords.filter((r) => r.category === "Psychological").length,
    };
  }, [alignRecords]);

  const filteredRecords = useMemo(() => {
    return folderFilter === "All"
      ? alignRecords
      : alignRecords.filter((r) => r.category === folderFilter);
  }, [folderFilter, alignRecords]);

  const saveAlignmentRecord = useCallback(
    (e) => {
      e.preventDefault();
      const entry = {
        id: Date.now(),
        category: alignCategory,
        title: alignTitle,
        provider: alignProvider,
        date: alignDate,
        summary: alignSummary,
      };
      const next = [entry, ...alignRecords];
      setAlignRecords(next);
      writeJson(ALIGN_RECORDS_KEY, next);
      setAlignmentOpen(false);
      setAlignCategory("Medical");
      setAlignTitle("");
      setAlignProvider("");
      setAlignDate("");
      setAlignSummary("");
    },
    [alignCategory, alignTitle, alignProvider, alignDate, alignSummary, alignRecords]
  );

  // Milestones
  const successCount = useMemo(
    () => milestones.filter((m) => m.type === "success").length,
    [milestones]
  );
  const frictionCount = useMemo(
    () => milestones.filter((m) => m.type === "friction").length,
    [milestones]
  );

  const addMilestoneLog = useCallback(() => {
    const title = window.prompt(
      "Enter Milestone Title (e.g. Smooth Holiday Transition):"
    );
    if (!title) return;
    const isSuccess = window.confirm(
      "Click OK for Successful Resolution, or Cancel for Friction Point."
    );
    const entry = {
      id: Date.now(),
      type: isSuccess ? "success" : "friction",
      title,
      date: new Date().toISOString().substring(0, 10),
      note: isSuccess
        ? "Logged as positive co-parenting milestone."
        : "Logged as friction point for mediation review.",
    };
    const next = [entry, ...milestones];
    setMilestones(next);
    writeJson(MILESTONE_KEY, next);
  }, [milestones]);

  // Reassessment
  const saveReassessment = useCallback(
    (e) => {
      e.preventDefault();
      const prev = readJson(REASSESSMENT_KEY, []);
      const snapshot = { ...healthIndex };
      const s1 = Number(snapshot.s1) || 0;
      const s2 = Number(snapshot.s2) || 0;
      const s3 = Number(snapshot.s3) || 0;
      const avg = Number(((s1 + s2 + s3) / 3).toFixed(1));
      const entry = {
        id: Date.now(),
        stage: reassStage,
        notes: reassNotes,
        date: new Date().toISOString(),
        // Snapshot the current Health Index so we can render a trend
        // sparkline across reassessments over time.
        snapshot,
        avg,
      };
      const next = [entry, ...prev];
      writeJson(REASSESSMENT_KEY, next);
      setReassessments(next);
      setReassessOpen(false);
      setReassNotes("");
      setReassStage("30-Day Progress Review");
      alert("Reassessment logged!");
    },
    [reassStage, reassNotes, healthIndex]
  );

  const handlePrint = useCallback(() => window.print(), []);

  const downloadPdfFromApi = useCallback(async (path, filename, body) => {
    try {
      const res = await api.post(path, body, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert("PDF could not be generated right now — please try again in a moment.");
    }
  }, []);

  // Mint a share link for the given artefact + payload, copy to clipboard.
  const [shareStatus, setShareStatus] = useState({}); // { foundation?: "loading"|"copied"|"error", ... }

  const createShareLink = useCallback(async (artefactType, payload) => {
    setShareStatus((prev) => ({ ...prev, [artefactType]: "loading" }));
    try {
      const { data } = await api.post("/portal/share", {
        artefact_type: artefactType,
        payload,
      });
      const url = data?.url;
      if (!url) throw new Error("no url");
      try {
        await navigator.clipboard.writeText(url);
        setShareStatus((prev) => ({ ...prev, [artefactType]: "copied" }));
        alert(
          `Share link copied to clipboard:\n\n${url}\n\nText or email this to your pediatrician, mediator, or attorney. It works for 30 days.`
        );
      } catch {
        setShareStatus((prev) => ({ ...prev, [artefactType]: "copied" }));
        window.prompt(
          "Copy this share link (Ctrl+C / Cmd+C):",
          url
        );
      }
      setTimeout(() => {
        setShareStatus((prev) => ({ ...prev, [artefactType]: undefined }));
      }, 4000);
    } catch {
      setShareStatus((prev) => ({ ...prev, [artefactType]: "error" }));
      alert("Couldn't create a share link — please try again in a moment.");
    }
  }, []);

  const downloadFoundationPdf = useCallback(() => {
    if (!foundationText.trim()) {
      alert("Please write your Foundation Statement before exporting the PDF.");
      return;
    }
    downloadPdfFromApi(
      "/portal/foundation-pdf",
      "sacoparents-foundation-statement.pdf",
      {
        foundation_text: foundationText,
        case_ref: courtKey || null,
        author_name: user?.name || null,
      }
    );
  }, [foundationText, courtKey, user, downloadPdfFromApi]);

  const downloadLegalPdf = useCallback(() => {
    downloadPdfFromApi(
      "/portal/legal-report-pdf",
      "sacoparents-legal-report.pdf",
      {
        health_index: healthIndex,
        foundation_text: foundationText || null,
        signatures: legalReport,
        case_ref: courtKey || null,
      }
    );
  }, [healthIndex, foundationText, legalReport, courtKey, downloadPdfFromApi]);

  const downloadWeeklyProgressPdf = useCallback(() => {
    downloadPdfFromApi(
      "/portal/weekly-progress-pdf",
      "sacoparents-weekly-progress.pdf",
      {
        health_index: healthIndex,
        biff_logs: biffLogs,
        milestones,
        reassessments,
        foundation_text: foundationText || null,
        case_ref: courtKey || null,
        author_name: user?.name || null,
      }
    );
  }, [
    healthIndex,
    biffLogs,
    milestones,
    reassessments,
    foundationText,
    courtKey,
    user,
    downloadPdfFromApi,
  ]);

  const showBackBtn = screen !== "gateway";

  return (
    <div
      className="bg-slate-50 text-slate-800 font-sans min-h-screen flex flex-col pb-20"
      data-testid="sacoparents-portal"
    >
      {/* Print-only styles */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          body { background: white !important; color: black !important; }
          .card-box { border: 1px solid #ccc !important; box-shadow: none !important; }
        }
        .print-only { display: none; }
        .bottom-nav-active { color: #5b21b6; font-weight: 700; }
      `}</style>

      {/* TOP APP HEADER */}
      <header
        className="bg-purple-950 text-white shadow-md sticky top-0 z-50 no-print"
        data-testid="portal-header"
      >
        <div className="max-w-md mx-auto px-4 py-3 flex justify-between items-center gap-2">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="bg-purple-800/50 p-2 rounded-xl backdrop-blur-md border border-purple-400/30 shrink-0">
              <i className="fa-solid fa-hands-holding-child text-purple-300 text-lg"></i>
            </div>
            <div className="min-w-0">
              <h1 className="text-base font-bold tracking-tight truncate">
                sacoparentsapp.online
              </h1>
              <p className="text-[10px] text-purple-200 truncate">
                SA CoParents Assessment & Alignment Portal
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            {showBackBtn && (
              <button
                data-testid="header-back-btn"
                onClick={openDoorGateway}
                className="bg-purple-900 hover:bg-purple-800 text-white px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 border border-purple-700 transition"
              >
                <i className="fa-solid fa-arrow-left"></i> Doors
              </button>
            )}
            <button
              onClick={handlePrint}
              data-testid="export-pdf-btn"
              className="bg-purple-700 hover:bg-purple-600 text-white px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 transition shadow"
            >
              <i className="fa-solid fa-file-pdf"></i> Export PDF
            </button>
          </div>
        </div>
      </header>

      {/* PRINT ONLY LEGAL SUMMARY HEADER */}
      <div className="print-only p-6 border-b-2 border-purple-900">
        <h1 className="text-2xl font-bold text-purple-950">
          sacoparentsapp.online - Official Legal Conflict Resolution & Alignment Report
        </h1>
        <p className="text-xs text-slate-600">
          Created by Matt Sossi, Founder of SA CoParents (San Antonio, Texas)
        </p>
        <p className="text-xs text-slate-600">
          Generated Date: {printDate} | Case Reference: {courtKey || "Self-Guided Parent Journey"}
        </p>
      </div>

      {/* MAIN CONTAINER */}
      <main className="max-w-md mx-auto px-4 py-4 flex-1 w-full space-y-4">
        {/* GATEWAY SCREEN */}
        {screen === "gateway" && (
          <div className="space-y-4" data-testid="screen-gateway">
            <div className="text-center py-2">
              <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider border border-purple-200">
                San Antonio, TX Methodology
              </span>
              <h2 className="text-xl font-bold text-slate-800 mt-2">
                Welcome to SA CoParents
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Select your entry path to access official assessments, foundation statements, and de-escalation tools.
              </p>
            </div>

            <div className="grid gap-4">
              {/* DOOR 1 */}
              <div
                onClick={enterParentJourney}
                data-testid="door-parent-journey"
                className="bg-white p-5 rounded-2xl shadow-sm border-2 border-purple-100 hover:border-purple-600 cursor-pointer transition flex flex-col justify-between space-y-3 group"
              >
                <div className="flex justify-between items-start">
                  <div className="p-3 bg-purple-50 text-purple-700 rounded-xl group-hover:bg-purple-800 group-hover:text-white transition">
                    <i className="fa-solid fa-heart-pulse text-2xl"></i>
                  </div>
                  <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2.5 py-0.5 rounded-full">
                    Door 1 · Self-Guided
                  </span>
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-base">Parent Journey</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Reflect independently, access existing co-parenting assessments, create a Foundation Statement PDF, and utilize BIFF tools.
                  </p>
                </div>
                <div className="flex items-center text-xs font-bold text-purple-700 group-hover:translate-x-1 transition">
                  <span>Enter Parent Path</span>{" "}
                  <i className="fa-solid fa-arrow-right ml-1"></i>
                </div>
              </div>

              {/* DOOR 2 */}
              <div
                onClick={enterCourtPath}
                data-testid="door-court-path"
                className="bg-white p-5 rounded-2xl shadow-sm border-2 border-slate-200 hover:border-purple-900 cursor-pointer transition flex flex-col justify-between space-y-3 group"
              >
                <div className="flex justify-between items-start">
                  <div className="p-3 bg-slate-100 text-slate-700 rounded-xl group-hover:bg-purple-950 group-hover:text-white transition">
                    <i className="fa-solid fa-gavel text-2xl"></i>
                  </div>
                  <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2.5 py-0.5 rounded-full">
                    Door 2 · Professional Key
                  </span>
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-base">Court Ordered Path</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Accept professional key from mediator or attorney at{" "}
                    <strong>sacoparentsalign.com</strong> for connected joint assessments.
                  </p>
                </div>
                <div className="flex items-center text-xs font-bold text-slate-700 group-hover:translate-x-1 transition">
                  <span>Enter Professional Key Door</span>{" "}
                  <i className="fa-solid fa-arrow-right ml-1"></i>
                </div>
              </div>
            </div>

            {/* Sync / Sign-in chip */}
            <div className="text-center pt-2" data-testid="sync-chip">
              {user ? (
                <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3 py-1.5 rounded-full text-[11px] font-semibold">
                  <i className="fa-solid fa-cloud-arrow-up"></i>
                  <span data-testid="sync-status">
                    {syncStatus === "syncing"
                      ? "Syncing across devices…"
                      : syncStatus === "offline"
                      ? "Offline — changes will sync when you're back"
                      : syncStatus === "error"
                      ? "Sync paused — your work is safe locally"
                      : `Synced as ${user.email || user.name || "your account"}`}
                  </span>
                </div>
              ) : (
                <Link
                  to="/login"
                  data-testid="sync-signin-link"
                  className="inline-flex items-center gap-2 bg-white border border-purple-200 text-purple-800 px-3 py-1.5 rounded-full text-[11px] font-semibold hover:bg-purple-50 transition"
                >
                  <i className="fa-solid fa-cloud"></i>
                  Sign in to sync across devices
                </Link>
              )}
            </div>
          </div>
        )}

        {/* COURT KEY SCREEN */}
        {screen === "court-key" && (
          <div className="space-y-4" data-testid="screen-court-key">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-purple-200 space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase">
                  sacoparentsalign.com Integration
                </span>
                <h2 className="text-lg font-bold text-slate-800 mt-1">
                  Enter Professional Access Key
                </h2>
                <p className="text-xs text-slate-500">
                  Provided by your court-appointed mediator, parenting coordinator, or family lawyer.
                </p>
              </div>

              <div className="space-y-3">
                <label className="block text-xs font-bold text-slate-700">
                  Professional Key Code
                </label>
                <input
                  type="text"
                  data-testid="court-key-input"
                  value={courtKeyInput}
                  onChange={(e) => {
                    setCourtKeyInput(e.target.value);
                    setCourtKeyError("");
                  }}
                  className="w-full p-3 border border-slate-300 rounded-xl text-sm font-mono tracking-wider focus:ring-2 focus:ring-purple-600 focus:outline-none"
                  placeholder="e.g. ALIGN-SA-2026"
                />
                {courtKeyError && (
                  <p
                    data-testid="court-key-error"
                    className="text-[11px] text-rose-600 font-semibold"
                  >
                    {courtKeyError}
                  </p>
                )}
                <p className="text-[10px] text-slate-400">
                  Demo Keys: Use{" "}
                  <button
                    type="button"
                    data-testid="demo-key-1"
                    onClick={() => setCourtKeyInput("ALIGN-SA-2026")}
                    className="text-purple-700 font-bold underline"
                  >
                    ALIGN-SA-2026
                  </button>{" "}
                  or{" "}
                  <button
                    type="button"
                    data-testid="demo-key-2"
                    onClick={() => setCourtKeyInput("COURT-8842")}
                    className="text-purple-700 font-bold underline"
                  >
                    COURT-8842
                  </button>
                </p>
              </div>

              <button
                onClick={verifyProfessionalKey}
                data-testid="verify-court-key-btn"
                disabled={courtKeyLoading}
                className="w-full bg-purple-950 hover:bg-purple-900 disabled:opacity-60 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl text-xs flex items-center justify-center gap-2 transition shadow"
              >
                <i className="fa-solid fa-key"></i>{" "}
                {courtKeyLoading ? "Verifying…" : "Verify & Sync Joint Case"}
              </button>
            </div>
          </div>
        )}

        {/* PARENT JOURNEY DASHBOARD */}
        {screen === "parent-journey" && (
          <div className="space-y-4" data-testid="screen-parent-journey">
            {/* Court Verified Banner */}
            {courtKey && (
              <div
                className="bg-purple-950 text-white p-3 rounded-2xl flex justify-between items-center text-xs border border-purple-800 shadow"
                data-testid="court-verified-banner"
              >
                <div>
                  <span className="text-[9px] bg-emerald-500 text-white font-bold px-2 py-0.5 rounded-full">
                    ACTIVE COURT KEY
                  </span>
                  <div className="font-bold mt-0.5" data-testid="verified-case-id">
                    Verified Case: {courtKey}
                  </div>
                  <div className="text-[10px] text-purple-200">
                    Mediator: {verifiedMediator || "Matt Sossi, Licensed Mediator (San Antonio, TX)"}
                  </div>
                </div>
                <i className="fa-solid fa-shield-halved text-purple-300 text-xl"></i>
              </div>
            )}

            {/* Hub Tabs */}
            <div className="grid grid-cols-2 gap-2 text-xs font-bold no-print">
              <button
                data-testid="hub-tab-alignment"
                onClick={() => setHubSection("alignment")}
                className={
                  hubSection === "alignment"
                    ? "p-3 bg-purple-900 text-white rounded-xl shadow-sm text-center border border-purple-800"
                    : "p-3 bg-white text-slate-700 rounded-xl shadow-sm border border-slate-200 text-center"
                }
              >
                <i className="fa-solid fa-scale-balanced block text-base mb-1"></i> I. Legal Report & Alignment
              </button>
              <button
                data-testid="hub-tab-biff"
                onClick={() => setHubSection("biff")}
                className={
                  hubSection === "biff"
                    ? "p-3 bg-purple-900 text-white rounded-xl shadow-sm text-center border border-purple-800"
                    : "p-3 bg-white text-slate-700 rounded-xl shadow-sm border border-slate-200 text-center"
                }
              >
                <i className="fa-solid fa-comments text-amber-500 block text-base mb-1"></i> II. BIFF & Success History
              </button>
            </div>

            {/* SECTION I: ALIGNMENT */}
            {hubSection === "alignment" && (
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
                          onClick={() => setReassessOpen(true)}
                          className="no-print bg-purple-800 text-white text-[10px] font-bold px-2 py-1 rounded"
                        >
                          Log Reassessment
                        </button>
                      </div>

                      {/* Trend sparkline (last 4 reassessments + current) */}
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
                              <td className="p-2">
                                24-Hr Advance Notice + Cooling Off
                              </td>
                            </tr>
                            <tr>
                              <td className="p-2 font-semibold text-slate-800">
                                Child Handoffs
                              </td>
                              <td className="p-2">
                                Neutral Public Location Default
                              </td>
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

                    {/* Actions */}
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
                        onClick={() =>
                          createShareLink("legal", {
                            health_index: healthIndex,
                            foundation_text: foundationText || null,
                            signatures: legalReport,
                            case_ref: courtKey || null,
                          })
                        }
                        title="Copy a 30-day share link"
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
                      onClick={() => setAlignmentOpen(true)}
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
                    Your one-page child-focused anchor statement to return to whenever emotions get hot.
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
                      onClick={() =>
                        createShareLink("foundation", {
                          foundation_text: foundationText,
                          case_ref: courtKey || null,
                          author_name: user?.name || null,
                        })
                      }
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
            )}

            {/* SECTION II: BIFF */}
            {hubSection === "biff" && (
              <div className="space-y-4" data-testid="hub-section-biff">
                {/* BIFF Builder */}
                <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
                  <div className="border-b border-slate-100 pb-2">
                    <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                      De-escalation Engine
                    </span>
                    <h3 className="font-bold text-slate-800 text-sm mt-1">
                      BIFF Communication Builder
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Brief, Informative, Friendly, and Firm messaging.
                    </p>
                  </div>

                  {/* Presets */}
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

                  {/* Input/Output */}
                  <div className="space-y-2">
                    <textarea
                      data-testid="raw-input"
                      value={rawInput}
                      onChange={(e) => handleRawInputChange(e.target.value)}
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
                            <span
                              key={i}
                              className="text-rose-600 font-medium mr-2"
                            >
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

                {/* Communication History */}
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

                {/* Milestones */}
                <div className="bg-white p-4 rounded-2xl shadow-sm border border-purple-200 space-y-3 card-box">
                  <div className="flex justify-between items-center">
                    <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
                      <i className="fa-solid fa-chart-line text-emerald-600"></i>{" "}
                      History of Successes & Failures
                    </h3>
                    <button
                      data-testid="add-milestone-btn"
                      onClick={addMilestoneLog}
                      className="no-print text-[10px] bg-slate-800 text-white px-2 py-1 rounded-lg"
                    >
                      + Log Milestone
                    </button>
                  </div>

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

                  <div className="space-y-2 text-xs pt-1" data-testid="milestone-history-list">
                    {milestones.length === 0 ? (
                      <p className="text-slate-400 text-center py-1">
                        No milestone events logged.
                      </p>
                    ) : (
                      milestones.map((m) => (
                        <div
                          key={m.id}
                          className="p-2 bg-slate-50 border border-slate-200 rounded-lg flex justify-between items-center text-xs"
                          data-testid={`milestone-${m.id}`}
                        >
                          <div>
                            <span className="font-bold text-slate-800">
                              {m.title}
                            </span>
                            <div className="text-[10px] text-slate-500">{m.note}</div>
                          </div>
                          <span
                            className={
                              m.type === "success"
                                ? "text-[9px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800"
                                : "text-[9px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800"
                            }
                          >
                            {m.type.toUpperCase()}
                          </span>
                        </div>
                      ))
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
                      onClick={() =>
                        createShareLink("weekly", {
                          health_index: healthIndex,
                          biff_logs: biffLogs,
                          milestones,
                          reassessments,
                          foundation_text: foundationText || null,
                          case_ref: courtKey || null,
                          author_name: user?.name || null,
                        })
                      }
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
              </div>
            )}
          </div>
        )}
      </main>

      {/* BOTTOM NAV */}
      <nav
        className="fixed bottom-0 left-0 right-0 bg-white border-t border-purple-200 py-2 px-6 flex justify-around items-center z-40 no-print max-w-md mx-auto shadow-lg"
        data-testid="bottom-nav"
      >
        <button
          data-testid="nav-doors"
          onClick={openDoorGateway}
          className="flex flex-col items-center space-y-0.5 text-slate-500 hover:text-purple-800"
        >
          <i className="fa-solid fa-door-open text-base"></i>
          <span className="text-[9px] font-semibold">Doors</span>
        </button>
        <button
          data-testid="nav-report"
          onClick={() => {
            setHubSection("alignment");
            enterParentJourney();
          }}
          className={
            screen === "parent-journey" && hubSection === "alignment"
              ? "flex flex-col items-center space-y-0.5 bottom-nav-active"
              : "flex flex-col items-center space-y-0.5 text-slate-500 hover:text-purple-800"
          }
        >
          <i className="fa-solid fa-scale-balanced text-base"></i>
          <span className="text-[9px] font-semibold">Report</span>
        </button>
        <button
          data-testid="nav-biff"
          onClick={() => {
            setHubSection("biff");
            enterParentJourney();
          }}
          className={
            screen === "parent-journey" && hubSection === "biff"
              ? "flex flex-col items-center space-y-0.5 bottom-nav-active"
              : "flex flex-col items-center space-y-0.5 text-slate-500 hover:text-purple-800"
          }
        >
          <i className="fa-solid fa-comments text-base"></i>
          <span className="text-[9px] font-semibold">BIFF Tool</span>
        </button>
        <button
          data-testid="nav-print"
          onClick={handlePrint}
          className="flex flex-col items-center space-y-0.5 text-slate-500 hover:text-purple-800"
        >
          <i className="fa-solid fa-file-pdf text-base"></i>
          <span className="text-[9px] font-semibold">PDF Export</span>
        </button>
      </nav>

      {/* REASSESSMENT MODAL */}
      {reassessOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 no-print"
          data-testid="modal-reassessment"
        >
          <div className="bg-white w-full max-w-sm rounded-2xl shadow-xl space-y-3 p-5">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-800 text-sm">
                Log Relationship Reassessment
              </h3>
              <button
                data-testid="close-reassessment-modal"
                onClick={() => setReassessOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>

            <form onSubmit={saveReassessment} className="space-y-2.5 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Reassessment Milestone Stage
                </label>
                <select
                  data-testid="reass-stage"
                  value={reassStage}
                  onChange={(e) => setReassStage(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                >
                  <option value="30-Day Progress Review">30-Day Progress Review</option>
                  <option value="Post-Mediation Check-in">Post-Mediation Check-in</option>
                  <option value="Quarterly Alignment Review">Quarterly Alignment Review</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Reassessment Notes & Observations
                </label>
                <textarea
                  data-testid="reass-notes"
                  rows={3}
                  required
                  value={reassNotes}
                  onChange={(e) => setReassNotes(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                  placeholder="Note improvements in communication or handoff consistency..."
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setReassessOpen(false)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg font-semibold text-slate-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="submit-reassessment-btn"
                  className="px-3 py-1.5 bg-purple-800 text-white rounded-lg font-semibold"
                >
                  Log Entry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ALIGNMENT MODAL */}
      {alignmentOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 no-print"
          data-testid="modal-alignment"
        >
          <div className="bg-white w-full max-w-sm rounded-2xl shadow-xl space-y-3 p-5">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-800 text-sm">
                Add Alignment Assessment
              </h3>
              <button
                data-testid="close-alignment-modal"
                onClick={() => setAlignmentOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>

            <form onSubmit={saveAlignmentRecord} className="space-y-2.5 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Sub-Folder Category
                </label>
                <select
                  data-testid="align-category"
                  value={alignCategory}
                  onChange={(e) => setAlignCategory(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                >
                  <option value="Medical">Child's Medical</option>
                  <option value="Educational">Educational Assessment</option>
                  <option value="Psychological">Psychological Assessment</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Assessment Document Title
                </label>
                <input
                  type="text"
                  data-testid="align-title"
                  required
                  value={alignTitle}
                  onChange={(e) => setAlignTitle(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                  placeholder="e.g. Annual Pediatric Health Plan"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Specialist / Provider Name
                </label>
                <input
                  type="text"
                  data-testid="align-provider"
                  required
                  value={alignProvider}
                  onChange={(e) => setAlignProvider(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                  placeholder="Dr. Sarah Jenkins"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Date Conducted
                </label>
                <input
                  type="date"
                  data-testid="align-date"
                  required
                  value={alignDate}
                  onChange={(e) => setAlignDate(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Alignment Summary Notes
                </label>
                <textarea
                  data-testid="align-summary"
                  rows={2}
                  required
                  value={alignSummary}
                  onChange={(e) => setAlignSummary(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                  placeholder="Enter key recommendations..."
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAlignmentOpen(false)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg font-semibold text-slate-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="submit-alignment-btn"
                  className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg font-semibold"
                >
                  Save Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
