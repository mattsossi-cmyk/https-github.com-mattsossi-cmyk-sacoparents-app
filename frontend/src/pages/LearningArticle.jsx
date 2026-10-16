import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAiGuard } from "../components/aiNotice/AiGuard";
import {
  ArrowLeft, Clock, CheckCircle2, Circle, Loader2, Sparkles,
  RefreshCw, ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { logError } from "../lib/logger";

/**
 * LearningArticle — full read view with "mark as read" toggle and an
 * optional "Ask the coach for more depth" AI expansion (Claude via the
 * Emergent LLM key, cached per user per article).
 */
export default function LearningArticle() {
  const { hubSlug, articleSlug } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [coachLoading, setCoachLoading] = useState(false);
  const aiGuard = useAiGuard("summary");
  const [coach, setCoach] = useState(null);
  const [coachError, setCoachError] = useState(null);

  const path = `/learning/hub/${hubSlug}/article/${articleSlug}`;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get(path);
      setData(r.data || null);
      if (r.data?.ai_expansion) setCoach(r.data.ai_expansion);
    } catch (err) {
      logError("article load failed:", err);
      if (err?.response?.status === 404) {
        navigate("/learning");
      }
    } finally {
      setLoading(false);
    }
  }, [path, navigate]);

  useEffect(() => { load(); }, [load]);

  async function toggleRead() {
    if (!data?.article) return;
    setSaving(true);
    try {
      if (data.read) {
        await api.delete(`${path}/read`);
        setData((d) => ({ ...d, read: false, read_at: null }));
        toast.message("Marked as unread.");
      } else {
        const r = await api.post(`${path}/read`);
        setData((d) => ({ ...d, read: true, read_at: r?.data?.read_at }));
        toast.success("Marked as read. Nice.");
      }
    } catch (err) {
      logError("toggle read failed:", err);
      toast.error("Couldn't update. Try again in a moment.");
    } finally {
      setSaving(false);
    }
  }

  async function askCoach(force = false) {
    if (!(await aiGuard.confirmSend(""))) return;
    setCoachLoading(true);
    setCoachError(null);
    try {
      const r = await api.post(`${path}/coach`, { force });
      setCoach(r?.data?.expansion || null);
      if (!r?.data?.cached) toast.success("Coach expanded this read for you.");
    } catch (err) {
      logError("coach expansion failed:", err);
      const detail = err?.response?.data?.detail;
      setCoachError(
        typeof detail === "string"
          ? detail
          : "The coach is briefly unavailable. Try again in a moment.",
      );
    } finally {
      setCoachLoading(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-6 pb-16">
          <div
            className="flex items-center gap-2 text-sm text-[#4B4567]"
            data-testid="learning-article-loading"
          >
            <Loader2 size={14} className="animate-spin" /> Loading…
          </div>
        </div>
      </AppShell>
    );
  }
  if (!data?.article) return null;

  const article = data.article;
  const paragraphs = (article.body || "").split(/\n\s*\n/);

  return (
    <AppShell>
      <div
        className="max-w-3xl mx-auto px-4 sm:px-6 pt-6 pb-16"
        data-testid="learning-article-page"
      >
        <Link
          to="/learning"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline"
          data-testid="learning-article-back"
        >
          <ArrowLeft size={14} /> All reads
        </Link>

        <header className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
            {article.hub_name}
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl font-extrabold text-[#1A1330] mt-2 leading-tight">
            {article.title}
          </h1>
          <p className="text-lg text-[#4B4567] mt-3">{article.summary}</p>
          <div className="flex flex-wrap items-center gap-3 mt-4">
            <span className="inline-flex items-center gap-1.5 text-[11px] text-[#857E9C]">
              <Clock size={11} /> {article.read_minutes} min read
            </span>
            <button
              type="button"
              onClick={toggleRead}
              disabled={saving}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                data.read
                  ? "bg-[#F1F9F4] text-[#1F5C3B] border border-[#B5DFC5]"
                  : "bg-[#3D1A78] text-white hover:brightness-110"
              } ${saving ? "opacity-60 cursor-progress" : ""}`}
              data-testid="learning-article-read-toggle"
            >
              {saving ? (
                <Loader2 size={12} className="animate-spin" />
              ) : data.read ? (
                <CheckCircle2 size={12} />
              ) : (
                <Circle size={12} />
              )}
              {data.read ? "Read — tap to undo" : "Mark as read"}
            </button>
          </div>
        </header>

        <article
          className="prose prose-neutral max-w-none mt-8"
          data-testid="learning-article-body"
        >
          {paragraphs.map((p, i) => (
            <p
              key={`para-${i}-${(p || "").slice(0, 30)}`}
              className="text-[#1A1330] text-[17px] leading-[1.75] mb-5"
            >
              {p}
            </p>
          ))}
        </article>

        {article.takeaways?.length > 0 && (
          <section
            className="mt-8 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-5"
            data-testid="learning-article-takeaways"
          >
            <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
              3 things to try this week
            </div>
            <ul className="mt-3 space-y-2.5">
              {article.takeaways.map((t, i) => (
                <li
                  key={`takeaway-${i}-${(t || "").slice(0, 30)}`}
                  className="flex items-start gap-2.5 text-[15px] text-[#1A1330] leading-snug"
                >
                  <CheckCircle2
                    size={16}
                    className="shrink-0 mt-0.5 text-[#3D1A78]"
                  />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* AI expansion */}
        <section
          className="mt-8 rounded-2xl border border-[#E4D8B8] bg-[#FFF9EB] p-5"
          data-testid="learning-article-coach"
        >
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] text-[#8A6B12] font-bold">
              <Sparkles size={12} /> Ask the coach for more depth
            </div>
            {coach && !coachLoading && (
              <button
                type="button"
                onClick={() => askCoach(true)}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#8A6B12] hover:underline"
                data-testid="learning-coach-regenerate"
              >
                <RefreshCw size={11} /> Regenerate
              </button>
            )}
          </div>

          {!coach && !coachLoading && (
            <>
              <p className="text-sm text-[#6E5910] mt-2">
                Want a little more? A neutral AI coach will expand this read
                into three short paragraphs: an example, a common pitfall, and
                one practice to try this week.
              </p>
              <button
                type="button"
                onClick={() => askCoach(false)}
                className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold bg-[#8A6B12] text-white hover:brightness-110 transition-all"
                data-testid="learning-coach-ask"
              >
                <Sparkles size={12} /> Ask the coach
              </button>
            </>
          )}

          {coachLoading && (
            <div
              className="flex items-center gap-2 mt-3 text-sm text-[#6E5910]"
              data-testid="learning-coach-loading"
            >
              <Loader2 size={14} className="animate-spin" /> The coach is thinking…
            </div>
          )}

          {coachError && !coachLoading && (
            <div
              className="mt-3 text-sm text-[#B4223B]"
              data-testid="learning-coach-error"
            >
              {coachError}
              <button
                type="button"
                onClick={() => askCoach(false)}
                className="ml-2 underline text-[#8A6B12]"
              >
                Try again
              </button>
            </div>
          )}

          {coach && !coachLoading && (
            <div className="mt-4 space-y-4" data-testid="learning-coach-body">
              {coach.paragraphs?.map((p, i) => (
                <p
                  key={`coach-p-${i}-${(p || "").slice(0, 30)}`}
                  className="text-[15px] leading-[1.7] text-[#3B2A05]"
                >
                  {p}
                </p>
              ))}
            </div>
          )}
        </section>

        <div className="mt-10 flex items-center justify-between">
          <Link
            to="/learning"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] hover:underline"
            data-testid="learning-article-back-bottom"
          >
            <ArrowLeft size={14} /> Back to all reads
          </Link>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#4B4567] hover:text-[#3D1A78]"
          >
            Dashboard <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
