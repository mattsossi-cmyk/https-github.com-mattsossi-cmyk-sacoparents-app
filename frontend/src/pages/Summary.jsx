import React, { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { api, API } from "../lib/api";
import { toast } from "sonner";
import { Sparkles, Download, RefreshCw } from "lucide-react";

export default function Summary() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const loadHistory = async () => {
    try {
      const r = await api.get("/mediation/summaries");
      setHistory(r.data || []);
      if (!summary && r.data?.length) setSummary(r.data[0]);
    } catch {}
  };

  useEffect(() => { loadHistory(); }, []); // eslint-disable-line

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
    if (!summary?.summary_id) return;
    try {
      const token = localStorage.getItem("sa_access_token");
      const res = await fetch(`${API}/mediation/summary/${summary.summary_id}/pdf`, {
        credentials: "include",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mediation-summary-${summary.summary_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Could not download PDF.");
    }
  };

  return (
    <AppShell>
      <div className="fade-up max-w-4xl mx-auto">
        <div className="eyebrow mb-3">Final</div>
        <h1 className="font-serif text-4xl sm:text-5xl text-[#2A3631] mb-3">
          Your mediation summary.
        </h1>
        <p className="text-[#5C6B64] mb-8 max-w-2xl">
          AI-synthesized from your preparation. Calm, balanced, and ready to share with your
          mediator.
        </p>

        {!summary && (
          <div className="card-soft p-10 text-center">
            <div className="w-14 h-14 rounded-full bg-[#849D8E]/15 text-[#849D8E] grid place-items-center mx-auto mb-4">
              <Sparkles size={20} />
            </div>
            <div className="font-serif text-2xl text-[#2A3631] mb-2">
              Generate your first summary
            </div>
            <p className="text-[#5C6B64] mb-6">
              We'll synthesize your goals, concerns, priority agenda, communication style,
              and readiness into a single mediator-ready document.
            </p>
            <button
              onClick={generate}
              disabled={loading}
              className="btn-sage inline-flex items-center gap-2"
              data-testid="summary-generate-button"
            >
              <Sparkles size={16} />
              {loading ? "Synthesizing…" : "Generate summary"}
            </button>
          </div>
        )}

        {summary && (
          <div className="space-y-6" data-testid="summary-card">
            <div className="card-soft p-8">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
                <div>
                  <div className="eyebrow mb-1">Readiness</div>
                  <div className="font-serif text-2xl text-[#2A3631]">
                    {summary.readiness_label}{" "}
                    <span className="text-[#8A9A92] text-base">
                      · {summary.readiness_score}/100
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={generate}
                    className="btn-soft inline-flex items-center gap-2"
                    disabled={loading}
                    data-testid="summary-regenerate-button"
                  >
                    <RefreshCw size={14} />
                    {loading ? "Re-generating…" : "Regenerate"}
                  </button>
                  <button
                    onClick={download}
                    className="btn-sage inline-flex items-center gap-2"
                    data-testid="summary-download-button"
                  >
                    <Download size={16} />
                    Download PDF
                  </button>
                </div>
              </div>

              <Section title="Child-centered goals">
                <p className="text-[#2A3631] leading-relaxed">
                  {summary.child_goals_summary}
                </p>
              </Section>

              <Section title="Top concerns">
                <BulletList items={summary.top_concerns} />
              </Section>

              <Section title="Priority agenda">
                <ol className="space-y-2 list-none">
                  {(summary.priority_agenda || []).map((it, i) => (
                    <li key={i} className="flex gap-3">
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
              <div className="card-soft p-6">
                <div className="eyebrow mb-3">Previous summaries</div>
                <div className="space-y-2">
                  {history.slice(0, 8).map((h) => (
                    <button
                      key={h.summary_id}
                      onClick={() => setSummary(h)}
                      className="w-full text-left rounded-xl px-4 py-3 bg-[#F5F3E9] hover:bg-[#E8ECE9] text-sm flex items-center justify-between"
                      data-testid={`summary-history-${h.summary_id}`}
                    >
                      <span className="text-[#2A3631]">{h.readiness_label}</span>
                      <span className="text-[#8A9A92]">
                        {new Date(h.generated_at).toLocaleString()}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
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
      {items.map((s, i) => (
        <li key={i} className="flex gap-2 text-[#2A3631]">
          <span className="text-[#849D8E] mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-[#849D8E]" />
          <span>{s}</span>
        </li>
      ))}
    </ul>
  );
}
