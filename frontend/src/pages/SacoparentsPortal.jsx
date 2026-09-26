import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

import {
  ALIGN_RECORDS_KEY,
  BIFF_LOG_KEY,
  COURT_KEY_KEY,
  DEFAULT_ALIGNMENTS,
  DEFAULT_BIFF_LOGS,
  DEFAULT_FOUNDATION,
  DEFAULT_HEALTH_INDEX,
  DEFAULT_LEGAL_REPORT,
  DEFAULT_MILESTONES,
  FOUNDATION_KEY,
  HEALTH_INDEX_KEY,
  LEGAL_REPORT_KEY,
  MILESTONE_KEY,
  PRESETS,
  REASSESSMENT_KEY,
  SAFETY_ACK_KEY,
  SAFETY_PLAN_KEY,
  SYNC_PENDING_KEY,
  computeHealthLabel,
  computeKudosStreak,
  readJson,
  readString,
  writeJson,
  writeString,
} from "./portal/portalStorage";
import { AlignmentHub } from "./portal/AlignmentHub";
import { BiffTab } from "./portal/BiffTab";
import { CourtKeyScreen } from "./portal/CourtKeyScreen";
import { DoorsGateway } from "./portal/DoorsGateway";
import {
  SafetyRetakeChip,
  SafetyScreen,
  SafetySoftBanner,
} from "./portal/SafetyScreen";
import { SafetyCrisisStrip } from "./portal/SafetyCrisisStrip";
import { ShareLegalModal } from "./portal/ShareLegalModal";

/**
 * sacoparentsapp.online — Child-Centered Co-Parenting Portal (SPA).
 *
 * This container owns state + effects; every visual block is rendered
 * by a per-tab component from ./portal/*.
 *
 * Clinical guardrails preserved (never removed):
 *   - Persistent SafetyCrisisStrip on every screen (911, 988, DV
 *     hotline, text-line).
 *   - First-visit SafetyScreen gate before EITHER Door.
 *   - SafetyRetakeChip on Parent Journey header — always re-openable.
 *   - SafetySoftBanner on BIFF + Alignment tabs whenever the last
 *     Quick Safety Check returned a risk flag.
 */
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

  // Safety Screen state (first-visit gate + persistent flag)
  const [safetyAck, setSafetyAck] = useState(null); // { date, cleared, flagged? } | null
  const [safetyPlan, setSafetyPlan] = useState(null); // {safe_place, trusted_contact, ...}
  const [safetyOpen, setSafetyOpen] = useState(false);
  const pendingDoorRef = useRef(null); // 'parent' | 'court' — where to go after safety

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
  const [shareLegalOpen, setShareLegalOpen] = useState(false);
  const [shareLegalLastUrl, setShareLegalLastUrl] = useState("");

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
  const [syncStatus, setSyncStatus] = useState("idle");
  const syncDebounceRef = useRef(null);
  const hasHydratedFromServerRef = useRef(false);

  // ----------------------------------------------------------------
  // Hydrate from localStorage on mount
  // ----------------------------------------------------------------
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

    const seededSafety = readJson(SAFETY_ACK_KEY, null);
    setSafetyAck(seededSafety);

    const seededSafetyPlan = readJson(SAFETY_PLAN_KEY, null);
    setSafetyPlan(seededSafetyPlan);
  }, []);

  // ----------------------------------------------------------------
  // Cross-device server hydrate
  // ----------------------------------------------------------------
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
        if (s.safety_ack && typeof s.safety_ack === "object") {
          setSafetyAck(s.safety_ack);
          writeJson(SAFETY_ACK_KEY, s.safety_ack);
        }
        if (s.safety_plan && typeof s.safety_plan === "object") {
          setSafetyPlan(s.safety_plan);
          writeJson(SAFETY_PLAN_KEY, s.safety_plan);
        }
        hasHydratedFromServerRef.current = true;
      } catch {
        hasHydratedFromServerRef.current = true;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  // ----------------------------------------------------------------
  // Debounced server push (offline-tolerant)
  // ----------------------------------------------------------------
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
          safety_ack: safetyAck,
          safety_plan: safetyPlan,
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
    safetyAck,
    safetyPlan,
  ]);

  // Flush queued PUT when we come back online
  const [onlineTick, setOnlineTick] = useState(0);
  useEffect(() => {
    if (!user) return;
    const pending = readString(SYNC_PENDING_KEY, "");
    if (
      pending === "1" &&
      typeof navigator !== "undefined" &&
      navigator.onLine !== false
    ) {
      setOnlineTick((t) => t + 1);
    }
    const onOnline = () => setOnlineTick((t) => t + 1);
    if (typeof window !== "undefined") {
      window.addEventListener("online", onOnline);
      return () => window.removeEventListener("online", onOnline);
    }
    return undefined;
  }, [user]);
  useEffect(() => {
    if (onlineTick === 0) return;
    setHealthIndex((prev) => ({ ...prev }));
  }, [onlineTick]);

  // ----------------------------------------------------------------
  // Derived state
  // ----------------------------------------------------------------
  const healthAvg = useMemo(() => {
    const s1 = Number(healthIndex.s1) || 0;
    const s2 = Number(healthIndex.s2) || 0;
    const s3 = Number(healthIndex.s3) || 0;
    return ((s1 + s2 + s3) / 3).toFixed(1);
  }, [healthIndex]);

  const healthLabel = useMemo(
    () => computeHealthLabel(Number(healthAvg)),
    [healthAvg]
  );

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

  const successCount = useMemo(
    () => milestones.filter((m) => m.type === "success").length,
    [milestones]
  );
  const frictionCount = useMemo(
    () => milestones.filter((m) => m.type === "friction").length,
    [milestones]
  );

  const kudosStreak = useMemo(() => computeKudosStreak(milestones), [milestones]);

  const safetyFlagged = !!(safetyAck && safetyAck.flagged);

  // ----------------------------------------------------------------
  // Handlers
  // ----------------------------------------------------------------
  const setHealthScore = useCallback((key, value) => {
    setHealthIndex((prev) => {
      const next = { ...prev, [key]: Number(value) };
      writeJson(HEALTH_INDEX_KEY, next);
      return next;
    });
  }, []);

  // Navigation with safety-gate: first-time visitors must complete
  // the quick safety check before entering EITHER door.
  const openDoorGateway = useCallback(() => setScreen("gateway"), []);

  const requestDoorEntry = useCallback(
    (door) => {
      if (!safetyAck) {
        pendingDoorRef.current = door;
        setSafetyOpen(true);
        return;
      }
      if (door === "parent") setScreen("parent-journey");
      else setScreen("court-key");
    },
    [safetyAck]
  );

  const enterParentJourney = useCallback(
    () => requestDoorEntry("parent"),
    [requestDoorEntry]
  );
  const enterCourtPath = useCallback(
    () => requestDoorEntry("court"),
    [requestDoorEntry]
  );

  const onSafetyCleared = useCallback(() => {
    const ack = {
      date: new Date().toISOString(),
      cleared: true,
      flagged: false,
    };
    writeJson(SAFETY_ACK_KEY, ack);
    setSafetyAck(ack);
    setSafetyOpen(false);
    const pending = pendingDoorRef.current;
    pendingDoorRef.current = null;
    if (pending === "parent") setScreen("parent-journey");
    else if (pending === "court") setScreen("court-key");
  }, []);

  const onSafetyContinueFlagged = useCallback(() => {
    const ack = {
      date: new Date().toISOString(),
      cleared: false,
      flagged: true,
    };
    writeJson(SAFETY_ACK_KEY, ack);
    setSafetyAck(ack);
    setSafetyOpen(false);
    const pending = pendingDoorRef.current;
    pendingDoorRef.current = null;
    if (pending === "parent") setScreen("parent-journey");
    else if (pending === "court") setScreen("court-key");
  }, []);

  const onOpenSafetyRetake = useCallback(() => {
    pendingDoorRef.current = null;
    setSafetyOpen(true);
  }, []);

  const onSaveSafetyPlan = useCallback(
    (plan) => {
      if (plan == null) {
        // Delete: wipe local storage AND state; fire a fire-and-
        // forget PUT NOW so the server-side copy is gone as soon as
        // the network round-trip completes — critical for a parent
        // who taps delete and then closes the tab. Uses the new
        // PATCH-style semantics on /portal/state so we only send
        // the field we're clearing, never risking clobbering
        // alignments / milestones / biff logs.
        try {
          localStorage.removeItem(SAFETY_PLAN_KEY);
        } catch {
          /* ignore quota */
        }
        setSafetyPlan(null);
        if (user) {
          api
            .put("/portal/state", { safety_plan: null })
            .catch(() => {
              // The debounced PUT triggered by the state change will
              // retry on the next tick / online event.
            });
        }
        return;
      }
      writeJson(SAFETY_PLAN_KEY, plan);
      setSafetyPlan(plan);
    },
    [user]
  );

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
          expired:
            "That key has expired — please request a new one from your mediator.",
          revoked:
            "That key has been revoked. Contact your mediator for a replacement.",
          unknown_key:
            "We don't recognise that key. Double-check the code or ask your mediator.",
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

  const handleCourtKeyInputChange = useCallback((val) => {
    setCourtKeyInput(val);
    setCourtKeyError("");
  }, []);

  const saveFoundationText = useCallback(() => {
    writeString(FOUNDATION_KEY, foundationText);
    alert("Foundation Statement PDF draft saved!");
  }, [foundationText]);

  const saveLegalReport = useCallback(() => {
    writeJson(LEGAL_REPORT_KEY, legalReport);
    alert("Official Legal Conflict Resolution Report draft saved!");
  }, [legalReport]);

  // BIFF local + AI refinement
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

  const runAiRefine = useCallback(
    (val) => {
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
      const flagged = !!(safetyAck && safetyAck.flagged);
      biffDebounceRef.current = setTimeout(async () => {
        setBiffLoading(true);
        setBiffError("");
        const controller = new AbortController();
        biffAbortRef.current = controller;
        try {
          const { data } = await api.post(
            "/portal/biff-refine",
            { raw: trimmed, safety_flagged: flagged },
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
    },
    [safetyAck]
  );

  const handleRawInputChange = useCallback(
    (val) => {
      setRawInput(val);
      runLocalAnalysis(val);
      runAiRefine(val);
    },
    [runLocalAnalysis, runAiRefine]
  );

  const applyPreset = useCallback(
    (key) => {
      const p = PRESETS[key];
      if (!p) return;
      setRawInput(p.raw);
      setFlagList(p.flags);
      setRiskLabel(p.flags.length > 0 ? "Escalation Flag" : "Low Risk");
      setBiffOutput(p.biff);
      runAiRefine(p.raw);
    },
    [runAiRefine]
  );

  const copyBiffOutput = useCallback(() => {
    if (!biffOutput) return;
    try {
      navigator.clipboard.writeText(biffOutput);
      alert("BIFF message copied!");
    } catch {
      alert("Clipboard unavailable — please copy manually.");
    }
  }, [biffOutput]);

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
      alert(
        "Tone-safe message copied with audit stamp — safe to share with your attorney or mediator."
      );
    } catch {
      alert("Clipboard unavailable — please copy manually.");
    }

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
    [
      alignCategory,
      alignTitle,
      alignProvider,
      alignDate,
      alignSummary,
      alignRecords,
    ]
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
      const url = window.URL.createObjectURL(
        new Blob([res.data], { type: "application/pdf" })
      );
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

  // Share links
  const [shareStatus, setShareStatus] = useState({});

  const createShareLink = useCallback(
    async (artefactType, payload, opts = {}) => {
      setShareStatus((prev) => ({ ...prev, [artefactType]: "loading" }));
      try {
        const requestBody = {
          artefact_type: artefactType,
          payload,
        };
        if (opts.passphrase) requestBody.passphrase = opts.passphrase;
        if (opts.ttl_days) requestBody.ttl_days = opts.ttl_days;

        const { data } = await api.post("/portal/share", requestBody);
        const url = data?.url;
        if (!url) throw new Error("no url");
        try {
          await navigator.clipboard.writeText(url);
          setShareStatus((prev) => ({ ...prev, [artefactType]: "copied" }));
          if (artefactType === "legal") {
            // ShareLegalModal renders the result; skip the alert.
            setShareLegalLastUrl(url);
          } else {
            alert(
              `Share link copied to clipboard:\n\n${url}\n\nText or email this to your pediatrician, mediator, or attorney. It works for ${opts.ttl_days || 30} days.`
            );
          }
        } catch {
          setShareStatus((prev) => ({ ...prev, [artefactType]: "copied" }));
          if (artefactType === "legal") {
            setShareLegalLastUrl(url);
          } else {
            window.prompt("Copy this share link (Ctrl+C / Cmd+C):", url);
          }
        }
        setTimeout(() => {
          setShareStatus((prev) => ({ ...prev, [artefactType]: undefined }));
        }, 4000);
      } catch (exc) {
        // Log for prod debugging (P2 follow-up from iter70 review)
        // eslint-disable-next-line no-console
        console.warn("createShareLink failed", exc);
        setShareStatus((prev) => ({ ...prev, [artefactType]: "error" }));
        alert("Couldn't create a share link — please try again in a moment.");
      }
    },
    []
  );

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

  const onShareFoundation = useCallback(() => {
    createShareLink("foundation", {
      foundation_text: foundationText,
      case_ref: courtKey || null,
      author_name: user?.name || null,
    });
  }, [createShareLink, foundationText, courtKey, user]);

  const onShareWeekly = useCallback(() => {
    createShareLink("weekly", {
      health_index: healthIndex,
      biff_logs: biffLogs,
      milestones,
      reassessments,
      foundation_text: foundationText || null,
      case_ref: courtKey || null,
      author_name: user?.name || null,
    });
  }, [
    createShareLink,
    healthIndex,
    biffLogs,
    milestones,
    reassessments,
    foundationText,
    courtKey,
    user,
  ]);

  const onOpenShareLegal = useCallback(() => {
    setShareLegalLastUrl("");
    setShareLegalOpen(true);
  }, []);

  const onMintShareLegal = useCallback(
    (opts) => {
      createShareLink(
        "legal",
        {
          health_index: healthIndex,
          foundation_text: foundationText || null,
          signatures: legalReport,
          case_ref: courtKey || null,
        },
        opts
      );
    },
    [createShareLink, healthIndex, foundationText, legalReport, courtKey]
  );

  const showBackBtn = screen !== "gateway";

  return (
    <div
      className="bg-slate-50 text-slate-800 font-sans min-h-screen flex flex-col pb-28"
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

      {/* PRINT-ONLY LEGAL HEADER */}
      <div className="print-only p-6 border-b-2 border-purple-900">
        <h1 className="text-2xl font-bold text-purple-950">
          sacoparentsapp.online - Official Legal Conflict Resolution & Alignment Report
        </h1>
        <p className="text-xs text-slate-600">
          Created by Matt Sossi, Founder of SA CoParents (San Antonio, Texas)
        </p>
        <p className="text-xs text-slate-600">
          Generated Date: {printDate} | Case Reference:{" "}
          {courtKey || "Self-Guided Parent Journey"}
        </p>
      </div>

      {/* MAIN CONTAINER */}
      <main className="max-w-md mx-auto px-4 py-4 flex-1 w-full space-y-4">
        {screen === "gateway" && (
          <DoorsGateway
            onEnterParent={enterParentJourney}
            onEnterCourt={enterCourtPath}
            user={user}
            syncStatus={syncStatus}
            kudosStreak={kudosStreak}
          />
        )}

        {screen === "court-key" && (
          <CourtKeyScreen
            courtKeyInput={courtKeyInput}
            onChange={handleCourtKeyInputChange}
            onVerify={verifyProfessionalKey}
            courtKeyError={courtKeyError}
            courtKeyLoading={courtKeyLoading}
          />
        )}

        {screen === "parent-journey" && (
          <div className="space-y-4" data-testid="screen-parent-journey">
            {/* Court verified banner */}
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
                    Mediator:{" "}
                    {verifiedMediator ||
                      "Matt Sossi, Licensed Mediator (San Antonio, TX)"}
                  </div>
                </div>
                <i className="fa-solid fa-shield-halved text-purple-300 text-xl"></i>
              </div>
            )}

            {/* Safety re-take chip (persistent) */}
            <div className="flex justify-center">
              <SafetyRetakeChip
                onOpen={onOpenSafetyRetake}
                flagged={safetyFlagged}
              />
            </div>

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
                <i className="fa-solid fa-scale-balanced block text-base mb-1"></i>{" "}
                I. Legal Report & Alignment
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
                <i className="fa-solid fa-comments text-amber-500 block text-base mb-1"></i>{" "}
                II. BIFF & Success History
              </button>
            </div>

            {hubSection === "alignment" && (
              <>
                {safetyFlagged && <SafetySoftBanner context="alignment" />}
                <AlignmentHub
                  healthIndex={healthIndex}
                  setHealthScore={setHealthScore}
                  healthAvg={healthAvg}
                  healthLabel={healthLabel}
                  trendSeries={trendSeries}
                  onLogReassessment={() => setReassessOpen(true)}
                  legalReport={legalReport}
                  setLegalReport={setLegalReport}
                  saveLegalReport={saveLegalReport}
                  downloadLegalPdf={downloadLegalPdf}
                  onShareLegal={onOpenShareLegal}
                  shareStatus={shareStatus}
                  alignmentCounts={alignmentCounts}
                  folderFilter={folderFilter}
                  setFolderFilter={setFolderFilter}
                  filteredRecords={filteredRecords}
                  onAddAlignment={() => setAlignmentOpen(true)}
                  foundationText={foundationText}
                  setFoundationText={setFoundationText}
                  saveFoundationText={saveFoundationText}
                  downloadFoundationPdf={downloadFoundationPdf}
                  onShareFoundation={onShareFoundation}
                />
              </>
            )}

            {hubSection === "biff" && (
              <>
                {safetyFlagged && <SafetySoftBanner context="biff" />}
                <BiffTab
                  rawInput={rawInput}
                  onRawInputChange={handleRawInputChange}
                  applyPreset={applyPreset}
                  riskLabel={riskLabel}
                  flagList={flagList}
                  biffOutput={biffOutput}
                  biffLoading={biffLoading}
                  biffError={biffError}
                  copyBiffOutput={copyBiffOutput}
                  copyToneSafe={copyToneSafe}
                  logCommunication={logCommunication}
                  biffLogs={biffLogs}
                  milestones={milestones}
                  successCount={successCount}
                  frictionCount={frictionCount}
                  addMilestoneLog={addMilestoneLog}
                  downloadWeeklyProgressPdf={downloadWeeklyProgressPdf}
                  onShareWeekly={onShareWeekly}
                  shareStatus={shareStatus}
                  safetyFlagged={safetyFlagged}
                />
              </>
            )}
          </div>
        )}
      </main>

      {/* Safety crisis strip — pinned above bottom nav */}
      <SafetyCrisisStrip />

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

      {/* Safety Screen modal */}
      <SafetyScreen
        open={safetyOpen}
        onClose={() => setSafetyOpen(false)}
        onCleared={onSafetyCleared}
        onContinueFlagged={onSafetyContinueFlagged}
        safetyPlan={safetyPlan}
        onSaveSafetyPlan={onSaveSafetyPlan}
      />

      {/* Share Legal modal (passphrase + TTL) */}
      <ShareLegalModal
        open={shareLegalOpen}
        onClose={() => {
          setShareLegalOpen(false);
          setShareLegalLastUrl("");
        }}
        onMint={onMintShareLegal}
        loading={shareStatus.legal === "loading"}
        lastUrl={shareLegalLastUrl}
      />

      {/* Reassessment modal */}
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
                  <option value="30-Day Progress Review">
                    30-Day Progress Review
                  </option>
                  <option value="Post-Mediation Check-in">
                    Post-Mediation Check-in
                  </option>
                  <option value="Quarterly Alignment Review">
                    Quarterly Alignment Review
                  </option>
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

      {/* Alignment modal */}
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
