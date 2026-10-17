/**
 * CostSplitterPanel.jsx — a lightweight ledger for kids' activity
 * costs (uniforms, camp fees, gear, transport).
 *
 * Mounted on `ActivitiesAlignment.jsx`. Each parent logs entries
 * against their own account; when a co-parent email is known, the
 * panel calls `/activities-costs/compare` to render a side-by-side
 * totals card. Free-text notes stay private — the compare endpoint
 * redacts the co-parent's notes to `null` before returning.
 *
 * Design principles (2026-03-06):
 *   - Never adjudicate "fair" — just show what each parent logged.
 *   - Totals + categories are visible; notes stay private.
 *   - Zero-state: an empty inline form so the parent can start
 *     without navigating.
 *   - Currency-aware: whatever code the parent enters is stored;
 *     the panel formats USD by default and falls back to the code
 *     for anything else.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  DollarSign,
  Download,
  Info,
  Loader2,
  Plus,
  Receipt,
} from "lucide-react";
import { toast } from "sonner";

import { api, API } from "../lib/api";
import { logError } from "../lib/logger";
import SplitSuggestion, { loadSplitPrefs } from "./SplitSuggestion";
import CostSplitterTotals from "./cost/CostSplitterTotals";
import CostSplitterCategoryBreakdown from "./cost/CostSplitterCategoryBreakdown";
import CostSplitterEntriesList from "./cost/CostSplitterEntriesList";

function formatMoney(cents, currency = "USD") {
  const n = (cents || 0) / 100;
  if (currency === "USD") {
    return n.toLocaleString(undefined, {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return `${n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${currency}`;
}

export default function CostSplitterPanel({ coparentEmail, coparentName }) {
  const [rows, setRows] = useState([]);
  const [totalCents, setTotalCents] = useState(0);
  const [categories, setCategories] = useState([]);
  const [compare, setCompare] = useState(null);
  const [loading, setLoading] = useState(true);

  const [form, setForm] = useState({
    activity_label: "",
    category: "sports",
    amount: "",
    incurred_on: "",
    note: "",
  });
  const [saving, setSaving] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const downloadPdf = useCallback(async () => {
    const prefs = loadSplitPrefs();
    const params = new URLSearchParams();
    if (coparentEmail) params.set("coparent_email", coparentEmail);
    params.set("mode", prefs.mode || "even");
    if (prefs.mode === "income") {
      // Backend expects cents.
      params.set("self_income", String(Math.round((prefs.selfIncome || 0) * 100)));
      params.set(
        "coparent_income",
        String(Math.round((prefs.coparentIncome || 0) * 100)),
      );
    }
    if (prefs.mode === "custom") {
      params.set("custom_pct", String(Math.round(prefs.customSelfPct || 50)));
    }
    setDownloadingPdf(true);
    try {
      const res = await fetch(
        `${API}/activities-costs/compare.pdf?${params.toString()}`,
        { credentials: "include" },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "activity-cost-ledger.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      logError("cost-splitter download-pdf", err);
      toast.error("Could not download the PDF right now.");
    } finally {
      setDownloadingPdf(false);
    }
  }, [coparentEmail]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const mine = await api.get("/activities-costs/mine");
      setRows(mine.data?.rows || []);
      setTotalCents(mine.data?.total_cents || 0);
      setCategories(mine.data?.categories || []);
      if (coparentEmail) {
        try {
          const cmp = await api.get(
            `/activities-costs/compare?coparent_email=${encodeURIComponent(coparentEmail)}`,
          );
          setCompare(cmp.data);
        } catch (err) {
          logError("cost-splitter compare", err);
          setCompare(null);
        }
      } else {
        setCompare(null);
      }
    } catch (err) {
      logError("cost-splitter load", err);
    } finally {
      setLoading(false);
    }
  }, [coparentEmail]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const submit = async (e) => {
    e?.preventDefault?.();
    const label = form.activity_label.trim();
    const amountNum = parseFloat(form.amount);
    if (!label) {
      toast.error("Add a short label (e.g. 'Soccer registration').");
      return;
    }
    if (!Number.isFinite(amountNum) || amountNum <= 0) {
      toast.error("Enter an amount greater than 0.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/activities-costs", {
        activity_label: label,
        category: form.category,
        amount_cents: Math.round(amountNum * 100),
        currency: "USD",
        incurred_on: form.incurred_on || undefined,
        note: form.note || undefined,
      });
      toast.success("Expense logged.");
      setForm({
        activity_label: "",
        category: form.category,
        amount: "",
        incurred_on: "",
        note: "",
      });
      await refresh();
    } catch (err) {
      logError("cost-splitter create", err);
      const detail = err?.response?.data?.detail || "Could not save that expense.";
      toast.error(detail);
    } finally {
      setSaving(false);
    }
  };

  const removeRow = async (cost_id) => {
    if (!window.confirm("Remove this entry?")) return;
    try {
      await api.delete(`/activities-costs/${cost_id}`);
      toast.success("Entry removed.");
      await refresh();
    } catch (err) {
      logError("cost-splitter delete", err);
      toast.error("Could not remove.");
    }
  };

  const selfTotal = compare?.self?.total_cents ?? totalCents;
  const coparentTotal = compare?.coparent?.total_cents ?? 0;
  const combinedTotal = compare?.combined_total_cents ?? selfTotal;
  const hasCompare = Boolean(compare);

  const perCategory = useMemo(() => {
    if (compare?.per_category_pair) return compare.per_category_pair;
    // Solo state — synthesize from `rows`.
    const map = new Map();
    rows.forEach((r) => {
      const key = r.category || "other";
      const existing = map.get(key) || {
        key,
        label: categories.find((c) => c.key === key)?.label || key,
        self_cents: 0,
        coparent_cents: 0,
      };
      existing.self_cents += r.amount_cents;
      map.set(key, existing);
    });
    return Array.from(map.values());
  }, [compare, rows, categories]);

  return (
    <div
      className="rounded-3xl border border-[#C7E5D3] bg-white p-6 sm:p-7"
      data-testid="cost-splitter-panel"
    >
      <div className="flex items-start gap-3 mb-4">
        <Receipt size={20} className="text-[#1E7A55] shrink-0 mt-1" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-serif text-xl text-[#1A1330] leading-tight">
              Cost splitter
            </h2>
            <span className="rounded-full bg-[#EEF7F1] text-[#1E7A55] px-2.5 py-0.5 text-[10px] uppercase tracking-[0.16em] font-bold">
              Beta
            </span>
          </div>
          <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
            Log what you&rsquo;ve paid toward the kids&rsquo; activities.
            When your co-parent has an account, you&rsquo;ll both see
            running totals side by side — private free-text notes stay
            just with you.
          </p>
        </div>
        {(selfTotal > 0 || coparentTotal > 0) && (
          <button
            type="button"
            onClick={downloadPdf}
            disabled={downloadingPdf}
            data-testid="cost-splitter-download-pdf"
            className="shrink-0 inline-flex items-center gap-1.5 rounded-full border border-[#1E7A55] text-[#1E7A55] px-3 py-1.5 text-xs font-semibold hover:bg-[#EEF7F1] disabled:opacity-60"
            title="Download a one-page PDF for your mediator"
          >
            {downloadingPdf ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Download size={12} />
            )}
            PDF
          </button>
        )}
      </div>

      {/* Totals card */}
      <CostSplitterTotals
        selfTotal={selfTotal}
        coparentTotal={coparentTotal}
        combinedTotal={combinedTotal}
        selfCount={compare?.self?.count ?? rows.length}
        coparentCount={compare?.coparent?.count ?? 0}
        hasCompare={hasCompare}
        coparentName={coparentName}
      />

      {/* Per-category breakdown */}
      <CostSplitterCategoryBreakdown
        perCategory={perCategory}
        hasCompare={hasCompare}
      />

      {/* Neutral split suggestion — deterministic math, never sent to
          the server. Renders whenever the parent has logged anything;
          waits for the pair to land before showing a real balance. */}
      {(selfTotal > 0 || coparentTotal > 0) && (
        <SplitSuggestion
          selfCents={selfTotal}
          coparentCents={coparentTotal}
          coparentName={coparentName}
          hasCompare={hasCompare}
        />
      )}

      {/* Log-entry form */}
      <form
        onSubmit={submit}
        className="rounded-2xl border border-[#C7E5D3] bg-[#F1F9F4] p-4 grid grid-cols-1 sm:grid-cols-6 gap-3"
        data-testid="cost-splitter-form"
      >
        <div className="sm:col-span-3">
          <label className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] block mb-1">
            Activity
          </label>
          <input
            type="text"
            value={form.activity_label}
            onChange={(e) => setForm({ ...form, activity_label: e.target.value })}
            placeholder="Soccer registration"
            data-testid="cost-splitter-input-label"
            className="w-full rounded-xl border border-[#C7E5D3] bg-white px-3 py-2 text-sm focus:outline-none focus:border-[#1E7A55]"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] block mb-1">
            Category
          </label>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            aria-label="Category"
            data-testid="cost-splitter-input-category"
            className="w-full rounded-xl border border-[#C7E5D3] bg-white px-3 py-2 text-sm focus:outline-none focus:border-[#1E7A55]"
          >
            {categories.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] block mb-1">
            Amount
          </label>
          <div className="relative">
            <DollarSign
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6E6787]"
            />
            <input
              type="number"
              inputMode="decimal"
              step="0.01"
              min="0"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              placeholder="0.00"
              data-testid="cost-splitter-input-amount"
              className="w-full pl-8 pr-3 py-2 rounded-xl border border-[#C7E5D3] bg-white text-sm focus:outline-none focus:border-[#1E7A55]"
            />
          </div>
        </div>
        <div className="sm:col-span-4">
          <label className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] block mb-1">
            Note (private to you)
          </label>
          <input
            type="text"
            value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })}
            placeholder="Optional — reference number, drop-off address, etc."
            data-testid="cost-splitter-input-note"
            className="w-full rounded-xl border border-[#C7E5D3] bg-white px-3 py-2 text-sm focus:outline-none focus:border-[#1E7A55]"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] block mb-1">
            Date
          </label>
          <input
            type="date"
            value={form.incurred_on}
            onChange={(e) => setForm({ ...form, incurred_on: e.target.value })}
            aria-label="Date"
            data-testid="cost-splitter-input-date"
            className="w-full rounded-xl border border-[#C7E5D3] bg-white px-3 py-2 text-sm focus:outline-none focus:border-[#1E7A55]"
          />
        </div>
        <div className="sm:col-span-6 flex flex-wrap items-center gap-3 justify-end">
          <p className="text-[11px] text-[#4B4567] flex items-center gap-1.5 mr-auto">
            <Info size={12} /> Free-text notes stay private. Totals + activity labels are visible to your co-parent.
          </p>
          <button
            type="submit"
            disabled={saving}
            data-testid="cost-splitter-submit"
            className="inline-flex items-center gap-2 rounded-full bg-[#1E7A55] text-white px-4 py-2 text-sm font-semibold hover:brightness-110 disabled:opacity-60"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Log expense
          </button>
        </div>
      </form>

      {/* Entries table (expandable) */}
      <CostSplitterEntriesList
        rows={rows}
        categories={categories}
        onRemove={removeRow}
      />

      {loading && (
        <div className="mt-3 text-xs text-[#4B4567] inline-flex items-center gap-1.5">
          <Loader2 size={12} className="animate-spin" /> Refreshing totals…
        </div>
      )}
    </div>
  );
}
