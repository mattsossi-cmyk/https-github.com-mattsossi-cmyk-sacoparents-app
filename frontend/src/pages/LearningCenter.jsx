import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import {
  BookOpen, Clock, CheckCircle2, Circle, Loader2, ArrowRight,
} from "lucide-react";
import { logError } from "../lib/logger";

/**
 * LearningCenter — index page listing all three hubs and their short
 * reads. Small, scannable, non-blocking. No milestone impact — Learning
 * Center is deliberately its own space.
 */
export default function LearningCenter() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/learning/hubs");
      setData(r.data || null);
    } catch (err) {
      logError("hubs load failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-6 pb-16">
        <header className="mb-8" data-testid="learning-header">
          <div className="flex items-center gap-2 text-[0.625rem] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
            <BookOpen size={12} /> Learning center
          </div>
          <h1 className="font-serif text-4xl sm:text-5xl font-extrabold text-[#1A1330] mt-2 leading-tight">
            Short reads for the long haul.
          </h1>
          <p className="text-[#4B4567] text-base sm:text-lg mt-3 max-w-2xl">
            A small library on child-focused communication, healthy boundaries
            between two homes, and how to walk into mediation prepared. Each
            piece takes 2-3 minutes. Skim what draws you in.
          </p>
        </header>

        {loading && (
          <div
            className="flex items-center gap-2 text-sm text-[#4B4567]"
            data-testid="learning-hubs-loading"
          >
            <Loader2 size={14} className="animate-spin" /> Loading…
          </div>
        )}

        {!loading && data && (
          <div className="space-y-8" data-testid="learning-hubs">
            {data.hubs.map((hub) => (
              <HubSection key={hub.slug} hub={hub} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function HubSection({ hub }) {
  const complete = hub.progress.read === hub.progress.total && hub.progress.total > 0;
  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
      data-testid={`learning-hub-${hub.slug}`}
    >
      <div className="flex flex-wrap items-baseline gap-3">
        <span
          className="inline-block h-3 w-3 rounded-full mt-1.5"
          style={{ background: hub.accent }}
          aria-hidden
        />
        <div className="flex-1 min-w-[240px]">
          <h2 className="font-serif text-2xl font-extrabold text-[#1A1330]">
            {hub.name}
          </h2>
          <p className="text-sm text-[#4B4567] mt-1">{hub.tagline}</p>
        </div>
        <span
          className={`text-[0.6875rem] font-semibold px-2.5 py-1 rounded-full ${
            complete
              ? "bg-[#F1F9F4] text-[#1F5C3B] border border-[#B5DFC5]"
              : "bg-[#F5F1FB] text-[#3D1A78] border border-[#E5E0EE]"
          }`}
          data-testid={`learning-hub-${hub.slug}-progress`}
        >
          {hub.progress.read} / {hub.progress.total} read
        </span>
      </div>

      <ul className="mt-5 divide-y divide-[#F1EEF7]">
        {hub.articles.map((a) => (
          <li key={a.slug}>
            <Link
              to={`/learning/${hub.slug}/${a.slug}`}
              className="group flex items-start gap-3 py-3 sm:py-4 hover:bg-[#FCFBFE] rounded-xl px-2 -mx-2 transition-colors"
              data-testid={`learning-article-${a.slug}`}
            >
              <div className="shrink-0 mt-0.5">
                {a.read ? (
                  <CheckCircle2 size={16} className="text-[#1F5C3B]" />
                ) : (
                  <Circle size={16} className="text-[#C7BFDA]" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-[#1A1330] text-base leading-snug group-hover:text-[#3D1A78]">
                  {a.title}
                </div>
                <div className="text-sm text-[#4B4567] mt-0.5">{a.summary}</div>
                <div className="flex items-center gap-2 mt-1.5 text-[0.6875rem] text-[#6E6787]">
                  <Clock size={11} /> {a.read_minutes} min read
                  {a.read && (
                    <span className="text-[#1F5C3B]">· read</span>
                  )}
                </div>
              </div>
              <ArrowRight
                size={16}
                className="shrink-0 text-[#C7BFDA] group-hover:text-[#3D1A78] mt-1"
              />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
