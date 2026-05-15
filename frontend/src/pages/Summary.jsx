import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api, API } from "../lib/api";
import { toast } from "sonner";
import { logError } from "../lib/logger";
import {
  Sparkles,
  Download,
  RefreshCw,
  FileText,
  Handshake,
  MessageSquare,
  Mail,
  X,
  Lightbulb,
  TrendingUp,
  PenSquare,
} from "lucide-react";

/* ------------------------------ shared bits ------------------------------ */

function ChangesSinceLast({ text }) {
  if (!text || !text.trim()) return null;
  return (
    <div
      className="rounded-2xl bg-[#D6A374]/10 border border-[#D6A374]/25 px-5 py-4 mb-6"
      data-testid="changes-since-last"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="w-7 h-7 rounded-full bg-[#D6A374]/20 text-[#A26852] grid place-items-center">
          <TrendingUp size={14} />
        </span>
        <div className="text-xs uppercase tracking-[0.2em] text-[#A26852]">
          What's changed since last time
        </div>
      </div>
      <p className="text-sm text-[#2A3631] leading-relaxed whitespace-pre-line">{text}</p>
    </div>
  );
}

function RetakeButton() {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate("/dashboard")}
      className="btn-soft inline-flex items-center gap-2"
      data-testid="retake-assessments-button"
      title="Update your prep answers and re-generate to track your growth"
    >
      <PenSquare size={14} />
      Retake assessments
    </button>
  );
}

function Section({ title, children }) {
  return (
    <div className="py-4 border-t border-[#E8ECE9] first:border-t-0 first:pt-0">
      <div className="eyebrow mb-2">{title}</div>
      {children}
    </div>
  );
}

function BulletList({ items }) {
  if (!items || !items.length)
    return <p className="text-sm italic text-[#8A9A92]">(none captured)</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((s) => (
        <li key={s} className="flex gap-2 text-[#2A3631]">
          <span className="text-[#849D8E] mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-[#849D8E]" />
          <span>{s}</span>
        </li>
      ))}
    </ul>
  );
}

function ClauseList({ items }) {
  if (!items || !items.length)
    return <p className="text-sm italic text-[#8A9A92]">(none captured)</p>;
  return (
    <div className="space-y-3">
      {items.map((it, i) => (
        <div key={`${it.area}-${i}`} className="rounded-xl bg-[#F5F3E9] px-4 py-3">
          <div className="text-xs uppercase tracking-[0.2em] text-[#849D8E] mb-1">
            {it.area}
          </div>
          <div className="text-[#2A3631] leading-relaxed">{it.agreement}</div>
        </div>
      ))}
    </div>
  );
}

function PriorityAgenda({ items }) {
  if (!items?.length)
    return <p className="text-sm italic text-[#8A9A92]">(none captured)</p>;
  return (
    <ol className="space-y-2 list-none">
      {items.map((it, i) => (
        <li key={`${it.rank || i}-${it.topic}`} className="flex gap-3">
          <span className="font-serif text-xl text-[#849D8E] w-7 shrink-0">
            {it.rank || i + 1}.
          </span>
          <div>
            <div className="text-[#2A3631]">{it.topic}</div>
            <div className="text-xs text-[#8A9A92] uppercase tracking-wider">
              {it.category}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

async function downloadBlob(url, filename) {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.text()).slice(0, 120);
    } catch (e) {
      logError("downloadBlob: failed to read error body", e);
    }
    throw new Error(`HTTP ${res.status}${detail ? ` - ${detail}` : ""}`);
  }
  const blob = await res.blob();
  if (!blob || blob.size === 0) {
    throw new Error("Empty PDF response");
  }
  const objUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(objUrl);
}

/* ----------------------------- Mediation Tab ----------------------------- */

function MediationSummaryTab() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [history, setHistory] = useState([]);
  const [emailOpen, setEmailOpen] = useState(false);
  const [latestAgreementId, setLatestAgreementId] = useState(null);

  const loadHistory = useCallback(async () => {
    try {
      const r = await api.get("/mediation/summaries");
      const list = r.data || [];
      setHistory(list);
      setSummary((prev) => prev || list[0] || null);
    } catch (err) {
      logError("Failed to load summaries:", err);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Surface the latest agreement so the email dialog can optionally attach it.
  useEffect(() => {
    api
      .get("/mediation/agreements")
      .then((r) => setLatestAgreementId((r.data || [])[0]?.agreement_id || null))
      .catch(() => {});
  }, []);

  const generate = async () => {
    setLoading(true);
    try {
      const r = await api.post("/mediation/summary");
      setSummary(r.data);
      toast.success("Summary ready.");
      loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not generate summary.");
    } finally {
      setLoading(false);
    }
  };

  const download = async () => {
    if (!summary?.summary_id) {
      toast.error("No summary loaded. Please generate one first.");
      return;
    }
    setDownloading(true);
    try {
      await downloadBlob(
        `${API}/mediation/summary/${summary.summary_id}/pdf`,
        `mediation-summary-${summary.summary_id}.pdf`
      );
    } catch (err) {
      logError("PDF download failed:", err);
      toast.error(`Could not download PDF. ${err?.message || ""}`.trim());
    } finally {
      setDownloading(false);
    }
  };

  const shareText = async () => {
    if (!summary?.summary_id) {
      toast.error("No summary loaded. Please generate one first.");
      return;
    }
    try {
      const r = await shareViaText(
        "summary",
        `/mediation/summary/${summary.summary_id}/share-link`,
        "Mediation Summary"
      );
      if (r.mode === "clipboard") {
        toast.success("Link copied. Paste it into your text message.");
      }
    } catch (err) {
      logError("Share link failed:", err);
      toast.error("Could not create share link.");
    }
  };

  if (!summary) {
    return (
      <EmptyState
        icon={<Sparkles size={20} />}
        title="Generate your mediation summary"
        body="We'll synthesize your goals, concerns, priority agenda, communication style, and readiness into a single mediator-ready document."
        cta={loading ? "Synthesizing…" : "Generate summary"}
        onCta={generate}
        loading={loading}
        testId="summary-generate-button"
      />
    );
  }

  return (
    <div className="space-y-6" data-testid="summary-card">
      <div className="card-soft p-8">
        <HeaderRow
          eyebrow="Readiness"
          title={
            <>
              {summary.readiness_label}{" "}
              <span className="text-[#8A9A92] text-base">
                · {summary.readiness_score}/100
              </span>
            </>
          }
          onRegenerate={generate}
          onDownload={download}
          onShare={shareText}
          onEmail={() => setEmailOpen(true)}
          loading={loading}
          downloading={downloading}
          regenerateTestId="summary-regenerate-button"
          downloadTestId="summary-download-button"
          shareTestId="summary-share-button"
          emailTestId="summary-email-button"
        />

        <ChangesSinceLast text={summary.changes_since_last} />

        <Section title="Child-centered goals">
          <p className="text-[#2A3631] leading-relaxed">
            {summary.child_goals_summary}
          </p>
        </Section>
        <Section title="Top concerns">
          <BulletList items={summary.top_concerns} />
        </Section>
        <Section title="Priority agenda">
          <PriorityAgenda items={summary.priority_agenda} />
        </Section>
        <Section title="Flexibility areas">
          <BulletList items={summary.flexibility_areas} />
        </Section>
        <Section title="Communication goals">
          <BulletList items={summary.communication_goals} />
        </Section>
        <Section title="Notes for the mediator">
          <p className="text-[#2A3631] leading-relaxed italic">
            {summary.notes_for_mediator}
          </p>
        </Section>
      </div>

      {history.length > 1 && (
        <HistoryList
          items={history}
          activeId={summary.summary_id}
          labelKey="readiness_label"
          idKey="summary_id"
          onSelect={setSummary}
        />
      )}
      <EmailMediatorDialog
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        summaryId={summary?.summary_id}
        agreementId={latestAgreementId}
        defaultDoc="summary"
      />
    </div>
  );
}

/* ----------------------------- Agreement Tab ----------------------------- */

function AgreementDraftTab() {
  const [agreement, setAgreement] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [history, setHistory] = useState([]);
  const [emailOpen, setEmailOpen] = useState(false);
  const [latestSummaryId, setLatestSummaryId] = useState(null);

  const loadHistory = useCallback(async () => {
    try {
      const r = await api.get("/mediation/agreements");
      const list = r.data || [];
      setHistory(list);
      setAgreement((prev) => prev || list[0] || null);
    } catch (err) {
      logError("Failed to load agreements:", err);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Surface the latest summary so the email dialog can optionally attach it.
  useEffect(() => {
    api
      .get("/mediation/summaries")
      .then((r) => setLatestSummaryId((r.data || [])[0]?.summary_id || null))
      .catch(() => {});
  }, []);

  const generate = async () => {
    setLoading(true);
    try {
      const r = await api.post("/mediation/agreement");
      setAgreement(r.data);
      toast.success("Draft ready.");
      loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not generate draft.");
    } finally {
      setLoading(false);
    }
  };

  const download = async () => {
    if (!agreement?.agreement_id) {
      toast.error("No draft loaded. Please generate one first.");
      return;
    }
    setDownloading(true);
    try {
      await downloadBlob(
        `${API}/mediation/agreement/${agreement.agreement_id}/pdf`,
        `coparenting-agreement-${agreement.agreement_id}.pdf`
      );
    } catch (err) {
      logError("PDF download failed:", err);
      toast.error(`Could not download PDF. ${err?.message || ""}`.trim());
    } finally {
      setDownloading(false);
    }
  };

  const shareText = async () => {
    if (!agreement?.agreement_id) {
      toast.error("No draft loaded. Please generate one first.");
      return;
    }
    try {
      const r = await shareViaText(
        "agreement",
        `/mediation/agreement/${agreement.agreement_id}/share-link`,
        "Co-Parenting Agreement Draft"
      );
      if (r.mode === "clipboard") {
        toast.success("Link copied. Paste it into your text message.");
      }
    } catch (err) {
      logError("Share link failed:", err);
      toast.error("Could not create share link.");
    }
  };

  if (!agreement) {
    return (
      <EmptyState
        icon={<Handshake size={20} />}
        title="Draft your co-parenting agreement"
        body="A neutral, child-centered draft based on your captured goals, concerns, and priorities. Bring it to your co-parent or mediator as a starting point — not a legal document."
        cta={loading ? "Drafting…" : "Generate draft"}
        onCta={generate}
        loading={loading}
        testId="agreement-generate-button"
      />
    );
  }

  return (
    <div className="space-y-6" data-testid="agreement-card">
      <div className="card-soft p-8">
        <HeaderRow
          eyebrow="Draft"
          title="Co-Parenting Agreement"
          onRegenerate={generate}
          onDownload={download}
          onShare={shareText}
          onEmail={() => setEmailOpen(true)}
          loading={loading}
          downloading={downloading}
          regenerateTestId="agreement-regenerate-button"
          downloadTestId="agreement-download-button"
          shareTestId="agreement-share-button"
          emailTestId="agreement-email-button"
        />

        <ChangesSinceLast text={agreement.changes_since_last} />

        {agreement.overview && (
          <Section title="Overview">
            <p className="text-[#2A3631] leading-relaxed italic">
              {agreement.overview}
            </p>
          </Section>
        )}
        <Section title="Shared goals for our child">
          <BulletList items={agreement.shared_goals} />
        </Section>
        <Section title="Communication">
          <ClauseList items={agreement.communication} />
        </Section>
        <Section title="Child needs">
          <ClauseList items={agreement.child_needs} />
        </Section>
        <Section title="Household rules">
          <ClauseList items={agreement.household_rules} />
        </Section>
        <Section title="Priority topics to discuss">
          <PriorityAgenda items={agreement.priority_items} />
        </Section>
        {agreement.open_for_discussion?.length > 0 && (
          <Section title="Open for discussion">
            <BulletList items={agreement.open_for_discussion} />
          </Section>
        )}
        {agreement.closing_note && (
          <Section title="A note from the draft">
            <p className="text-[#2A3631] leading-relaxed italic">
              {agreement.closing_note}
            </p>
          </Section>
        )}

        <div className="mt-6 rounded-xl bg-[#C28771]/8 border border-[#C28771]/25 px-4 py-3 text-xs text-[#5C6B64]">
          This is a working draft to start a conversation — not a legal document.
          Review it together with your co-parent and, when ready, with a mediator or
          attorney.
        </div>
      </div>

      {history.length > 1 && (
        <HistoryList
          items={history}
          activeId={agreement.agreement_id}
          labelKey="closing_note"
          idKey="agreement_id"
          onSelect={setAgreement}
        />
      )}
      <EmailMediatorDialog
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        summaryId={latestSummaryId}
        agreementId={agreement?.agreement_id}
        defaultDoc="agreement"
      />
    </div>
  );
}


/* ----------------------- Things I Can Improve On Tab ----------------------- */

function ImprovementPlanTab() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const loadHistory = useCallback(async () => {
    try {
      const r = await api.get("/mediation/improvement-plans");
      const list = r.data || [];
      setHistory(list);
      setPlan((prev) => prev || list[0] || null);
    } catch (err) {
      logError("Failed to load improvement plans:", err);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const generate = async () => {
    setLoading(true);
    try {
      const r = await api.post("/mediation/improvement-plan");
      setPlan(r.data);
      toast.success("Your growth plan is ready.");
      loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not generate plan.");
    } finally {
      setLoading(false);
    }
  };

  if (!plan) {
    return (
      <EmptyState
        icon={<Lightbulb size={20} />}
        title="Build your personal growth plan"
        body="Using your Communication and Readiness responses, we'll compile a short, specific action plan with tips for both your everyday quality of life and the quality of your communication with your co-parent."
        cta={loading ? "Compiling…" : "Generate my plan"}
        onCta={generate}
        loading={loading}
        testId="improve-generate-button"
      />
    );
  }

  return (
    <div className="space-y-6" data-testid="improve-card">
      <div className="card-soft p-8">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <div className="eyebrow mb-1">Things I can improve on</div>
            <div className="font-serif text-2xl text-[#2A3631] leading-snug max-w-2xl">
              {plan.headline}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <RetakeButton />
            <button
              onClick={generate}
              className="btn-soft inline-flex items-center gap-2"
              disabled={loading}
              data-testid="improve-regenerate-button"
            >
              <RefreshCw size={14} />
              {loading ? "Working…" : "Regenerate"}
            </button>
          </div>
        </div>

        <ChangesSinceLast text={plan.changes_since_last} />

        {(plan.focus_areas || []).length === 0 && (
          <div className="rounded-2xl bg-[#F5F3E9] px-5 py-4 text-sm text-[#5C6B64]">
            We didn't have enough Communication or Readiness data to compile growth
            areas. Revisit those steps and try again.
          </div>
        )}

        <div className="space-y-5">
          {(plan.focus_areas || []).map((fa, i) => (
            <FocusAreaCard key={`${fa.title}-${i}`} fa={fa} index={i} />
          ))}
        </div>

        {plan.this_week?.length > 0 && (
          <div className="mt-8 rounded-2xl bg-[#849D8E]/8 border border-[#849D8E]/25 p-6">
            <div className="eyebrow mb-3">Try this week</div>
            <ol className="space-y-2 list-none">
              {plan.this_week.map((t, i) => (
                <li key={`${t}-${i}`} className="flex gap-3 text-[#2A3631]">
                  <span className="font-serif text-xl text-[#5C7A6A] w-6 shrink-0">
                    {i + 1}.
                  </span>
                  <span>{t}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {plan.encouragement && (
          <div className="mt-6 text-center px-2">
            <p className="font-serif text-lg text-[#5C7A6A] italic leading-snug">
              {plan.encouragement}
            </p>
          </div>
        )}
      </div>

      {history.length > 1 && (
        <HistoryList
          items={history}
          activeId={plan.plan_id}
          labelKey="headline"
          idKey="plan_id"
          onSelect={setPlan}
        />
      )}
    </div>
  );
}

function FocusAreaCard({ fa, index }) {
  return (
    <div
      className="rounded-2xl bg-[#F5F3E9] p-5 sm:p-6"
      data-testid={`improve-focus-${index}`}
    >
      <div className="flex items-start gap-3 mb-3">
        <span className="font-serif text-xl text-[#849D8E] shrink-0 leading-none mt-0.5">
          {index + 1}.
        </span>
        <div>
          <div className="font-serif text-xl text-[#2A3631] leading-snug">
            {fa.title}
          </div>
          {fa.why_it_matters && (
            <p className="text-sm text-[#5C6B64] mt-1.5">{fa.why_it_matters}</p>
          )}
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-4 sm:gap-5 mt-4">
        <TipBlock
          eyebrow="Communication"
          accent="#849D8E"
          tips={fa.communication_tips}
        />
        <TipBlock
          eyebrow="Quality of life"
          accent="#D6A374"
          tips={fa.quality_of_life_tips}
        />
      </div>
    </div>
  );
}

function TipBlock({ eyebrow, accent, tips }) {
  if (!tips?.length) return null;
  return (
    <div>
      <div
        className="text-[10px] uppercase tracking-[0.2em] mb-2"
        style={{ color: accent }}
      >
        {eyebrow}
      </div>
      <ul className="space-y-1.5">
        {tips.map((t, i) => (
          <li key={`${t}-${i}`} className="flex gap-2 text-sm text-[#2A3631]">
            <span
              className="w-1.5 h-1.5 rounded-full mt-2 shrink-0"
              style={{ background: accent }}
            />
            <span>{t}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}


/* -------------------------- shared sub-components ------------------------ */

function EmptyState({ icon, title, body, cta, onCta, loading, testId }) {
  return (
    <div className="card-soft p-10 text-center">
      <div className="w-14 h-14 rounded-full bg-[#849D8E]/15 text-[#849D8E] grid place-items-center mx-auto mb-4">
        {icon}
      </div>
      <div className="font-serif text-2xl text-[#2A3631] mb-2">{title}</div>
      <p className="text-[#5C6B64] mb-6 max-w-xl mx-auto">{body}</p>
      <button
        onClick={onCta}
        disabled={loading}
        className="btn-sage inline-flex items-center gap-2"
        data-testid={testId}
      >
        <Sparkles size={16} />
        {cta}
      </button>
    </div>
  );
}

function HeaderRow({
  eyebrow,
  title,
  onRegenerate,
  onDownload,
  onShare,
  onEmail,
  loading,
  downloading,
  regenerateTestId,
  downloadTestId,
  shareTestId,
  emailTestId,
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center sm:justify-between gap-3 mb-6">
      <div>
        <div className="eyebrow mb-1">{eyebrow}</div>
        <div className="font-serif text-2xl text-[#2A3631]">{title}</div>
      </div>
      <div className="grid grid-cols-2 sm:flex sm:flex-wrap items-stretch sm:items-center gap-2">
        <RetakeButton />
        <button
          onClick={onRegenerate}
          className="btn-soft inline-flex items-center justify-center gap-2 min-h-[44px]"
          disabled={loading || downloading}
          data-testid={regenerateTestId}
        >
          <RefreshCw size={14} />
          {loading ? "Working…" : "Regenerate"}
        </button>
        {onShare && (
          <button
            onClick={onShare}
            className="btn-soft inline-flex items-center justify-center gap-2 min-h-[44px]"
            disabled={loading || downloading}
            data-testid={shareTestId}
            title="Share a 7-day download link via text message"
          >
            <MessageSquare size={14} />
            Share via text
          </button>
        )}
        {onEmail && (
          <button
            onClick={onEmail}
            className="btn-soft inline-flex items-center justify-center gap-2 min-h-[44px]"
            disabled={loading || downloading}
            data-testid={emailTestId}
            title="Email this document directly to your mediator"
          >
            <Mail size={14} />
            Email to mediator
          </button>
        )}
        <button
          onClick={onDownload}
          className="btn-sage inline-flex items-center justify-center gap-2 min-h-[44px] col-span-2 sm:col-span-1"
          disabled={downloading || loading}
          data-testid={downloadTestId}
        >
          <Download size={16} />
          {downloading ? "Downloading…" : "Download PDF"}
        </button>
      </div>
    </div>
  );
}

function HistoryList({ items, activeId, labelKey, idKey, onSelect }) {
  return (
    <div className="card-soft p-6">
      <div className="eyebrow mb-3">Previous versions</div>
      <div className="space-y-2">
        {items.slice(0, 8).map((h) => (
          <button
            key={h[idKey]}
            onClick={() => onSelect(h)}
            disabled={h[idKey] === activeId}
            className={`w-full text-left rounded-xl px-4 py-3 text-sm flex items-center justify-between transition-colors ${
              h[idKey] === activeId
                ? "bg-[#849D8E]/15 text-[#2A3631] ring-1 ring-[#849D8E]/30"
                : "bg-[#F5F3E9] hover:bg-[#E8ECE9] text-[#2A3631]"
            }`}
            data-testid={`history-${h[idKey]}`}
          >
            <span className="truncate max-w-[70%]">
              {h[labelKey] || "Untitled"}
            </span>
            <span className="text-[#8A9A92] shrink-0">
              {new Date(h.generated_at).toLocaleString()}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ------------------------- Email to Mediator dialog ----------------------- */

function EmailMediatorDialog({ open, onClose, summaryId, agreementId, defaultDoc }) {
  const [mediatorEmail, setMediatorEmail] = useState("");
  const [mediatorName, setMediatorName] = useState("");
  const [includeSummary, setIncludeSummary] = useState(defaultDoc === "summary" && !!summaryId);
  const [includeAgreement, setIncludeAgreement] = useState(defaultDoc === "agreement" && !!agreementId);
  const [sending, setSending] = useState(false);
  const [configured, setConfigured] = useState(true);

  useEffect(() => {
    if (open) {
      setMediatorEmail("");
      setMediatorName("");
      setIncludeSummary(defaultDoc === "summary" && !!summaryId);
      setIncludeAgreement(defaultDoc === "agreement" && !!agreementId);
      api
        .get("/mediation/email/status")
        .then((r) => setConfigured(!!r.data?.configured))
        .catch(() => setConfigured(true));
    }
  }, [open, defaultDoc, summaryId, agreementId]);

  if (!open) return null;

  const canSend =
    !sending &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mediatorEmail.trim()) &&
    (includeSummary || includeAgreement);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!canSend) return;
    setSending(true);
    try {
      const payload = { mediator_email: mediatorEmail.trim() };
      if (mediatorName.trim()) payload.mediator_name = mediatorName.trim();
      if (includeSummary && summaryId) payload.summary_id = summaryId;
      if (includeAgreement && agreementId) payload.agreement_id = agreementId;
      const r = await api.post("/mediation/email-mediator", payload);
      toast.success(`Sent to ${r.data.sent_to}.`);
      onClose();
    } catch (err) {
      logError("Email to mediator failed:", err);
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Could not send email. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#2A3631]/40 backdrop-blur-sm"
      onClick={onClose}
      data-testid="email-mediator-dialog"
    >
      <form
        onSubmit={onSubmit}
        onClick={(e) => e.stopPropagation()}
        className="bg-[#FDFAF3] rounded-2xl shadow-xl w-full max-w-md border border-[#E8ECE9] overflow-hidden"
      >
        <div className="px-6 pt-6 pb-2 flex items-start justify-between gap-4">
          <div>
            <div className="w-10 h-10 rounded-full bg-[#849D8E]/15 text-[#5C7A6A] grid place-items-center mb-3">
              <Mail size={18} />
            </div>
            <div className="font-serif text-2xl text-[#2A3631] leading-tight">
              Email to your mediator
            </div>
            <p className="text-sm text-[#5C6B64] mt-1">
              We'll attach your selected PDF(s) with a short cover note. Replies
              go straight to your inbox.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#8A9A92] hover:text-[#2A3631] -mr-1 -mt-1 p-1"
            aria-label="Close"
            data-testid="email-mediator-close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {!configured && (
            <div
              className="rounded-xl bg-[#C28771]/10 border border-[#C28771]/25 px-4 py-3 text-sm text-[#5C6B64]"
              data-testid="email-mediator-not-configured"
            >
              Email sending isn't fully set up on this account yet. You can still
              fill in the form — but sending will fail until the administrator
              completes the SMTP setup in <code className="text-xs">backend/.env</code>.
            </div>
          )}
          <div>
            <label
              htmlFor="mediator-email"
              className="block text-xs uppercase tracking-[0.2em] text-[#8A9A92] mb-1.5"
            >
              Mediator's email
            </label>
            <input
              id="mediator-email"
              type="email"
              required
              autoFocus
              className="input-soft w-full"
              placeholder="mediator@example.com"
              value={mediatorEmail}
              onChange={(e) => setMediatorEmail(e.target.value)}
              data-testid="email-mediator-email-input"
            />
          </div>

          <div>
            <label
              htmlFor="mediator-name"
              className="block text-xs uppercase tracking-[0.2em] text-[#8A9A92] mb-1.5"
            >
              Mediator's name (optional)
            </label>
            <input
              id="mediator-name"
              type="text"
              className="input-soft w-full"
              placeholder="e.g., Maria Lopez"
              value={mediatorName}
              onChange={(e) => setMediatorName(e.target.value)}
              data-testid="email-mediator-name-input"
            />
          </div>

          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-[#8A9A92] mb-2">
              Attach
            </div>
            <div className="space-y-2">
              <DocCheckbox
                checked={includeSummary}
                disabled={!summaryId}
                onChange={setIncludeSummary}
                label="Mediation Summary"
                hint={!summaryId ? "Generate one first to include it" : "PDF — your prep at a glance"}
                testId="email-mediator-check-summary"
              />
              <DocCheckbox
                checked={includeAgreement}
                disabled={!agreementId}
                onChange={setIncludeAgreement}
                label="Co-Parenting Agreement Draft"
                hint={!agreementId ? "Generate one first to include it" : "PDF — neutral starter agreement"}
                testId="email-mediator-check-agreement"
              />
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-[#F5F3E9] flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="btn-soft"
            disabled={sending}
            data-testid="email-mediator-cancel"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canSend}
            className="btn-sage inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="email-mediator-send"
          >
            <Mail size={14} />
            {sending ? "Sending…" : "Send email"}
          </button>
        </div>
      </form>
    </div>
  );
}

function DocCheckbox({ checked, disabled, onChange, label, hint, testId }) {
  return (
    <label
      className={`flex items-start gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
        disabled
          ? "border-[#E8ECE9] bg-[#F5F3E9]/40 cursor-not-allowed opacity-60"
          : checked
          ? "border-[#849D8E]/40 bg-[#849D8E]/8 cursor-pointer"
          : "border-[#E8ECE9] hover:bg-[#F5F3E9]/60 cursor-pointer"
      }`}
    >
      <input
        type="checkbox"
        className="mt-1 accent-[#849D8E]"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        data-testid={testId}
      />
      <span>
        <span className="block text-[#2A3631] text-sm font-medium">{label}</span>
        {hint && (
          <span className="block text-xs text-[#8A9A92] mt-0.5">{hint}</span>
        )}
      </span>
    </label>
  );
}


/* --------------------------------- Page --------------------------------- */

const TABS = [
  { key: "summary", label: "Mediation Summary", icon: FileText },
  { key: "agreement", label: "Co-Parenting Agreement Draft", icon: Handshake },
  { key: "improve", label: "Things I Can Improve On", icon: Lightbulb },
];

export default function Summary() {
  const [tab, setTab] = useState("summary");

  return (
    <AppShell>
      <div className="fade-up max-w-4xl mx-auto">
        <div className="eyebrow mb-3">Final</div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl text-[#2A3631] mb-3 leading-tight">
          Your prepared documents.
        </h1>
        <p className="text-[#5C6B64] mb-8 max-w-2xl">
          Three AI-synthesized views of your preparation: a focused summary for your
          mediator, a neutral draft agreement to start the conversation with your
          co-parent, and a personal growth plan compiled from your communication and
          readiness reflections.
        </p>

        <div
          className="inline-flex flex-wrap items-center gap-1 p-1 rounded-2xl sm:rounded-full bg-[#F5F3E9] mb-8 max-w-full"
          role="tablist"
        >
          {TABS.map(({ key, label, icon: Icon }) => {
            const active = tab === key;
            return (
              <button
                key={key}
                role="tab"
                aria-selected={active}
                onClick={() => setTab(key)}
                data-testid={`summary-tab-${key}`}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm transition-colors ${
                  active
                    ? "bg-white text-[#2A3631] shadow-sm"
                    : "text-[#5C6B64] hover:text-[#2A3631]"
                }`}
              >
                <Icon size={14} />
                {label}
              </button>
            );
          })}
        </div>

        {tab === "summary" && <MediationSummaryTab />}
        {tab === "agreement" && <AgreementDraftTab />}
        {tab === "improve" && <ImprovementPlanTab />}

        <OrgContactCard />
      </div>
    </AppShell>
  );
}

function OrgContactCard() {
  return (
    <div
      className="mt-12 card-soft p-6 sm:p-7 flex flex-col sm:flex-row items-center gap-5 sm:gap-7"
      data-testid="org-contact-card"
    >
      <img
        src="https://customer-assets.emergentagent.com/job_prepared-parents/artifacts/3vfnf7kd__sacoparentscharactersacoparents_three_feet_away_rotating_and.png"
        alt="SA Coparents"
        className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl object-cover shrink-0 shadow-sm"
      />
      <div className="text-center sm:text-left">
        <div className="font-serif text-xl text-[#2A3631] mb-1">SA Coparents</div>
        <div className="text-xs uppercase tracking-[0.2em] text-[#8A9A92] mb-3">
          Relational Mediation Prep
        </div>
        <address className="not-italic text-sm text-[#5C6B64] leading-relaxed space-y-0.5">
          <div>16607 Blanco #703, San Antonio, Texas 78232</div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3">
            <a
              href="tel:2102241667"
              className="text-[#5C7A6A] hover:text-[#849D8E] hover:underline"
              data-testid="org-contact-phone"
            >
              210-224-1667
            </a>
            <span className="hidden sm:inline text-[#D5D9D5]">·</span>
            <a
              href="mailto:mattsossi@bsossi.com"
              className="text-[#5C7A6A] hover:text-[#849D8E] hover:underline"
              data-testid="org-contact-email"
            >
              mattsossi@bsossi.com
            </a>
          </div>
        </address>
      </div>
    </div>
  );
}
