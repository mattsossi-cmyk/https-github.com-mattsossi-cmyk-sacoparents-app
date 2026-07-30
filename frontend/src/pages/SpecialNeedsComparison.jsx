/**
 * SpecialNeedsComparison.jsx — neutral side-by-side between the two parents'
 * SNC individual reports. Rendered from the cached comparison on the backend.
 *
 * Design guardrails:
 *   * Section 11 (Safety) is never shown here.
 *   * Verbatim narrative/open-text answers are never copied across.
 *   * Neither parent is labelled correct/incorrect.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  Loader2,
  ArrowLeft,
  RefreshCcw,
  Users,
  Handshake,
  Compass,
  HelpCircle,
  Info,
  ShieldOff,
} from "lucide-react";
import { logError } from "../lib/logger";

const BUCKET_LABELS = {
  agreement: "Where you agree",
  different_observations: "Where you see it differently",
  missing_information: "Where more information would help",
};

function BucketPill({ bucket }) {
  const map = {
    agreement: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
    different_observations: "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]",
    missing_information: "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${map[bucket] || map.missing_information}`}>
      {BUCKET_LABELS[bucket] || bucket}
    </span>
  );
}

function CategoryRow({ row, parents }) {
  const scoreOf = (side) =>
    side.score === null || side.score === undefined
      ? "—"
      : typeof side.score === "number"
      ? side.score.toFixed(2)
      : String(side.score);
  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-[1.4fr,1fr,1fr,auto] gap-3 items-center p-4 rounded-2xl border border-[#EEE9F7] bg-white"
      data-testid={`snc-cmp-cat-${row.id}`}
    >
      <div className="min-w-0">
        <div className="text-sm font-medium text-[#1A1330] truncate">{row.name}</div>
        <div className="text-xs text-[#4B4567] mt-0.5">{row.note}</div>
      </div>
      <div className="text-xs text-[#1A1330]">
        <div className="text-[10px] uppercase tracking-[0.16em] text-[#3D1A78] font-semibold">{parents.a.name}</div>
        <div className="mt-0.5">{row.a.classification} · <span className="text-[#4B4567]">Score {scoreOf(row.a)}</span></div>
      </div>
      <div className="text-xs text-[#1A1330]">
        <div className="text-[10px] uppercase tracking-[0.16em] text-[#3D1A78] font-semibold">{parents.b.name}</div>
        <div className="mt-0.5">{row.b.classification} · <span className="text-[#4B4567]">Score {scoreOf(row.b)}</span></div>
      </div>
      <div className="justify-self-start sm:justify-self-end">
        <BucketPill bucket={row.bucket} />
      </div>
    </div>
  );
}

function BulletList({ items = [], testId }) {
  if (!items || items.length === 0) return <div className="text-sm text-[#8471B3] italic">—</div>;
  return (
    <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1" data-testid={testId}>
      {items.map((it, i) => (
        <li key={`${i}-${String(it).slice(0, 40)}`}>{it}</li>
      ))}
    </ul>
  );
}

export default function SpecialNeedsComparison() {
  const { inviteId } = useParams();
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get(`/snc/comparison/${inviteId}`);
      setState({ loading: false, data: r.data, error: null });
    } catch (err) {
      logError("snc comparison load", err);
      setState({ loading: false, data: null, error: err?.response?.data?.detail || "Could not load comparison." });
    }
  }, [inviteId]);

  useEffect(() => { load(); }, [load]);

  const regenerate = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/snc/comparison/${inviteId}/regenerate`);
      setState({ loading: false, data: r.data, error: null });
      toast.success("Comparison refreshed.");
    } catch (err) {
      logError("snc comparison regen", err);
      toast.error(err?.response?.data?.detail || "Could not refresh.");
    } finally {
      setBusy(false);
    }
  };

  if (state.loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]">
          <Loader2 className="animate-spin inline" /> Loading comparison…
        </div>
      </AppShell>
    );
  }
  if (state.error) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10">
          <h1 className="font-serif text-3xl text-[#1A1330] mb-2">Comparison unavailable</h1>
          <p className="text-sm text-[#4B4567]">{state.error}</p>
          <Link to="/special-needs/invite" className="text-xs text-[#3D1A78] underline mt-4 inline-block">Back to invites</Link>
        </div>
      </AppShell>
    );
  }

  const data = state.data || {};
  if (!data.ready) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10" data-testid="snc-cmp-waiting">
          <Link to="/special-needs/invite" className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4">
            <ArrowLeft size={12} /> Back to invites
          </Link>
          <h1 className="font-serif text-3xl text-[#1A1330] mb-2">Waiting on both reports</h1>
          <div className="mt-4 rounded-3xl bg-white border border-[#E5E0EE] p-5 shadow-sm">
            <ul className="text-sm text-[#1A1330] space-y-2 list-disc pl-5">
              {data.missing?.a_report && (
                <li>Parent A hasn&apos;t generated their report yet.</li>
              )}
              {data.missing?.b_report && data.missing?.b_accepted && (
                <li>Your co-parent has accepted, but hasn&apos;t generated their report yet.</li>
              )}
              {!data.missing?.b_accepted && (
                <li>Your co-parent hasn&apos;t accepted the invite yet.</li>
              )}
            </ul>
          </div>
        </div>
      </AppShell>
    );
  }

  const cmp = data.comparison || {};
  const parents = cmp.parents || { a: { name: "Parent A" }, b: { name: "Parent B" } };
  const buckets = cmp.buckets || {};
  const categoriesById = Object.fromEntries((cmp.categories || []).map((c) => [c.id, c]));
  const generatedAt = data.generated_at;

  const renderBucketCategories = (bucketKey, testId) => {
    const ids = buckets[bucketKey] || [];
    if (ids.length === 0) {
      return <div className="text-sm text-[#8471B3] italic" data-testid={testId}>None in this bucket.</div>;
    }
    return (
      <div className="space-y-3" data-testid={testId}>
        {ids.map((id) => categoriesById[id]).filter(Boolean).map((row) => (
          <CategoryRow key={row.id} row={row} parents={parents} />
        ))}
      </div>
    );
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc-comparison-root">
        <Link to="/special-needs/invite" className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4">
          <ArrowLeft size={12} /> Back to invites
        </Link>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
          Neutral side-by-side
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          {parents.a.name} &amp; {parents.b.name}
        </h1>

        {/* Cache header */}
        <div className="mt-4 rounded-3xl border border-[#E5E0EE] p-4 sm:p-5 bg-white flex flex-wrap items-center justify-between gap-3 shadow-sm">
          <div className="text-xs text-[#4B4567]">
            Last generated {generatedAt ? new Date(generatedAt).toLocaleString() : "—"}.
          </div>
          <button
            onClick={regenerate}
            disabled={busy}
            data-testid="snc-cmp-regenerate"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60"
          >
            {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCcw size={13} />} Refresh
          </button>
        </div>

        {/* Safety notice */}
        <div className="mt-4 rounded-3xl border-2 border-[#F1BDA1] bg-white p-4 sm:p-5 text-sm text-[#1A1330] flex items-start gap-3" data-testid="snc-cmp-safety-notice">
          <ShieldOff className="text-[#C2481F] shrink-0 mt-0.5" size={20} />
          <div>{cmp.safety_notice}</div>
        </div>

        {/* Counts */}
        {cmp.counts && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6" data-testid="snc-cmp-counts">
            {[
              { key: "total_categories", label: "Categories compared", icon: Users },
              { key: "agreement", label: "Agreement", icon: Handshake },
              { key: "different_observations", label: "Different observations", icon: Compass },
              { key: "missing_information", label: "Missing info", icon: HelpCircle },
            ].map(({ key, label, icon: Icon }) => (
              <div key={key} className="bg-white rounded-2xl border border-[#E5E0EE] p-4 shadow-sm">
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-[#3D1A78] font-semibold">
                  <Icon size={14} /> {label}
                </div>
                <div className="mt-1 font-serif text-2xl text-[#1A1330]">{cmp.counts[key] ?? 0}</div>
              </div>
            ))}
          </div>
        )}

        {/* Buckets */}
        <section className="mt-8">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3 flex items-center gap-2">
            <Handshake size={20} className="text-[#3D1A78]" /> Where you agree
          </h2>
          {renderBucketCategories("agreement", "snc-cmp-agreement")}
        </section>

        <section className="mt-8">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3 flex items-center gap-2">
            <Compass size={20} className="text-[#8C5A2C]" /> Where you see it differently
          </h2>
          {renderBucketCategories("different_observations", "snc-cmp-different")}
        </section>

        <section className="mt-8">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3 flex items-center gap-2">
            <HelpCircle size={20} className="text-[#6E6E82]" /> Where more information would help
          </h2>
          {renderBucketCategories("missing_information", "snc-cmp-missing")}
        </section>

        <section className="mt-8 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3 flex items-center gap-2">
            <Info size={20} className="text-[#3D1A78]" /> Professional questions
          </h2>
          <BulletList items={buckets.professional_questions} testId="snc-cmp-professional" />
        </section>

        <section className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3 flex items-center gap-2">
            <Users size={20} className="text-[#3D1A78]" /> Practical coordination areas
          </h2>
          <BulletList items={buckets.coordination_areas} testId="snc-cmp-coordination" />
        </section>

        <div className="mt-8 text-xs text-[#8471B3] italic">{cmp.disclaimer}</div>
      </div>
    </AppShell>
  );
}
