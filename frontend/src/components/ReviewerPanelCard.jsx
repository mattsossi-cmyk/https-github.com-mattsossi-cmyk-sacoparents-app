/**
 * ReviewerPanelCard — Transparency component on the Methodology page.
 * Lists independent expert reviewers who have signed off on the Family
 * Violence and Communication Safety Screen. Falls back to a clear
 * "pending" state when no reviewers have been added.
 *
 * Also surfaces a "Download reviewer packet" link for the app operator
 * to hand to a candidate reviewer.
 */
import { useEffect, useState } from "react";
import { Users, Download, Loader2, ShieldCheck, Clock } from "lucide-react";
import { api, API } from "../lib/api";

const ROLE_LABEL = {
  dv_advocate:            "Domestic-violence advocate",
  forensic_psychologist:  "Forensic psychologist",
  family_law_attorney:    "Family-law attorney (Texas)",
  clinician:              "Licensed clinician",
  other:                  "Other",
};

function StatusPill({ status }) {
  if (status === "reviewed") {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F4EC] text-[#1F5C3B] ring-1 ring-[#1F5C3B]/25"
        data-testid="reviewer-panel-status-reviewed"
      >
        <ShieldCheck size={10} /> Reviewed
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#F0EAFB] text-[#3D1A78] ring-1 ring-[#3D1A78]/25"
      data-testid="reviewer-panel-status-pending"
    >
      <Clock size={10} /> Review pending
    </span>
  );
}

export default function ReviewerPanelCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await api.get("/reviewer-panel");
        setData(r.data);
      } catch {
        setData({ status: "pending", reviewers: [] });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <aside
        className="not-prose rounded-3xl border border-[#E5E0EE] bg-white p-5 my-6 inline-flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="reviewer-panel-loading"
      >
        <Loader2 size={14} className="animate-spin" /> Loading reviewer panel…
      </aside>
    );
  }

  const reviewers = data?.reviewers || [];
  const packetUrl = `${API}/reviewer-panel/packet`;

  return (
    <aside
      className="not-prose rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 my-6"
      data-testid="reviewer-panel"
      aria-labelledby="reviewer-panel-title"
    >
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
            Independent expert review
          </div>
          <h3
            id="reviewer-panel-title"
            className="font-serif text-xl text-[#1A1330]"
          >
            Who has reviewed this screen
          </h3>
        </div>
        <StatusPill status={data?.status || "pending"} />
      </div>

      <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
        Because a family-violence screen carries weight, we publish the
        names, credentials, roles, and review dates of every independent
        expert who has evaluated the current questions and scoring rules.
        No reviewer&rsquo;s name appears here unless they have signed off
        in writing and agreed to be listed.
      </p>

      {reviewers.length === 0 ? (
        <div
          className="rounded-2xl border-2 border-dashed border-[#E5E0EE] bg-[#FAF8FE] p-5"
          data-testid="reviewer-panel-empty"
        >
          <div className="flex items-start gap-2 mb-2">
            <Users size={16} className="text-[#3D1A78] shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-[#1A1330]">
                Independent expert review is pending
              </div>
              <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
                We are seeking sign-off from three professionals: a
                domestic-violence advocate, a forensic psychologist, and
                a Texas family-law attorney. Their credentials, roles,
                and review dates will appear here immediately upon
                approval.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <ul className="space-y-3" data-testid="reviewer-panel-list">
          {reviewers.map((r, i) => (
            <li
              key={`${r.name}-${r.review_date}-${i}`}
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
              data-testid={`reviewer-item-${i}`}
            >
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <div className="font-bold text-[#1A1330]">{r.name}</div>
                  <div className="text-[11px] uppercase tracking-[0.15em] text-[#3D1A78] font-bold mt-0.5">
                    {ROLE_LABEL[r.role] || r.role}
                    {r.org ? ` · ${r.org}` : ""}
                  </div>
                </div>
                <div className="text-xs text-[#4B4567]">
                  Reviewed {r.review_date}
                </div>
              </div>
              {r.review_scope && (
                <div className="mt-2 text-[12px] text-[#4B4567]">
                  <strong>Scope:</strong> {r.review_scope}
                </div>
              )}
              {r.attestation && (
                <blockquote className="mt-2 pl-3 border-l-2 border-[#3D1A78]/30 text-sm text-[#1A1330] italic">
                  "{r.attestation}"
                </blockquote>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 pt-3 border-t border-[#EFECF6] flex items-center justify-between gap-3 flex-wrap">
        <div className="text-[11px] text-[#8471B3]">
          Screen version: <strong>{data?.review_scope_version || "v1.0"}</strong>
        </div>
        <a
          href={packetUrl}
          data-testid="reviewer-panel-download-packet"
          className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] font-semibold hover:underline"
        >
          <Download size={12} /> Download reviewer packet (PDF)
        </a>
      </div>
    </aside>
  );
}
