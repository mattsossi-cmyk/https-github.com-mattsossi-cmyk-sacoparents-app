import React, { useEffect, useState } from "react";
import { Navigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  Sparkles,
  RefreshCw,
  Loader2,
  AlertTriangle,
  TrendingUp,
  MessageSquare,
  CheckCircle2,
} from "lucide-react";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function CountStat({ label, value, hint }) {
  return (
    <div className="card-soft p-4">
      <div className="text-[10px] uppercase tracking-[0.15em] text-[#857E9C] font-bold">
        {label}
      </div>
      <div className="font-serif text-2xl text-[#1A1330] mt-1">{value}</div>
      {hint && <div className="text-[11px] text-[#857E9C] mt-1">{hint}</div>}
    </div>
  );
}

function Block({ icon: Icon, title, items, color, testid }) {
  return (
    <div className="card-soft p-6" data-testid={testid}>
      <div className="flex items-center gap-2.5 mb-4">
        <div className={`w-9 h-9 rounded-2xl grid place-items-center ${color.bg} ${color.fg}`}>
          <Icon size={16} />
        </div>
        <h3 className="font-serif text-lg text-[#1A1330]">{title}</h3>
      </div>
      {!items?.length ? (
        <div className="text-xs text-[#857E9C]">Nothing this week.</div>
      ) : (
        <ul className="space-y-2.5" data-testid={`${testid}-list`}>
          {items.map((item) => (
            <li
              key={item}
              className="flex items-start gap-2.5 text-sm text-[#1A1330]"
            >
              <span className={`w-1.5 h-1.5 rounded-full mt-2 shrink-0 ${color.dot}`} />
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function AdminInsights() {
  const { user, loading } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [regenerating, setRegenerating] = useState(false);

  const load = async () => {
    setErr(null);
    try {
      const r = await api.get("/insights/admin/weekly");
      setData(r.data);
    } catch (e) {
      logError("insights load failed", e);
      setErr(
        e?.response?.status === 403
          ? "forbidden"
          : e?.response?.data?.detail || "Could not load the weekly insights."
      );
    }
  };

  useEffect(() => {
    if (user) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const regenerate = async () => {
    setRegenerating(true);
    setErr(null);
    try {
      const r = await api.post("/insights/admin/weekly/regenerate");
      setData(r.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Could not regenerate insights.");
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (err === "forbidden") {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center max-w-lg mx-auto">
          <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
          <p className="text-sm text-[#4B4567] mt-2">
            Weekly insights are restricted to the SA CoParents owner.
          </p>
        </div>
      </AppShell>
    );
  }
  if (!data && !err) {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center">
          <Loader2 className="animate-spin w-6 h-6 mx-auto text-[#3D1A78]" />
          <p className="text-sm text-[#4B4567] mt-3">
            Building this week&apos;s briefing — this takes about 30 seconds the
            first time.
          </p>
        </div>
      </AppShell>
    );
  }
  if (err) {
    return (
      <AppShell>
        <div className="card-soft p-8 text-center">
          <p className="text-sm text-[#4B4567]">{err}</p>
        </div>
      </AppShell>
    );
  }

  const { briefing = {}, signals = {}, week_iso, generated_at } = data;
  const c = signals.counts || {};
  const concerning = briefing.concerning_patterns || [];

  return (
    <AppShell>
      <div className="fade-up space-y-8" data-testid="admin-insights">
        <Link
          to="/admin"
          className="inline-flex items-center gap-2 text-sm text-[#3D1A78] hover:underline"
          data-testid="admin-insights-back-link"
        >
          <ArrowLeft size={14} /> Back to admin
        </Link>

        <div className="card-soft p-7 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <div className="eyebrow mb-2">Weekly insights · {week_iso}</div>
              <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] flex items-center gap-3">
                <Sparkles className="text-[#3D1A78]" size={28} />
                Your 5-minute Monday read
              </h1>
              <p className="text-sm text-[#4B4567] mt-2 max-w-2xl leading-relaxed">
                A calm, honest narrative drawn from the past 7 days of survey
                responses, journal entries, sign-ups, and acknowledgments.
              </p>
              <div className="text-[11px] text-[#857E9C] mt-3">
                Last generated: {fmtDate(generated_at)}
              </div>
            </div>
            <button
              type="button"
              onClick={regenerate}
              disabled={regenerating}
              data-testid="admin-insights-regenerate-button"
              className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2c1158] disabled:opacity-60 shadow-sm"
            >
              {regenerating ? (
                <Loader2 className="animate-spin" size={14} />
              ) : (
                <RefreshCw size={14} />
              )}
              {regenerating ? "Regenerating…" : "Regenerate"}
            </button>
          </div>
        </div>

        {/* Headline */}
        {briefing.headline && (
          <div
            className="card-soft p-7 bg-gradient-to-br from-[#EFE9F9] to-[#E4F1F1]"
            data-testid="admin-insights-headline"
          >
            <div className="eyebrow mb-2">This week&apos;s read</div>
            <p className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug">
              {briefing.headline}
            </p>
          </div>
        )}

        {/* Counts at a glance */}
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
          <CountStat
            label="New signups"
            value={(c.new_users || 0) + (c.new_guests || 0)}
            hint={`${c.new_users || 0} accounts · ${c.new_guests || 0} guests`}
          />
          <CountStat label="Summaries generated" value={c.summaries_generated || 0} />
          <CountStat
            label="Survey responses"
            value={c.survey_responses || 0}
            hint={
              signals.nps?.avg != null
                ? `Avg NPS ${signals.nps.avg} / 10`
                : "No NPS yet"
            }
          />
          <CountStat
            label="Co-parent invites"
            value={c.invites_sent || 0}
            hint={`${c.invites_accepted || 0} accepted`}
          />
        </div>

        {/* Concerning patterns — only render if non-empty */}
        {concerning.length > 0 && (
          <div
            className="card-soft p-7 border-l-4 border-[#9A3A23] bg-[#FCE3DC]/60"
            data-testid="admin-insights-concerning"
          >
            <div className="flex items-start gap-3 mb-3">
              <AlertTriangle size={20} className="text-[#9A3A23] mt-1 shrink-0" />
              <div>
                <h3 className="font-serif text-lg text-[#1A1330]">
                  Worth a closer look
                </h3>
                <p className="text-xs text-[#9A3A23] mt-1">
                  Patterns the AI flagged for owner attention. Always your call —
                  this is a signal, not a verdict.
                </p>
              </div>
            </div>
            <ul className="space-y-2 mt-2">
              {concerning.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2.5 text-sm text-[#1A1330]"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[#9A3A23] mt-2 shrink-0" />
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-6">
          <Block
            icon={TrendingUp}
            title="Highlights"
            items={briefing.highlights || []}
            color={{
              bg: "bg-[#EFE9F9]",
              fg: "text-[#3D1A78]",
              dot: "bg-[#3D1A78]",
            }}
            testid="admin-insights-highlights"
          />
          <Block
            icon={MessageSquare}
            title="User voice themes"
            items={briefing.user_voice_themes || []}
            color={{
              bg: "bg-[#D5F2F2]",
              fg: "text-[#0E7A7A]",
              dot: "bg-[#2DB5B5]",
            }}
            testid="admin-insights-themes"
          />
        </div>

        <Block
          icon={CheckCircle2}
          title="Recommended actions this week"
          items={briefing.recommended_actions || []}
          color={{
            bg: "bg-[#FFF1E2]",
            fg: "text-[#B6663B]",
            dot: "bg-[#C28771]",
          }}
          testid="admin-insights-actions"
        />

        {briefing.closing_note && (
          <div className="card-soft p-6 text-center">
            <p className="font-serif text-base text-[#1A1330] italic">
              &ldquo;{briefing.closing_note}&rdquo;
            </p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
