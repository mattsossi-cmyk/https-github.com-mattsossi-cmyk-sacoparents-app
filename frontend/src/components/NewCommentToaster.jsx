/**
 * NewCommentToaster — headless component that polls the reviewer
 * comment feed and fires a `sonner` toast the moment a comment
 * appears that the parent hasn't seen yet.
 *
 * How it decides "new":
 *   * Reads `pathwayCommentSeenAt` from localStorage (ISO timestamp).
 *   * On first mount, if the value is missing, it seeds it to the
 *     current newest `created_at` — silent baseline so a returning
 *     parent doesn't get a wall of toasts for comments that
 *     already lived on the dashboard.
 *   * On each poll, any comment with `created_at` strictly greater
 *     than the stored value triggers a toast, and the stored value
 *     bumps to the freshest `created_at` seen.
 *
 * Renders nothing. Mounted from the Dashboard so it only runs when
 * a signed-in parent is on the primary in-app surface.
 */
import React, { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";
import { api } from "../lib/api";


const STORAGE_KEY = "pathwayCommentSeenAt";
const POLL_MS = 30_000;


function readSeen() {
  try { return window.localStorage.getItem(STORAGE_KEY) || ""; }
  catch { return ""; }
}


function writeSeen(iso) {
  try { window.localStorage.setItem(STORAGE_KEY, iso); }
  catch { /* private-mode / storage full — best effort only */ }
}


function firstName(name) {
  return (name || "").trim().split(/\s+/)[0] || "a reviewer";
}


function focusPathwayCommentsCard() {
  // If we're already on the dashboard, smooth-scroll to the reviewer-
  // comments card. Otherwise navigate + hash so the target lands in view.
  if (window.location.pathname === "/dashboard") {
    const el = document.getElementById("pathway-reviewer-comments");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
  }
  window.location.assign("/dashboard#pathway-reviewer-comments");
}


export default function NewCommentToaster() {
  const bootedRef = useRef(false);
  const toastedRef = useRef(new Set());

  const poll = useCallback(async () => {
    try {
      const { data } = await api.get("/pathway-report/comments/mine");
      const comments = Array.isArray(data?.comments) ? data.comments : [];
      if (comments.length === 0) return;

      // Sorted newest-first server-side. Grab the freshest timestamp.
      const newestIso = comments[0]?.created_at || "";
      const seen = readSeen();

      // First-time seed: adopt the current newest so we don't spam
      // a returning parent with historical comments.
      if (!seen) {
        if (newestIso) writeSeen(newestIso);
        bootedRef.current = true;
        return;
      }
      bootedRef.current = true;

      // Everything strictly newer than seen is a fresh comment.
      const fresh = comments.filter(
        (c) => (c.created_at || "") > seen,
      );
      if (fresh.length === 0) return;

      // De-dupe against toasts we've already popped in this session
      // (belt-and-braces — the localStorage bump below covers most
      // cases but a very slow poll window could still repeat).
      const notYetToasted = fresh.filter(
        (c) => !toastedRef.current.has(c.comment_id),
      );

      // Aggregate when >2 come in at once — keeps the corner tidy.
      if (notYetToasted.length >= 3) {
        toast.success(
          `${notYetToasted.length} new reviewer comments on your pathway report.`,
          {
            description: "Open the dashboard card to read them.",
            duration: 8000,
            action: {
              label: "Open",
              onClick: focusPathwayCommentsCard,
            },
          },
        );
      } else {
        for (const c of notYetToasted) {
          const who = firstName(c.reviewer_name);
          toast.success(
            `${who} left a comment on your pathway report`,
            {
              description: (c.comment_text || "").slice(0, 120),
              duration: 8000,
              action: {
                label: "Read",
                onClick: focusPathwayCommentsCard,
              },
            },
          );
        }
      }
      notYetToasted.forEach((c) => toastedRef.current.add(c.comment_id));

      if (newestIso) writeSeen(newestIso);
    } catch {
      // Silent — this is a background helper, never surface poll failures.
    }
  }, []);

  useEffect(() => {
    // Initial baseline / catch-up on mount, then poll every 30s.
    // Delayed 4s so we don't compete with the dashboard's own
    // opening fetch burst.
    const kickoff = window.setTimeout(poll, 4000);
    const interval = window.setInterval(poll, POLL_MS);
    return () => {
      window.clearTimeout(kickoff);
      window.clearInterval(interval);
    };
  }, [poll]);

  // Poll immediately when the tab regains focus so a parent who
  // switches from their email inbox back to SA CoParents sees the
  // toast without waiting for the next interval tick.
  useEffect(() => {
    const onFocus = () => { poll(); };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [poll]);

  // Nothing to render — this is a headless side-effect component.
  return null;
}
