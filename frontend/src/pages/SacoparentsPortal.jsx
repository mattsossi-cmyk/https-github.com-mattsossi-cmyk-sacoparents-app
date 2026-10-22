import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import JourneyFlow from "./JourneyFlow";

import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { PathPicker } from "../components/journeyPath/PathPicker";
import { NEW_HOME_ON } from "../lib/previewGate";

import {
  ALIGN_RECORDS_KEY,
  BIFF_LOG_KEY,
  COURT_KEY_KEY,
  DEFAULT_FOUNDATION,
  DEFAULT_HEALTH_INDEX,
  DEFAULT_LEGAL_REPORT,
  FOUNDATION_KEY,
  GUIDED_DRAFT_KEY_PREFIX,
  HEALTH_INDEX_KEY,
  LEGAL_REPORT_KEY,
  MILESTONE_KEY,
  PRESETS,
  REASSESSMENT_KEY,
  RECORDS_ENABLED,
  SNAPSHOT_HISTORY_KEY,
  SNAPSHOT_HISTORY_MAX,
  withoutSamples,
  PATH_PICKED_KEY,
  FIRST_ENGAGEMENT_KEY,
  FOLLOWUP_DISMISSED_KEY,
  FOLLOWUP_MIN_HOURS,
  FOLLOWUP_SNOOZE_DAYS,
  SYNC_PENDING_KEY,
  computeHealthLabel,
  computeKudosStreak,
  readJson,
  readString,
  writeJson,
  writeString,
} from "./portal/portalStorage";
import { GuidedJourneyModal } from "./portal/GuidedJourneyModal";
import { JourneyShell, quickExitAction } from "./portal/JourneyShell";
import { CommunicationBuilderView } from "./portal/CommunicationBuilderView";
import {
  BiffCoachDrawer,
  FoundationDrawer,
  RecordsDrawer,
} from "./portal/JourneyDrawers";
import {
  IntroChatBot,
  hasIntroBeenSeen,
} from "./portal/IntroChatBot";
import { GuideFollowupModal } from "./portal/GuideFollowupModal";
import { SafetyCrisisStrip } from "./portal/SafetyCrisisStrip";
import { ProfessionalAccessCard } from "../components/privacy/ProfessionalAccessCard";
import { useOwnFooterLink } from "../lib/footerLink";
import { ShareLegalModal } from "./portal/ShareLegalModal";

const GREY_ROCK_KEY = "sacoparents_grey_rock";

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
  useOwnFooterLink();
  const { user } = useAuth();

  // iter248 — the parent-journey screen (and its hub-tabs toggle)
  // has been deleted. The parent-facing surface is now exclusively
  // the five-step JourneyShell + three modal drawers (BIFF,
  // Records, Foundation). The Court path is a full page inside the journey.
  // See NORTH_STAR.md.
  const [screen, setScreen] = useState("journey");

  // Modal drawer state (iter248).
  const [biffDrawerOpen, setBiffDrawerOpen] = useState(false);
  const [commBuilderOpen, setCommBuilderOpen] = useState(false);
  const [commBuilderFocus, setCommBuilderFocus] = useState(null);
  const [courtRequest, setCourtRequest] = useState(0);
  const [recordsDrawerOpen, setRecordsDrawerOpen] = useState(false);
  const [foundationDrawerOpen, setFoundationDrawerOpen] = useState(false);

  // Persistent data
  const [alignRecords, setAlignRecords] = useState([]);
  const [biffLogs, setBiffLogs] = useState([]);
  const [milestones, setMilestones] = useState([]);
  const [reassessments, setReassessments] = useState([]);
  const [foundationText, setFoundationText] = useState(DEFAULT_FOUNDATION);
  // Snapshot Library (iter227) — committed Guided Journey runs, newest
  // first. Capped at SNAPSHOT_HISTORY_MAX both here and by the server
  // sanitizer so a bad client can't push runaway data.
  const [snapshotHistory, setSnapshotHistory] = useState([]);
  const [legalReport, setLegalReport] = useState(DEFAULT_LEGAL_REPORT);
  const [healthIndex, setHealthIndex] = useState(DEFAULT_HEALTH_INDEX);
  const [courtKey, setCourtKey] = useState("");

  // Grey-rock tone: the parent's own on/off choice. (The old in-app safety check is off.)
  const [greyRock, setGreyRock] = useState(false);
  const navigate = useNavigate();
  // /journey shows the Journey Flow page inside the portal (same header, crisis strip and bottom bar).
  const onFlow = useLocation().pathname === "/journey";

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
  const [shareCompleteOpen, setShareCompleteOpen] = useState(false);
  const [shareCompleteLastUrl, setShareCompleteLastUrl] = useState("");
  // Guided-journey chat wizard state (iter220). One modal, six topics.
  const [guidedTopic, setGuidedTopic] = useState(null);
  // Guided-drafts revision counter (iter222). Bumped whenever the
  // modal persists a draft to localStorage, so the debounced PUT
  // effect re-fires and pushes the fresh drafts up to portal_state
  // for cross-device resume.
  const [guidedDraftsRev, setGuidedDraftsRev] = useState(0);
  // iter228 — intro chatbot ("SA CoParents Guide") shown on first
  // visit and re-invokable from a Gateway pill.
  const [introOpen, setIntroOpen] = useState(false);
  // iter265 — Partner Pair Celebration. The dashboard polls
  // /api/invites/coparent/pair-progress on mount so the
  // JourneyShell can fire a shared confetti + toast when the
  // linked co-parent has finished their three primary reflection
  // modules. iter266 — polling is periodic so the celebration can
  // fire while the parent is still in the app. iter267 — the
  // interval is jittered by ±10 s so a thousand simultaneous
  // parents don't all hit the endpoint on the same tick.
  const [pairProgress, setPairProgress] = useState(null);
  useEffect(() => {
    let cancelled = false;
    let timerId = null;

    const schedule = () => {
      if (cancelled) return;
      // 60 s ± 10 s jitter.
      const next = 60000 + Math.floor(Math.random() * 20001) - 10000;
      timerId = setTimeout(async () => {
        if (cancelled) return;
        try {
          if (
            typeof document !== "undefined" &&
            document.visibilityState &&
            document.visibilityState !== "visible"
          ) {
            // Still schedule the next tick, just skip this fetch.
            schedule();
            return;
          }
        } catch {
          /* ignore */
        }
        const stop = await fetchOnce();
        if (!stop) schedule();
      }, next);
    };

    const fetchOnce = async () => {
      if (cancelled) return true;
      try {
        const resp = await api.get("/invites/coparent/pair-progress");
        if (cancelled) return true;
        const data = resp.data || null;
        setPairProgress(data);
        // Stop polling once the pair milestone is reached.
        if (data && data.coparent_all_three_done) {
          return true;
        }
      } catch {
        // Non-fatal: parent may not have a linked co-parent, or
        // may not be signed in on this device.
      }
      return false;
    };

    // Fire once immediately, then start the jittered schedule.
    fetchOnce().then((stop) => {
      if (!stop) schedule();
    });

    // Also refetch when the tab becomes visible again.
    const onVisibility = () => {
      try {
        if (document.visibilityState === "visible") fetchOnce();
      } catch {
        /* ignore */
      }
    };
    try {
      document.addEventListener("visibilitychange", onVisibility);
    } catch {
      /* SSR / no document */
    }

    return () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
      try {
        document.removeEventListener("visibilitychange", onVisibility);
      } catch {
        /* ignore */
      }
    };
  }, []);
  // iter231 — follow-up "how's it going?" modal shown to a parent
  // who picked a path but never opened their first tile.
  const [followupState, setFollowupState] = useState(null);
  // iter232/iter233 — the SA CoParents Assessment Guide is now
  // rendered inline on the Alignment & Tools page (AlignmentHub);
  // the standalone modal export <AssessmentGuideChat/> is still
  // available for import if a future flow (intro/follow-up nudge)
  // needs to open it as a popup.

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

  // BIFF live-refine state. biffStatus: idle | loading | ai (AI-reviewed wording) | unavailable.
  const [biffLoading, setBiffLoading] = useState(false);
  const [biffError, setBiffError] = useState("");
  const [biffStatus, setBiffStatus] = useState("idle");
  const biffAbortRef = useRef(null);
  const biffDebounceRef = useRef(null);

  const [verifiedMediator, setVerifiedMediator] = useState("");

  // Sync state
  const [syncStatus, setSyncStatus] = useState("idle");
  const syncDebounceRef = useRef(null);
  const hasHydratedFromServerRef = useRef(false);
  const [portalHydrated, setPortalHydrated] = useState(false);
  const [journeyView, setJourneyView] = useState(null);

  // ----------------------------------------------------------------
  // Hydrate from localStorage on mount
  // ----------------------------------------------------------------
  useEffect(() => {
    if (initialisedRef.current) return;
    initialisedRef.current = true;

    // Child record folders are off: clear any copy saved in this browser.
    try {
      window.localStorage.removeItem(ALIGN_RECORDS_KEY);
      ["medical", "educational", "psychological"].forEach((t) =>
        window.localStorage.removeItem(`${GUIDED_DRAFT_KEY_PREFIX}${t}`)
      );
    } catch {
      /* storage unavailable */
    }
    setAlignRecords([]);

    // History starts empty; built-in sample entries saved by older builds are removed.
    const localMilestones = withoutSamples("milestones", readJson(MILESTONE_KEY, []));
    writeJson(MILESTONE_KEY, localMilestones);
    setMilestones(localMilestones);

    const seededFoundation = readString(FOUNDATION_KEY, null);
    if (seededFoundation == null) writeString(FOUNDATION_KEY, DEFAULT_FOUNDATION);
    setFoundationText(seededFoundation ?? DEFAULT_FOUNDATION);

    const seededLegal = readJson(LEGAL_REPORT_KEY, null);
    setLegalReport({ ...DEFAULT_LEGAL_REPORT, ...(seededLegal || {}) });

    const seededHealth = readJson(HEALTH_INDEX_KEY, null);
    setHealthIndex({ ...DEFAULT_HEALTH_INDEX, ...(seededHealth || {}) });

    const localLogs = withoutSamples("biff_logs", readJson(BIFF_LOG_KEY, []));
    writeJson(BIFF_LOG_KEY, localLogs);
    setBiffLogs(localLogs);

    const seededReassessments = readJson(REASSESSMENT_KEY, null);
    setReassessments(seededReassessments ?? []);

    const seededCourtKey = readString(COURT_KEY_KEY, "");
    setCourtKey(seededCourtKey);

    setGreyRock(readString(GREY_ROCK_KEY, "") === "1");

    const seededSnapshotHistory = readJson(SNAPSHOT_HISTORY_KEY, []);
    if (Array.isArray(seededSnapshotHistory)) {
      setSnapshotHistory(seededSnapshotHistory);
    }

    // iter259 — auto-open suppressed per founder: the simplified
    // two-door landing shows only the Court Ordered / Self Journey
    // buttons on first visit. The intro Guide stays reachable (any
    // call site that invokes `onOpenIntroGuide` still works) but is
    // no longer force-opened on load.
    if (!hasIntroBeenSeen()) {
      // intentionally no-op; keep the "seen" marker so the follow-up
      // branch below doesn't misfire on later visits.
    } else {
      // iter231 — if a returning parent picked a path (via intro or
      // gateway) but never opened a tile in the meantime, and enough
      // time has passed, surface the Follow-up Guide check-in.
      try {
        const picked = readJson(PATH_PICKED_KEY, null);
        const engaged = readJson(FIRST_ENGAGEMENT_KEY, null);
        const dismissed = readJson(FOLLOWUP_DISMISSED_KEY, null);
        if (picked && picked.picked_at && !engaged) {
          const pickedAt = Date.parse(picked.picked_at);
          const hoursSince =
            (Date.now() - pickedAt) / (1000 * 60 * 60);
          const dismissedAt = dismissed?.at
            ? Date.parse(dismissed.at)
            : 0;
          const snoozeExpired =
            !dismissedAt ||
            Date.now() - dismissedAt >
              FOLLOWUP_SNOOZE_DAYS * 24 * 60 * 60 * 1000;
          if (hoursSince >= FOLLOWUP_MIN_HOURS && snoozeExpired) {
            setFollowupState({
              path: picked.path,
              daysSincePick: Math.max(
                1,
                Math.round(hoursSince / 24)
              ),
            });
          }
        }
      } catch {
        /* ignore */
      }
    }
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
        setPortalHydrated(true);
          return;
        }
        const s = data.state || {};
        if (RECORDS_ENABLED && Array.isArray(s.align_records)) {
          setAlignRecords(s.align_records);
          writeJson(ALIGN_RECORDS_KEY, s.align_records);
        }
        if (Array.isArray(s.milestones)) {
          const clean = withoutSamples("milestones", s.milestones);
          setMilestones(clean);
          writeJson(MILESTONE_KEY, clean);
        }
        if (Array.isArray(s.biff_logs)) {
          const clean = withoutSamples("biff_logs", s.biff_logs);
          setBiffLogs(clean);
          writeJson(BIFF_LOG_KEY, clean);
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
        if (typeof s.grey_rock === "boolean") {
          setGreyRock(s.grey_rock);
          writeString(GREY_ROCK_KEY, s.grey_rock ? "1" : "");
        }
        // iter222 — hydrate guided drafts so a signed-in parent can
        // resume a mid-wizard session on a new device.
        if (s.guided_drafts && typeof s.guided_drafts === "object") {
          try {
            for (const [topic, snapshot] of Object.entries(s.guided_drafts)) {
              if (snapshot && typeof snapshot === "object") {
                window.localStorage.setItem(
                  `sacoparents_guided_draft_${topic}`,
                  JSON.stringify(snapshot)
                );
              }
            }
          } catch {
            /* ignore quota / SSR */
          }
        }
        // iter227 — hydrate snapshot history so re-download works
        // across devices for a signed-in parent.
        if (Array.isArray(s.snapshot_history)) {
          setSnapshotHistory(s.snapshot_history);
          writeJson(SNAPSHOT_HISTORY_KEY, s.snapshot_history);
        }
        hasHydratedFromServerRef.current = true;
        setPortalHydrated(true);
      } catch {
        hasHydratedFromServerRef.current = true;
        setPortalHydrated(true);
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
        // Collect the current guided-journey drafts from localStorage
        // so the debounced PUT carries them up to portal_state for
        // cross-device resume.
        let guidedDrafts = null;
        try {
          const collected = {};
          const topics = [
            "foundation",
            "coparenting",
            "safety",
            "medical",
            "educational",
            "psychological",
          ];
          for (const t of topics) {
            const raw = window.localStorage.getItem(
              `sacoparents_guided_draft_${t}`
            );
            if (raw) {
              try {
                collected[t] = JSON.parse(raw);
              } catch {
                /* skip malformed */
              }
            }
          }
          if (Object.keys(collected).length) guidedDrafts = collected;
        } catch {
          /* SSR / storage disabled */
        }
        await api.put("/portal/state", {
          align_records: alignRecords,
          milestones,
          biff_logs: biffLogs,
          foundation_text: foundationText,
          legal_report: legalReport,
          health_index: healthIndex,
          court_key: courtKey,
          reassessments,
          grey_rock: greyRock,
          guided_drafts: guidedDrafts,
          snapshot_history: snapshotHistory,
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
    greyRock,
    guidedDraftsRev,
    snapshotHistory,
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

  // iter258 — Per-topic progress signal for the new 3-tab dashboard.
  // "completed" = a snapshot (or foundation text / safetyAck /
  // align-record) exists; "in_progress" = a guided-journey draft is
  // in localStorage but no completion artifact yet; otherwise "not_yet".
  const progressByTopic = useMemo(() => {
    const readDraft = (topic) => {
      try {
        return !!window.localStorage.getItem(
          `sacoparents_guided_draft_${topic}`
        );
      } catch {
        return false;
      }
    };
    // Old safety-check snapshots stay stored but never count or show.
    const hasSnap = (topic) =>
      snapshotHistory.some((s) => s?.topic === topic && s?.save_key !== "safety_ack");
    const state = (completed, topic) => {
      if (completed) return "completed";
      if (readDraft(topic)) return "in_progress";
      return "not_yet";
    };
    const foundationDone =
      !!(foundationText && foundationText.trim() &&
         foundationText.trim() !== (DEFAULT_FOUNDATION || "").trim());
    return {
      foundation: state(foundationDone || hasSnap("foundation"), "foundation"),
      coparenting: state(hasSnap("coparenting"), "coparenting"),
      safety: state(hasSnap("safety"), "safety"),
      educational: state(
        hasSnap("educational") || alignmentCounts.Educational > 0,
        "educational"
      ),
      medical: state(
        hasSnap("medical") || alignmentCounts.Medical > 0,
        "medical"
      ),
      psychological: state(
        hasSnap("psychological") || alignmentCounts.Psychological > 0,
        "psychological"
      ),
    };
  }, [
    snapshotHistory,
    foundationText,
    alignmentCounts,
    guidedDraftsRev,
  ]);

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
  const advocateReviewCount = useMemo(
    () => milestones.filter((m) => m.source === "advocate_review").length,
    [milestones]
  );

  const kudosStreak = useMemo(() => computeKudosStreak(milestones), [milestones]);

  const safetyFlagged = greyRock;

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

  const [homeRequest, setHomeRequest] = useState(0);
  const openDoorGateway = useCallback(() => {
    setScreen("journey");
    if (NEW_HOME_ON) setHomeRequest((n) => n + 1);
  }, []);

  const requestDoorEntry = useCallback((door) => {
    setScreen("journey");
    if (door === "court") setCourtRequest((n) => n + 1);
  }, []);

  const enterParentJourney = useCallback(
    () => {
      // iter231 — remember which path the parent picked + when, so
      // the Follow-up Guide can check in later if they never open a
      // tile. Overwrite is safe: parents can flip doors anytime.
      writeJson(PATH_PICKED_KEY, {
        path: "parent",
        picked_at: new Date().toISOString(),
      });
      requestDoorEntry("parent");
    },
    [requestDoorEntry]
  );
  const enterCourtPath = useCallback(
    () => {
      writeJson(PATH_PICKED_KEY, {
        path: "court",
        picked_at: new Date().toISOString(),
      });
      requestDoorEntry("court");
    },
    [requestDoorEntry]
  );

  // Grey-rock is a manual toggle; no reason is shown or stored.
  const setGreyRockMode = useCallback((on) => {
    setGreyRock(on);
    writeString(GREY_ROCK_KEY, on ? "1" : "");
    api.post("/portal/grey-rock/audit", { event: on ? "on" : "off", source: "toggle_chip" }).catch(() => {});
  }, []);

  // Court page: verify a case / invite code. Returns { caseId } or { error }.
  const verifyCourtKey = useCallback(async (key) => {
    const reasonMap = {
      expired: "That code has expired. Please request a new one from your mediator.",
      revoked: "That code has been revoked. Contact your mediator for a replacement.",
      unknown_key: "We don't recognise that code. Double-check it or ask your mediator.",
    };
    try {
      const { data } = await api.post("/portal/court-keys/verify", { key });
      if (!data?.verified) {
        return { error: reasonMap[data?.reason] || "We couldn't verify that code. Please check it and try again." };
      }
      const caseId = data.case_id || key;
      setCourtKey(caseId);
      setVerifiedMediator(data.mediator_name || "");
      writeString(COURT_KEY_KEY, caseId);
      return { caseId };
    } catch {
      return { error: "Network issue while verifying. Please check your connection and try again." };
    }
  }, []);

  const saveFoundationText = useCallback(() => {
    writeString(FOUNDATION_KEY, foundationText);
    alert("Foundation Statement PDF draft saved!");
  }, [foundationText]);

  const saveLegalReport = useCallback(() => {
    writeJson(LEGAL_REPORT_KEY, legalReport);
    alert("Official Legal Conflict Resolution Report draft saved!");
  }, [legalReport]);

  // BIFF suggested wording: only AI-reviewed text is ever shown; no rule-based placeholder or tone label.
  const cancelBiff = useCallback(() => {
    if (biffDebounceRef.current) clearTimeout(biffDebounceRef.current);
    if (biffAbortRef.current) {
      try {
        biffAbortRef.current.abort();
      } catch {
        /* noop */
      }
    }
  }, []);

  const resetBiff = useCallback(() => {
    setFlagList([]);
    setBiffOutput("");
    setRiskLabel("Neutral");
    setBiffStatus("idle");
    setBiffError("");
    setBiffLoading(false);
  }, []);

  const runAiRefine = useCallback(
    (val, delay = 900) => {
      cancelBiff();
      const trimmed = (val || "").trim();
      if (!trimmed) {
        resetBiff();
        return;
      }
      const flagged = greyRock;
      setBiffOutput("");
      setFlagList([]);
      setRiskLabel("Neutral");
      setBiffStatus("loading");
      setBiffLoading(true);
      setBiffError("");
      biffDebounceRef.current = setTimeout(async () => {
        const controller = new AbortController();
        biffAbortRef.current = controller;
        try {
          const { data } = await api.post(
            "/portal/biff-refine",
            { raw: trimmed, safety_flagged: flagged },
            { signal: controller.signal }
          );
          if (data?.status === "ok" && data.biff) {
            setBiffOutput(data.biff);
            setFlagList(Array.isArray(data.flags) ? data.flags : []);
            setRiskLabel(data.risk === "Escalation Flag" ? "Escalation Flag" : "Low Risk");
            setBiffStatus("ai");
          } else {
            setBiffStatus("unavailable");
            setBiffError("Suggested wording isn't available right now.");
          }
        } catch (err) {
          if (err?.name === "CanceledError" || err?.code === "ERR_CANCELED") return;
          setBiffStatus("unavailable");
          setBiffError("Suggested wording isn't available right now.");
        }
        setBiffLoading(false);
      }, delay);
    },
    [greyRock, cancelBiff, resetBiff]
  );

  // Editing the draft clears any earlier suggestion; nothing is sent until the parent asks.
  const handleRawInputChange = useCallback(
    (val) => {
      setRawInput(val);
      cancelBiff();
      resetBiff();
    },
    [cancelBiff, resetBiff]
  );

  const applyPreset = useCallback(
    (key, delay = 900) => {
      const p = PRESETS[key];
      if (!p) return;
      setRawInput(p.raw);
      runAiRefine(p.raw, delay);
    },
    [runAiRefine]
  );

  const transformBiff = useCallback((val) => runAiRefine(val, 0), [runAiRefine]);

  const copyBiffOutput = useCallback(() => {
    if (!biffOutput) return;
    try {
      navigator.clipboard.writeText(biffOutput);
      alert("Suggested wording copied.");
    } catch {
      alert("Clipboard unavailable — please copy manually.");
    }
  }, [biffOutput]);

  const copyToneSafe = useCallback(() => {
    if (!biffOutput) return;
    const stamp = [
      "",
      "---",
      "Suggested wording from SA CoParents Communication Builder",
      `Copied: ${new Date().toISOString().replace("T", " ").substring(0, 16)} UTC`,
      `Case: ${courtKey || "Self-Guided Coparenting Journey"}`,
      "sacoparentsapp.online",
    ].join("\n");
    try {
      navigator.clipboard.writeText(`${biffOutput}${stamp}`);
      alert("Suggested wording copied with a date stamp for your records.");
    } catch {
      alert("Clipboard unavailable — please copy manually.");
    }

    if (riskLabel === "Escalation Flag") {
      const kudos = {
        id: Date.now(),
        type: "success",
        title: "Calmer wording copied",
        date: new Date().toISOString().substring(0, 10),
        note:
          "You copied suggested wording for a draft the AI tone check flagged for friction.",
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
    const title = window.prompt("Enter Milestone Title (e.g. Smooth Holiday Transition):");
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

  // Toolkit tile → filter the Assessments (Medical/Educational/
  // Psychological) records section by category and scroll it into
  // view. Uses instance behaviour="smooth" for a gentle jump.
  const openAssessmentFolder = useCallback((category) => {
    setFolderFilter(category);
    // iter231 — mark first tile-open so the Follow-up Guide stops
    // nagging on the next visit.
    try {
      if (!window.localStorage.getItem(FIRST_ENGAGEMENT_KEY)) {
        writeJson(FIRST_ENGAGEMENT_KEY, {
          at: new Date().toISOString(),
        });
      }
    } catch {
      /* ignore SSR / quota */
    }
    // Defer one tick so the filter re-render commits before we scroll.
    setTimeout(() => {
      const el = document.getElementById("assessment-records-section");
      if (el && typeof el.scrollIntoView === "function") {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 60);
  }, []);

  // iter232 — Assessment Guide chatbot routing. Each key maps to a
  // concrete surface the parent already has in their journey so we
  // never introduce a new dead-end screen.
  const onStartAssessment = useCallback(
    (key) => {
      if (key === "court") {
        // Route back to the journey shell + trip the court door via
        // the container's existing helper.
        setScreen("journey");
        enterCourtPath();
        return;
      }
      if (key === "safety") {
        navigate("/help");
        return;
      }
      if (key === "communication") {
        // iter248 — Communication maps to the BIFF Coach drawer.
        setBiffDrawerOpen(true);
        return;
      }
      // The remaining four (coparenting, educational, medical,
      // psychological) all fire the Guided Journey wizard for that
      // topic. openGuidedJourney also marks first-engagement so the
      // iter231 follow-up nudge stops.
      openGuidedJourney(key);
    },
    [enterCourtPath]
  );

  // Guided-journey chat wizard (iter220). Opens the modal for a
  // specific topic; save handler funnels the collected answers into
  // the correct portal storage.
  const openGuidedJourney = useCallback((topic) => {
    setGuidedTopic(topic);
    // iter231 — count guided-chat opens as first engagement too.
    try {
      if (!window.localStorage.getItem(FIRST_ENGAGEMENT_KEY)) {
        writeJson(FIRST_ENGAGEMENT_KEY, {
          at: new Date().toISOString(),
        });
      }
    } catch {
      /* ignore */
    }
  }, []);

  const onGuidedSave = useCallback(
    ({ save_key, category, answers, summary }) => {
      if (!Array.isArray(answers) || answers.length === 0) {
        setGuidedTopic(null);
        return;
      }
      const today = new Date().toISOString().substring(0, 10);
      // iter227 — record every committed run so the "Recent snapshots"
      // strip on the toolkit can re-download without re-running the
      // wizard. Newest first, capped at SNAPSHOT_HISTORY_MAX.
      const snapshotEntry = {
        id: Date.now(),
        topic: guidedTopic,
        answers,
        saved_at: new Date().toISOString(),
        save_key,
        category: category || null,
        safety_flagged: !!safetyFlagged,
      };
      const nextHistory = [snapshotEntry, ...snapshotHistory].slice(
        0,
        SNAPSHOT_HISTORY_MAX
      );
      setSnapshotHistory(nextHistory);
      writeJson(SNAPSHOT_HISTORY_KEY, nextHistory);
      if (save_key === "foundation_text") {
        // Prepend the guided summary to the existing foundation text
        // so the parent's prior draft is preserved.
        const stitched = [
          "Foundation Statement (guided draft)",
          summary,
          foundationText && foundationText.trim() ? "\n---\nPrevious draft:\n" + foundationText : "",
        ]
          .filter(Boolean)
          .join("\n\n")
          .slice(0, 8000);
        setFoundationText(stitched);
        writeString(FOUNDATION_KEY, stitched);
      } else if (save_key === "align_record" && category && RECORDS_ENABLED) {
        const first = answers[0]?.answer || "Guided record";
        const rest = answers.slice(1).map((qa) => `- ${qa.answer}`).join("\n");
        const entry = {
          id: Date.now(),
          category,
          title: `${category} — Guided Journey ${today}`,
          provider: first.slice(0, 120),
          date: today,
          summary: rest.slice(0, 600),
        };
        const next = [entry, ...alignRecords];
        setAlignRecords(next);
        writeJson(ALIGN_RECORDS_KEY, next);
        openAssessmentFolder(category);
      } else if (save_key === "cop_assessment_note") {
        // Append the co-parenting reflection to milestones as a
        // "reassessment" so it lands in the weekly PDF too.
        const entry = {
          id: Date.now(),
          type: "success",
          title: `Co-parenting Reflection ${today}`,
          date: today,
          note: summary.slice(0, 600),
        };
        const next = [entry, ...milestones];
        setMilestones(next);
        writeJson(MILESTONE_KEY, next);
      }
      setGuidedTopic(null);
    },
    [foundationText, alignRecords, milestones, openAssessmentFolder, guidedTopic, safetyFlagged, snapshotHistory]
  );

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

  // iter222 — download the Coparent Snapshot PDF built from a finished
  // Guided Journey run. Called from GuidedJourneyModal's recap card.
  // iter223 — supports `variant='fridge'` for the postcard-size card.
  // iter225 — supports `variant='fridge_pair'` for two side-by-side.
  const downloadGuidedSnapshot = useCallback(
    async ({ topic, answers, safety_flagged, variant }) => {
      let chosen = "standard";
      let suffix = "";
      if (variant === "fridge") {
        chosen = "fridge";
        suffix = "-fridge";
      } else if (variant === "fridge_pair") {
        chosen = "fridge_pair";
        suffix = "-fridge-pair";
      }
      await downloadPdfFromApi(
        "/portal/guided-snapshot-pdf",
        `coparent-snapshot-${topic}${suffix}.pdf`,
        {
          topic,
          answers,
          parent_name: user?.name || null,
          case_ref: courtKey || null,
          safety_flagged: !!safety_flagged,
          variant: chosen,
        }
      );
    },
    [downloadPdfFromApi, user, courtKey]
  );

  // iter229 — delete a single snapshot from the library. Removes
  // by stable id (with fallback to index-match) and syncs via the
  // existing debounced PUT.
  const onDeleteSnapshot = useCallback(
    (idOrIdx) => {
      setSnapshotHistory((prev) => {
        const next = prev.filter((s, i) =>
          s.id !== undefined
            ? s.id !== idOrIdx
            : i !== idOrIdx
        );
        writeJson(SNAPSHOT_HISTORY_KEY, next);
        return next;
      });
    },
    []
  );

  // iter250 — Draft-to-Snapshot. Files the parent's raw first-draft
  // + its BIFF rewrite into the Snapshot Library as a single
  // `biff_pair` snapshot so the mediator PDF can show the actual
  // tone progression (not just the before/after count). Uses the
  // existing `answers: [{question, answer}, ...]` schema so the
  // backend sanitizer and SnapshotStrip's rename/pin/share flows
  // all work without a new code path.
  const onSaveBiffSnapshot = useCallback(
    ({ raw, biff, category }) => {
      const rawTrim = (raw || "").trim();
      const biffTrim = (biff || "").trim();
      if (!rawTrim || !biffTrim) return false;
      const nowIso = new Date().toISOString();
      const snapshotEntry = {
        id: Date.now(),
        topic: "biff_pair",
        answers: [
          { question: "Original message", answer: rawTrim.slice(0, 2000) },
          { question: "BIFF rewrite", answer: biffTrim.slice(0, 2000) },
        ],
        saved_at: nowIso,
        save_key: `biff_pair_${Date.now()}`,
        category: category || null,
        safety_flagged: !!safetyFlagged,
      };
      setSnapshotHistory((prev) => {
        const next = [snapshotEntry, ...prev].slice(0, SNAPSHOT_HISTORY_MAX);
        writeJson(SNAPSHOT_HISTORY_KEY, next);
        return next;
      });
      return true;
    },
    [safetyFlagged]
  );

  // iter235 — rename a saved snapshot so the library reads like a
  // real folder ("Emma's summer plan") instead of the auto-labelled
  // "Foundation · 3d ago". Label is capped at 40 chars at the input
  // and trimmed again here so empty values clear the label cleanly.
  const onRenameSnapshot = useCallback(
    (idOrIdx, rawLabel) => {
      const trimmed = (rawLabel || "").trim().slice(0, 40);
      setSnapshotHistory((prev) => {
        const next = prev.map((s, i) => {
          const match =
            s.id !== undefined ? s.id === idOrIdx : i === idOrIdx;
          if (!match) return s;
          if (!trimmed) {
            // Clear a label by passing an empty string.
            const { label: _dropped, ...rest } = s;
            return rest;
          }
          return { ...s, label: trimmed };
        });
        writeJson(SNAPSHOT_HISTORY_KEY, next);
        return next;
      });
    },
    []
  );

  // iter237 — pin / unpin a snapshot. Pinned items float to the top
  // of the Snapshot library (sort rule lives in SnapshotStrip). When
  // pinning, stamp `pinned_at` so a flurry of pin flips preserves
  // the most-recently-pinned order within the pinned group.
  const onPinSnapshot = useCallback(
    (idOrIdx, nextPinned) => {
      setSnapshotHistory((prev) => {
        const next = prev.map((s, i) => {
          const match =
            s.id !== undefined ? s.id === idOrIdx : i === idOrIdx;
          if (!match) return s;
          if (nextPinned) {
            return {
              ...s,
              pinned: true,
              pinned_at: new Date().toISOString(),
            };
          }
          // Unpinning strips both fields so the sorter falls back
          // to insertion order cleanly.
          const { pinned: _p, pinned_at: _pa, ...rest } = s;
          return rest;
        });
        writeJson(SNAPSHOT_HISTORY_KEY, next);
        return next;
      });
    },
    []
  );

  // iter222 — fire when the guided modal writes/clears a localStorage
  // draft. Bumping guidedDraftsRev re-triggers the debounced PUT
  // effect, which reads all localStorage guided drafts and syncs
  // them into portal_state.guided_drafts.
  const onGuidedDraftPersist = useCallback(() => {
    if (!user) return;
    setGuidedDraftsRev((r) => r + 1);
  }, [user]);

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
          } else if (artefactType === "complete") {
            setShareCompleteLastUrl(url);
          } else {
            alert(
              `Share link copied to clipboard:\n\n${url}\n\nText or email this to your pediatrician, mediator, or attorney. It works for ${opts.ttl_days || 30} days.`
            );
          }
        } catch {
          setShareStatus((prev) => ({ ...prev, [artefactType]: "copied" }));
          if (artefactType === "legal") {
            setShareLegalLastUrl(url);
          } else if (artefactType === "complete") {
            setShareCompleteLastUrl(url);
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
    return downloadPdfFromApi(
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

  // ---- Complete Coparenting Report (iter218) ------------------
  // Bundle every parent-facing artefact into one PDF: safety step status,
  // co-parenting assessment (health index), individual + joint
  // Align-Before-Agreement records (Medical/Educational/Psychological),
  // and Foundation Statement. Empty sections render as stubs so the
  // reader sees what's still to build.
  const buildCompleteReportPayload = useCallback(
    () => ({
      cop_assessment: healthIndex,
      align_records: alignRecords,
      // Joint records aren't held in the portal state today — the
      // joint flow lives on /joint-agreement. Pass an empty list so
      // the section renders its empty-state stub with the "build
      // your joint report" pointer.
      joint_records: [],
      foundation_text: foundationText || null,
      case_ref: courtKey || null,
      author_name: user?.name || null,
    }),
    [healthIndex, alignRecords, foundationText, courtKey, user]
  );

  const downloadCompleteReportPdf = useCallback(() => {
    downloadPdfFromApi(
      "/portal/complete-report-pdf",
      "sacoparents-complete-report.pdf",
      buildCompleteReportPayload()
    );
  }, [downloadPdfFromApi, buildCompleteReportPayload]);

  const onShareFoundation = useCallback(() => {
    createShareLink("foundation", {
      foundation_text: foundationText,
      case_ref: courtKey || null,
      author_name: user?.name || null,
    });
  }, [createShareLink, foundationText, courtKey, user]);

  // Email Foundation Statement to co-parent (iter219): opens the parent's own mail app.
  const onEmailFoundationToCoparent = useCallback(async () => {
    if (!foundationText.trim()) {
      alert(
        "Write your Foundation Statement first — the email links to the PDF."
      );
      return;
    }
    setShareStatus((prev) => ({ ...prev, foundation_email: "loading" }));
    try {
      const { data } = await api.post("/portal/share", {
        artefact_type: "foundation",
        payload: {
          foundation_text: foundationText,
          case_ref: courtKey || null,
          author_name: user?.name || null,
        },
        ttl_days: 30,
      });
      if (!data?.url) throw new Error("no share url");
      const subject = encodeURIComponent(
        "My Foundation Statement — sacoparentsapp.online"
      );
      const body = encodeURIComponent(
        `Hi,\n\nHere's my Foundation Statement for our co-parenting.\n\n` +
          `${foundationText.slice(0, 500)}${foundationText.length > 500 ? "..." : ""}\n\n` +
          `Full PDF (link expires in 30 days):\n${data.url}\n\n` +
          `— Sent via sacoparentsapp.online`
      );
      // Empty `mailto:` recipient — the user's email client opens with
      // no address prefilled, so the app never sees or stores the
      // co-parent's email. Privacy-first.
      window.location.href = `mailto:?subject=${subject}&body=${body}`;
      setShareStatus((prev) => ({ ...prev, foundation_email: "copied" }));
      setTimeout(
        () =>
          setShareStatus((prev) => ({
            ...prev,
            foundation_email: undefined,
          })),
        4000
      );
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("email foundation to coparent failed", err);
      setShareStatus((prev) => ({ ...prev, foundation_email: "error" }));
      alert(
        "Couldn't prepare the email — please try again in a moment, or use the Share link button."
      );
    }
  }, [foundationText, courtKey, user]);

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

  const onShareCompleteReport = useCallback(() => {
    setShareCompleteLastUrl("");
    setShareCompleteOpen(true);
  }, []);

  const onMintShareComplete = useCallback(
    (opts) => {
      createShareLink("complete", buildCompleteReportPayload(), opts);
    },
    [createShareLink, buildCompleteReportPayload]
  );

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

  const showBackBtn = screen !== "journey";
  const dashboardMode = NEW_HOME_ON && !onFlow && screen === "journey" && journeyView === "door";

  return (
    <div
      className="bg-slate-50 text-slate-800 font-sans min-h-screen flex flex-col pb-32"
      data-testid="sacoparents-portal"
    >
      <PathPicker />
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
        <div className="max-w-md mx-auto px-4 py-3 flex flex-wrap justify-between items-center gap-2">
          <div className={`flex items-center space-x-2.5 flex-1 ${dashboardMode ? "min-w-[14rem]" : "min-w-[10rem]"}`}>
            <div className="bg-purple-800/50 p-2 rounded-xl backdrop-blur-md border border-purple-400/30 shrink-0">
              <i className="fa-solid fa-hands-holding-child text-purple-300 text-lg"></i>
            </div>
            <div className="min-w-0">
              <p className="text-base font-bold tracking-tight">
                sacoparentsapp.online
              </p>
              <p className="text-[0.625rem] text-purple-200">
                SA CoParents Assessment & Alignment Portal
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0 ml-auto">
            {showBackBtn && (
              <button
                data-testid="header-back-btn"
                onClick={openDoorGateway}
                className="bg-purple-900 hover:bg-purple-800 text-white px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 border border-purple-700 transition"
              >
                <i className="fa-solid fa-arrow-left"></i> Journey
              </button>
            )}
            <button
              onClick={handlePrint}
              data-testid="export-pdf-btn"
              className="bg-purple-700 hover:bg-purple-600 text-white px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 transition shadow"
            >
              <i className="fa-solid fa-file-pdf"></i> Export PDF
            </button>
            {(dashboardMode || onFlow) && (
              <button
                type="button"
                onClick={quickExitAction}
                data-testid="header-quick-exit"
                className="min-h-[44px] px-4 rounded-full bg-[#b42318] hover:bg-[#9a1d14] text-white text-[0.95rem] font-bold transition-colors"
              >
                Quick Exit <span aria-hidden="true">✕</span>
              </button>
            )}
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
          {courtKey || "Self-Guided Coparenting Journey"}
        </p>
      </div>

      {/* MAIN CONTAINER */}
      <main className="max-w-md mx-auto px-4 py-4 flex-1 w-full space-y-4">
        {onFlow && <JourneyFlow />}
        {!onFlow && screen === "journey" && !dashboardMode && <ProfessionalAccessCard />}
        {!onFlow && screen === "journey" && (
          <JourneyShell
            user={user}
            pathPickedAt={
              (readJson(PATH_PICKED_KEY, null) || {}).picked_at || null
            }
            courtKey={courtKey}
            verifiedMediator={verifiedMediator}
            /* iter252 — Communication Builder progress signals.
               `biffAuthoredCount` subtracts the seed demo entry so a
               brand-new parent sees "0 messages reworked." A filed
               `biff_pair` snapshot (iter250 Draft-to-Snapshot) is a
               stronger explicit-save signal. */
            biffAuthoredCount={biffLogs.length}
            biffPairCount={
              snapshotHistory.filter((s) => s?.topic === "biff_pair").length
            }
            onEnterParent={enterParentJourney}
            onVerifyCourtKey={verifyCourtKey}
            onDownloadCourtPdf={downloadLegalPdf}
            courtRequest={courtRequest}
            overlayOpen={
              !!guidedTopic ||
              biffDrawerOpen ||
              recordsDrawerOpen ||
              foundationDrawerOpen ||
              commBuilderOpen ||
              introOpen ||
              !!followupState ||
              shareLegalOpen ||
              shareCompleteOpen
            }
            onOpenBiffCoach={() => setBiffDrawerOpen(true)}
            biffCoachOpen={biffDrawerOpen}
            onOpenCommBuilder={(focus) => {
              setCommBuilderFocus(focus === "history" ? "history" : null);
              setCommBuilderOpen(true);
            }}
            onOpenIntroGuide={() => setIntroOpen(true)}
            onOpenReport={() => setFoundationDrawerOpen(true)}
            progressByTopic={progressByTopic}
            pairProgress={pairProgress}
            safetyFlagged={safetyFlagged}
            onViewChange={setJourneyView}
            biffReady={!user || portalHydrated}
            homeRequest={homeRequest}
          />
        )}

      </main>
      {/* The site-wide footer sits under the fixed bottom bar here, so the link is repeated above it. */}
      <div data-testid="portal-privacy-footer" className={`no-print py-4 text-center text-[0.8125rem] ${dashboardMode ? "hidden" : ""}`}>
        <Link to="/privacy-notice" data-testid="portal-privacy-footer-link" className="font-semibold text-[#3D1A78] underline underline-offset-2">
          Privacy Notice
        </Link>
        <span aria-hidden="true" className="mx-2 text-[#B9B3C9]">·</span>
        <Link to="/who-can-see-my-information" data-testid="portal-who-can-see-footer-link" className="font-semibold text-[#3D1A78] underline underline-offset-2">
          Who can see my information
        </Link>
      </div>

      {/* Safety crisis strip — pinned above bottom nav */}
      <SafetyCrisisStrip />

      {/* BOTTOM NAV */}
      <nav
        className="fixed bottom-0 left-0 right-0 bg-white border-t border-purple-200 py-2 px-2 gap-1 flex justify-around items-start z-40 no-print max-w-md mx-auto shadow-lg"
        data-testid="bottom-nav"
      >
        <button
          data-testid="nav-doors"
          onClick={() => navigate("/journey")}
          className={
            onFlow
              ? "flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center bottom-nav-active"
              : "flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center text-slate-500 hover:text-purple-800"
          }
        >
          <i className="fa-solid fa-compass text-base"></i>
          <span className="text-[0.5625rem] font-semibold">Journey</span>
        </button>
        <button
          data-testid="nav-report"
          onClick={() => {
            // iter248 — "Report" at the bottom nav opens the Foundation
            // Statement drawer (Step 5). The parent's primary report
            // artefact is the Foundation Statement PDF; nothing else
            // in the five-step journey calls itself a "report."
            setFoundationDrawerOpen(true);
          }}
          className={
            foundationDrawerOpen
              ? "flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center bottom-nav-active"
              : "flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center text-slate-500 hover:text-purple-800"
          }
        >
          <i className="fa-solid fa-scale-balanced text-base"></i>
          <span className="text-[0.5625rem] font-semibold">Report</span>
        </button>
        <button
          data-testid="nav-biff"
          onClick={() => {
            // iter248 — "BIFF Tool" at the bottom nav opens the BIFF
            // Coach drawer directly (Step 4). No more hub-tab switch.
            setBiffDrawerOpen(true);
          }}
          className={
            biffDrawerOpen
              ? "flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center bottom-nav-active"
              : "flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center text-slate-500 hover:text-purple-800"
          }
        >
          <i className="fa-solid fa-comments text-base"></i>
          <span className="text-[0.5625rem] font-semibold">BIFF Tool</span>
        </button>
        <button
          data-testid="nav-print"
          onClick={handlePrint}
          className="flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center text-slate-500 hover:text-purple-800"
        >
          <i className="fa-solid fa-file-pdf text-base"></i>
          <span className="text-[0.5625rem] font-semibold">PDF Export</span>
        </button>
        <button
          data-testid="nav-get-help"
          onClick={() => navigate("/help")}
          className="flex flex-1 min-w-0 flex-col items-center space-y-0.5 text-center text-slate-500 hover:text-purple-800"
        >
          <i className="fa-solid fa-life-ring text-base"></i>
          <span className="text-[0.5625rem] font-semibold">Get help</span>
        </button>
      </nav>


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

      {/* Share Complete Coparenting Report modal (same passphrase +
          TTL flow, reuses ShareLegalModal via `variant='complete'`). */}
      <ShareLegalModal
        variant="complete"
        open={shareCompleteOpen}
        onClose={() => {
          setShareCompleteOpen(false);
          setShareCompleteLastUrl("");
        }}
        onMint={onMintShareComplete}
        loading={shareStatus.complete === "loading"}
        lastUrl={shareCompleteLastUrl}
      />

      {/* iter248 — three modal drawers replace the old parent-journey
          screen's hub-tabs toggle. BIFF Coach / Alignment Records /
          Foundation Statement are invoked directly from the Step
          panels and bottom-nav. The grey-rock toggle is mirrored
          inside the BIFF drawer. */}
      {commBuilderOpen && (
        <CommunicationBuilderView
          open
          focus={commBuilderFocus}
          onClose={() => setCommBuilderOpen(false)}
          onQuickExit={quickExitAction}
          greyRock={safetyFlagged}
          biff={{
            rawInput,
            setRawInput: handleRawInputChange,
            transform: transformBiff,
            applyPreset,
            riskLabel,
            flagList,
            biffOutput,
            biffLoading,
            biffStatus,
            copyToneSafe,
            logCommunication,
            onSaveBiffSnapshot,
          }}
          extras={{
            biffLogs,
            milestones,
            successCount,
            frictionCount,
            addMilestoneLog,
            advocateReviewCount,
            downloadWeeklyProgressPdf,
            onShareWeekly,
            shareStatus,
          }}
        />
      )}
      <BiffCoachDrawer
        open={biffDrawerOpen}
        onClose={() => setBiffDrawerOpen(false)}
        safetyFlagged={safetyFlagged}
        onSetGreyRock={setGreyRockMode}
        onSaveBiffSnapshot={onSaveBiffSnapshot}
        rawInput={rawInput}
        onRawInputChange={handleRawInputChange}
        applyPreset={applyPreset}
        riskLabel={riskLabel}
        flagList={flagList}
        biffOutput={biffOutput}
        biffLoading={biffLoading}
        biffError={biffError}
        biffStatus={biffStatus}
        onSuggest={() => transformBiff(rawInput)}
        copyBiffOutput={copyBiffOutput}
        copyToneSafe={copyToneSafe}
        logCommunication={logCommunication}
        biffLogs={biffLogs}
        milestones={milestones}
        successCount={successCount}
        frictionCount={frictionCount}
        addMilestoneLog={addMilestoneLog}
        advocateReviewCount={advocateReviewCount}
        downloadWeeklyProgressPdf={downloadWeeklyProgressPdf}
        onShareWeekly={onShareWeekly}
        shareStatus={shareStatus}
      />
      <RecordsDrawer
        open={recordsDrawerOpen}
        onClose={() => setRecordsDrawerOpen(false)}
        alignmentCounts={alignmentCounts}
        folderFilter={folderFilter}
        setFolderFilter={setFolderFilter}
        filteredRecords={filteredRecords}
        onAddAlignment={() => setAlignmentOpen(true)}
      />
      <FoundationDrawer
        open={foundationDrawerOpen}
        onClose={() => setFoundationDrawerOpen(false)}
        foundationText={foundationText}
        setFoundationText={setFoundationText}
        saveFoundationText={saveFoundationText}
        downloadFoundationPdf={downloadFoundationPdf}
        onShareFoundation={onShareFoundation}
        shareStatus={shareStatus}
        onEmailFoundationToCoparent={onEmailFoundationToCoparent}
      />

      {/* Guided-journey chat wizard (iter220) — one modal, six topics. */}
      {guidedTopic && (
        <GuidedJourneyModal
          topic={guidedTopic}
          open={!!guidedTopic}
          onClose={() => setGuidedTopic(null)}
          onSave={onGuidedSave}
          safetyFlagged={safetyFlagged}
          onDownloadSnapshot={downloadGuidedSnapshot}
          onDraftPersist={onGuidedDraftPersist}
        />
      )}

      {/* iter228 — SA CoParents Guide intro chatbot */}
      <IntroChatBot
        open={introOpen}
        onClose={() => setIntroOpen(false)}
        onEnterParent={enterParentJourney}
        onEnterCourt={enterCourtPath}
      />

      {/* iter231 — SA CoParents Guide follow-up nudge */}
      {followupState && (
        <GuideFollowupModal
          open={!!followupState}
          onClose={() => setFollowupState(null)}
          onDismissForWeek={() => {
            writeJson(FOLLOWUP_DISMISSED_KEY, {
              at: new Date().toISOString(),
            });
            setFollowupState(null);
          }}
          onResume={() => {
            // Mark engagement so we don't loop back to this modal
            // even if the parent bounces before opening a tile.
            try {
              if (!window.localStorage.getItem(FIRST_ENGAGEMENT_KEY)) {
                writeJson(FIRST_ENGAGEMENT_KEY, {
                  at: new Date().toISOString(),
                });
              }
            } catch {
              /* ignore */
            }
            const path = followupState.path;
            setFollowupState(null);
            if (path === "court") enterCourtPath();
            else enterParentJourney();
          }}
          path={followupState.path}
          daysSincePick={followupState.daysSincePick}
          parentName={user?.name || null}
        />
      )}

      {/* iter233 — SA CoParents Assessment Guide chatbot has moved
          inline on the Alignment & Tools page. The <AssessmentGuideChat/>
          modal export remains available for future intro/follow-up
          flows if they need a popup, but it's no longer mounted here. */}

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
