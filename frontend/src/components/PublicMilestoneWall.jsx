import React, { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  ShieldCheck, Users, EyeOff, Loader2, Sparkles, Info, Heart,
  MessageCircle, TrendingUp, Award,
} from "lucide-react";
import { toast } from "sonner";
import { logError } from "../lib/logger";

/**
 * PublicMilestoneWall — a small, opt-in feed of anonymised badges other
 * parents have earned in the last 30 days. First-timers see momentum and
 * feel the community cheering them on.
 *
 * Privacy contract (mirrored server-side):
 *   • Wall is completely off unless the parent flips the opt-in toggle.
 *   • The feed only ever shows a stable user_hash + badge type + relative
 *     time. No names, no emails, no city, no numeric stats.
 *   • Opting out later stops future events; existing events remain until
 *     the admin runs a scheduled purge.
 */
const BADGE_META = {
  foundation_ready: {
    accent: { bg: "bg-[#F1F9F4]", border: "border-[#B5DFC5]", text: "text-[#1F5C3B]" },
    Icon: ShieldCheck,
    iconClass: "text-[#1F5C3B]",
  },
  first_compare: {
    accent: { bg: "bg-[#F5F1FB]", border: "border-[#D6CFE8]", text: "text-[#3D1A78]" },
    Icon: Sparkles,
    iconClass: "text-[#3D1A78]",
  },
  high_alignment_90: {
    accent: { bg: "bg-[#FBEDDA]", border: "border-[#EDD5B0]", text: "text-[#8C5A2C]" },
    Icon: TrendingUp,
    iconClass: "text-[#8C5A2C]",
  },
  communication_master: {
    accent: { bg: "bg-[#EEF3FB]", border: "border-[#C7D6EB]", text: "text-[#233B6C]" },
    Icon: MessageCircle,
    iconClass: "text-[#233B6C]",
  },
  week_streak_7: {
    accent: { bg: "bg-[#F5F1FB]", border: "border-[#D6CFE8]", text: "text-[#3D1A78]" },
    Icon: Award,
    iconClass: "text-[#3D1A78]",
  },
  month_streak_30: {
    accent: { bg: "bg-[#F1F9F4]", border: "border-[#B5DFC5]", text: "text-[#1F5C3B]" },
    Icon: Award,
    iconClass: "text-[#1F5C3B]",
  },
  hundred_day_streak: {
    accent: { bg: "bg-[#FBEDDA]", border: "border-[#EDD5B0]", text: "text-[#8C5A2C]" },
    Icon: Award,
    iconClass: "text-[#8C5A2C]",
  },
};

const CATEGORY_CHIPS = [
  { key: "all",         label: "All" },
  { key: "milestones",  label: "Streaks & badges" },
  { key: "streaks",     label: "Streaks" },
  { key: "foundations", label: "Foundations" },
  { key: "alignment",   label: "Alignment" },
];

function AnonAvatar({ userHash }) {
  // Deterministic two-tone circle so parents can spot repeat events from
  // the same anon parent without knowing who they are.
  const hue = parseInt((userHash || "0").slice(0, 4), 16) % 360;
  return (
    <span
      className="shrink-0 h-8 w-8 rounded-full border border-white shadow-sm flex items-center justify-center text-white font-semibold text-[0.6875rem]"
      style={{
        background: `linear-gradient(135deg, hsl(${hue}, 45%, 45%), hsl(${(hue + 40) % 360}, 45%, 60%))`,
      }}
      aria-hidden
    >
      {(userHash || "").slice(0, 2).toUpperCase()}
    </span>
  );
}

export default function PublicMilestoneWall() {
  const [status, setStatus] = useState(null);   // {opt_in, my_events_this_month}
  const [feed, setFeed] = useState(null);       // {events, total, days, category, category_counts}
  const [category, setCategory] = useState("all");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (cat) => {
    try {
      const [s, f] = await Promise.all([
        api.get("/wall/status"),
        api.get("/wall/feed", { params: { days: 30, limit: 25, category: cat } }),
      ]);
      setStatus(s.data || null);
      setFeed(f.data || null);
    } catch (err) {
      logError("wall load failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(category);
  }, [load, category]);

  async function toggle() {
    if (!status) return;
    setBusy(true);
    try {
      const r = await api.post("/wall/opt-in", { opt_in: !status.opt_in });
      const nowOptedIn = !!r.data?.opt_in;
      setStatus((s) => ({ ...(s || {}), opt_in: nowOptedIn }));
      if (nowOptedIn) {
        toast.success(
          r.data?.backfilled_event
            ? "You're on the wall — your Foundation Ready badge is up now."
            : "You're on the wall — your next badge will appear here.",
        );
      } else {
        toast("Off the wall — new badges won't be shared.");
      }
      // Refresh feed after opt-in so a backfilled event shows up.
      // Reset filter to "all" — the backfilled badge may belong to a
      // sub-category the user hasn't selected, which would hide it.
      setCategory("all");
      const f = await api.get("/wall/feed", {
        params: { days: 30, limit: 25, category: "all" },
      });
      setFeed(f.data || null);
    } catch (err) {
      logError("wall toggle failed:", err);
      toast.error("Couldn't update your wall preference. Try again shortly.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleCheer(eventId) {
    try {
      const r = await api.post(`/wall/cheer/${eventId}`);
      const cheered = !!r.data?.cheered;
      const count = Number(r.data?.cheer_count ?? 0);
      setFeed((f) => {
        if (!f) return f;
        return {
          ...f,
          events: (f.events || []).map((ev) =>
            ev.event_id === eventId
              ? { ...ev, i_cheered: cheered, cheer_count: count }
              : ev,
          ),
        };
      });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(
        typeof detail === "string"
          ? detail
          : "Couldn't send a cheer. Try again shortly.",
      );
    }
  }

  if (loading) {
    return (
      <section
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 shadow-sm flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="wall-loading"
      >
        <Loader2 size={14} className="animate-spin" />
        Loading the community wall…
      </section>
    );
  }

  const events = feed?.events || [];
  const optIn = !!status?.opt_in;

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid="wall"
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] text-[#3D1A78] font-bold flex items-center gap-1.5">
            <Users size={12} /> Community wall
          </div>
          <h2
            className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1 leading-snug"
            data-testid="wall-headline"
          >
            {events.length === 0
              ? "Be the first parent on the wall this month."
              : `${feed.total} parent${feed.total === 1 ? "" : "s"} lit a milestone in the last ${feed.days} days.`}
          </h2>
          <p className="text-xs text-[#4B4567] mt-1 max-w-xl">
            Anonymised — names, emails, and stats are never shared.
          </p>
        </div>
        <button
          type="button"
          onClick={toggle}
          disabled={busy}
          data-testid="wall-toggle"
          data-opted-in={optIn ? "1" : "0"}
          className={`shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold transition-all ${
            optIn
              ? "bg-[#1F5C3B] text-white hover:brightness-110"
              : "border border-[#3D1A78] text-[#3D1A78] bg-white hover:bg-[#F5F1FB]"
          } ${busy ? "opacity-60 cursor-progress" : ""}`}
        >
          {busy ? (
            <Loader2 size={12} className="animate-spin" />
          ) : optIn ? (
            <ShieldCheck size={12} />
          ) : (
            <Sparkles size={12} />
          )}
          {optIn ? "On the wall — tap to opt out" : "Add my anonymous badge"}
        </button>
      </div>

      {/* Category filter chips — parents can zoom the feed to just
          streak-and-badge stories or a specific badge track. Renders
          only when there's at least one event across the whole feed
          (i.e. the all-count is non-zero). */}
      {(feed?.category_counts?.all || 0) > 0 && (
        <div
          className="mt-4 flex flex-wrap gap-1.5"
          data-testid="wall-category-chips"
          role="tablist"
          aria-label="Filter the wall feed"
        >
          {CATEGORY_CHIPS.map((c) => {
            const active = category === c.key;
            const count = feed?.category_counts?.[c.key] ?? 0;
            return (
              <button
                key={c.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setCategory(c.key)}
                data-testid={`wall-category-chip-${c.key}`}
                data-active={active ? "1" : "0"}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[0.6875rem] font-semibold border transition-all ${
                  active
                    ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                    : "bg-white text-[#3D1A78] border-[#D6CFE8] hover:bg-[#F5F1FB]"
                }`}
              >
                {c.label}
                <span
                  className={`inline-flex items-center justify-center min-w-[18px] px-1 rounded-full text-[0.625rem] tabular-nums ${
                    active
                      ? "bg-white/25 text-white"
                      : "bg-[#F1EEF7] text-[#4B4567]"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {(feed?.top_cheered || []).length > 0 && (
        <div
          className="mt-5 rounded-2xl border border-[#F1D9A0] bg-gradient-to-br from-[#FDF4E6] to-[#FBEDDA] p-4"
          data-testid="wall-top-cheered"
        >
          <div className="flex items-center gap-1.5 text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#8C5A2C]">
            <Heart size={12} className="fill-[#B23C3C] text-[#B23C3C]" />
            Most cheered this week
          </div>
          <ul className="mt-2 space-y-1.5">
            {feed.top_cheered.map((ev) => {
              const meta = BADGE_META[ev.badge_type] || {
                Icon: Award,
                iconClass: "text-[#3D1A78]",
              };
              const { Icon, iconClass } = meta;
              return (
                <li
                  key={ev.event_id}
                  className="flex items-center gap-2.5 text-sm text-[#1A1330]"
                  data-testid={`wall-top-cheered-item-${ev.event_id}`}
                >
                  <AnonAvatar userHash={ev.user_hash} />
                  <span className="flex-1 min-w-0 truncate">
                    A parent {ev.badge_label}
                  </span>
                  <span
                    className="shrink-0 inline-flex items-center gap-1 text-xs font-semibold text-[#B23C3C] px-2 py-0.5 rounded-full bg-white border border-[#EDD1D1]"
                    data-testid={`wall-top-cheered-count-${ev.event_id}`}
                  >
                    <Heart size={11} className="fill-[#B23C3C]" />
                    {ev.cheer_count}
                  </span>
                  <Icon size={14} className={iconClass} />
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {events.length === 0 ? (
        <div
          className="mt-5 rounded-2xl border border-dashed border-[#E5E0EE] bg-[#FCFBFE] p-5 text-sm text-[#4B4567] flex items-start gap-2"
          data-testid="wall-empty"
        >
          <Info size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
          <span>
            {category !== "all" ? (
              <>
                No {CATEGORY_CHIPS.find((c) => c.key === category)?.label.toLowerCase()} stories yet in the last 30 days.{" "}
                <button
                  type="button"
                  onClick={() => setCategory("all")}
                  className="underline text-[#3D1A78] font-semibold"
                  data-testid="wall-empty-clear-filter"
                >
                  Show everything
                </button>
                .
              </>
            ) : (
              <>
                Nothing here yet. Light your five milestones + opt in and your
                anonymous badge will appear on this wall for other parents to
                cheer on.
              </>
            )}
          </span>
        </div>
      ) : (
        <ul
          className="mt-5 space-y-2.5 max-h-96 overflow-y-auto pr-1"
          data-testid="wall-feed"
        >
          {events.map((ev) => {
            const meta = BADGE_META[ev.badge_type] || {
              accent: {
                bg: "bg-[#FCFBFE]",
                border: "border-[#EEE9F7]",
                text: "text-[#3D1A78]",
              },
              Icon: Award,
              iconClass: "text-[#3D1A78]",
            };
            const { accent, Icon, iconClass } = meta;
            const cheered = !!ev.i_cheered;
            const count = Number(ev.cheer_count || 0);
            return (
              <li
                key={ev.event_id}
                className={`flex items-start gap-3 rounded-2xl border ${accent.border} ${accent.bg} p-3.5`}
                data-testid={`wall-event-${ev.event_id}`}
              >
                <AnonAvatar userHash={ev.user_hash} />
                <div className="min-w-0 flex-1">
                  <div
                    className={`text-sm font-semibold leading-snug ${accent.text}`}
                  >
                    A parent {ev.badge_label}
                  </div>
                  <div className="text-xs text-[#4B4567] mt-0.5">
                    {ev.when_human}
                  </div>
                </div>
                <div className="shrink-0 flex items-center gap-2 mt-0.5">
                  <button
                    type="button"
                    onClick={() => toggleCheer(ev.event_id)}
                    disabled={!optIn}
                    title={
                      optIn
                        ? cheered ? "Take back your cheer" : "Send a one-tap cheer"
                        : "Opt in to the wall to cheer other parents"
                    }
                    data-testid={`wall-cheer-${ev.event_id}`}
                    data-cheered={cheered ? "1" : "0"}
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[0.6875rem] font-semibold border transition-all ${
                      cheered
                        ? "bg-[#FBEDED] border-[#EDD1D1] text-[#B23C3C]"
                        : "bg-white border-[#E5E0EE] text-[#3D1A78] hover:bg-[#F5F1FB]"
                    } ${!optIn ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
                  >
                    <Heart
                      size={12}
                      className={cheered ? "fill-[#B23C3C]" : ""}
                    />
                    <span data-testid={`wall-cheer-${ev.event_id}-count`}>
                      {count}
                    </span>
                  </button>
                  <Icon size={16} className={iconClass} />
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {!optIn && (
        <div
          className="mt-4 flex items-start gap-2 text-[0.6875rem] text-[#4B4567]"
          data-testid="wall-privacy-note"
        >
          <EyeOff size={12} className="shrink-0 mt-0.5" />
          <span>
            You&apos;re currently invisible to the wall. Nothing about you is
            recorded until you tap the button above.
          </span>
        </div>
      )}
    </section>
  );
}
