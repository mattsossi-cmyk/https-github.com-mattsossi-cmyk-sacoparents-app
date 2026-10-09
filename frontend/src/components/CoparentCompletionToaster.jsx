/**
 * CoparentCompletionToaster — headless dashboard poller.
 *
 * Fires a `sonner` toast the moment the *other* parent on a Joint
 * Alignment case finishes their assessment. Never surfaces the
 * co-parent's answers — only the completion milestone timestamp
 * returned by `/api/joint-alignment/mine`.
 *
 * Mirrors the design of `NewCommentToaster.jsx`:
 *   * Reads `coparentCompletionSeenAt` from localStorage (ISO).
 *   * On boot, adopts the newest completion timestamp so a returning
 *     parent doesn't get a wall of toasts for historical completions.
 *   * Every 60 seconds thereafter, any completion strictly newer
 *     than the stored value fires a toast and bumps the stored ISO.
 *   * Aggregates when >2 land at once so the corner stays tidy.
 */
import React, { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const POLL_MS = 60_000;
const STORAGE_KEY = "coparentCompletionSeenAt";

const ASSESSMENT_LABELS = {
  "co-parenting": "Co-Parenting Assessment",
  communication: "Communication Assessment",
  educational: "Educational Needs Assessment",
  medical: "Medical Needs Assessment",
  psychological: "Psychological / Emotional Needs Assessment",
  "special-needs": "Special Needs Assessment",
};

function readSeen() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function writeSeen(iso) {
  try {
    window.localStorage.setItem(STORAGE_KEY, iso);
  } catch {
    /* private mode / no localStorage — best effort only */
  }
}

function firstName(name) {
  return (name || "").trim().split(/\s+/)[0] || "Your co-parent";
}

export default function CoparentCompletionToaster() {
  const bootedRef = useRef(false);
  const toastedRef = useRef(new Set());
  const { user } = useAuth();
  const isSignedIn = !!user;

  const poll = useCallback(async () => {
    try {
      // Session cookie is auto-sent by api.withCredentials — a 401
      // just means "not signed in yet" and lands in the catch.
      const r = await api.get("/joint-alignment/mine");
      const events = [];
      for (const c of r.data?.cases || []) {
        const completedAt = c?.coparent?.completed_at;
        if (!completedAt) continue;
        events.push({
          case_id: c.case_id,
          assessment_type: c.assessment_type,
          coparent_name: c?.coparent?.name,
          coparent_completed_at: completedAt,
          my_status: c.my_status,
        });
      }
      if (events.length === 0) return;

      // Newest first
      events.sort((a, b) =>
        a.coparent_completed_at > b.coparent_completed_at ? -1 : 1
      );
      const newestIso = events[0].coparent_completed_at;
      const seen = readSeen();

      // First-time seed: adopt the current newest so a returning
      // parent doesn't get a wall of toasts for historical events.
      if (!seen) {
        writeSeen(newestIso);
        bootedRef.current = true;
        return;
      }
      bootedRef.current = true;

      const fresh = events.filter(
        (e) => (e.coparent_completed_at || "") > seen
      );
      if (fresh.length === 0) return;

      const notYetToasted = fresh.filter(
        (e) => !toastedRef.current.has(e.case_id + e.coparent_completed_at)
      );
      if (notYetToasted.length === 0) return;

      if (notYetToasted.length >= 3) {
        toast.success(
          `${notYetToasted.length} co-parents just finished their assessments.`,
          {
            description: "Open your dashboard to see which cases advanced.",
            duration: 8000,
            action: {
              label: "Open dashboard",
              onClick: () => window.location.assign("/dashboard"),
            },
          }
        );
      } else {
        for (const ev of notYetToasted) {
          const assessmentLabel =
            ASSESSMENT_LABELS[ev.assessment_type] || "assessment";
          const iMissing = ev.my_status !== "completed";
          toast.success(
            `${firstName(ev.coparent_name)} finished the ${assessmentLabel}.`,
            {
              description: iMissing
                ? "Case " +
                  ev.case_id +
                  " — your turn. When you finish, your professional will generate the Co-Parenting Agreement."
                : "Case " +
                  ev.case_id +
                  " — both of you are done. Your professional can now generate the Co-Parenting Agreement.",
              duration: 9000,
              action: {
                label: "Open dashboard",
                onClick: () => window.location.assign("/dashboard"),
              },
            }
          );
        }
      }

      notYetToasted.forEach((e) =>
        toastedRef.current.add(e.case_id + e.coparent_completed_at)
      );
      writeSeen(newestIso);
    } catch {
      /* Network hiccup or 401 — retry on next tick */
    }
  }, []);

  useEffect(() => {
    if (!isSignedIn) return;
    // Small delay so the initial dashboard render isn't racing our
    // fetch burst.
    const boot = setTimeout(poll, 2500);
    const interval = setInterval(poll, POLL_MS);
    return () => {
      clearTimeout(boot);
      clearInterval(interval);
    };
  }, [isSignedIn, poll]);

  // Re-poll on tab focus so a parent switching back from email gets
  // a toast without waiting for the next interval tick.
  useEffect(() => {
    if (!isSignedIn) return;
    const onFocus = () => poll();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [isSignedIn, poll]);

  return null;
}
