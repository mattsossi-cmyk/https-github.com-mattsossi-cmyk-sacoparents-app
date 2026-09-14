import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Gavel } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function CourtReferralsInbox({ refs: external, onChange, alwaysShow = false }) {
  const [internal, setInternal] = useState(null);
  const refs = external !== undefined ? external : internal;
  const navigate = useNavigate();
  const load = () => {
    if (onChange) return onChange();
    api.get("/professional/court-referrals").then((r) => setInternal(r.data)).catch(() => setInternal([]));
  };
  useEffect(() => { if (external === undefined) load(); }, []);

  const accept = async (x) => {
    try { const { data } = await api.post(`/professional/court-referrals/${x.id}/accept`); toast.success("Referral accepted — invite both parents to open the case"); navigate(data.next); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const decline = async (x) => {
    const reason = window.prompt(`Decline the referral for Cause No. ${x.cause_number}? Give the court a brief reason:`);
    if (reason === null) return;
    try { await api.post(`/professional/court-referrals/${x.id}/decline`, { reason }); toast.success("Referral declined — the court has been notified"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const pending = (refs || []).filter((x) => x.status === "pending");
  if (!alwaysShow && (!refs || refs.length === 0)) return null;
  return (
    <section id="court-referrals" className="bg-white border border-border rounded-lg p-6 mb-6 scroll-mt-6" data-testid="court-referrals-inbox">
      <h2 className="text-lg font-semibold flex items-center gap-2"><Gavel className="h-4 w-4" /> Court-Referred Cases {pending.length > 0 && <span className="rounded-full bg-align-yellow px-2 py-0.5 text-xs font-bold text-yellow-950" data-testid="court-referrals-pending-count">{pending.length} new</span>}</h2>
      <p className="text-sm text-muted-foreground mt-1">Court Refers Case → You Accept → You Invite Parents → Parents Complete Assessments → Joint Report → Your Review → Professional Statement → You Send Reports to Court.</p>
      {(!refs || refs.length === 0) && <p className="mt-4 text-sm text-muted-foreground" data-testid="court-referrals-empty">No court referrals yet. When a judge refers a matter to you, it appears here for you to accept.</p>}
      <ul className="mt-4 divide-y divide-border" data-testid="court-referrals-list">
        {(refs || []).map((x) => (
          <li key={x.id} className="py-3 flex flex-wrap items-start justify-between gap-3" data-testid={`court-referral-${x.id}`}>
            <div className="min-w-0 text-sm">
              <p className="font-semibold">Cause No. {x.cause_number} <span className="ml-1 font-normal text-muted-foreground">· {x.court_name || "court"} · {x.judge_name}</span></p>
              <p className="text-xs text-muted-foreground mt-0.5">{[x.child_initials && `Child ${x.child_initials}`, x.parent_a_name, x.parent_b_name, `referred ${x.created_at?.slice(0, 10)}`].filter(Boolean).join(" · ")}</p>
              {x.hearing_date && <p className={`mt-0.5 text-xs font-semibold ${x.overdue ? "text-red-700" : "text-brand-purple"}`} data-testid={`court-referral-hearing-${x.id}`}>{x.overdue ? "⚠ OVERDUE · " : ""}Hearing {x.hearing_date}{x.overdue ? " — within 7 days and nothing submitted" : x.status !== "submitted" ? " · reminder one week before if not yet submitted" : ""}</p>}
              {(x.requested_reports || []).length > 0 && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1" data-testid={`court-referral-reports-${x.id}`}>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Court requests:</span>
                  {x.requested_reports.map((r) => <span key={r.key} className="rounded-full bg-secondary px-2 py-0.5 text-xs font-semibold text-brand-purple">{r.label}</span>)}
                </div>
              )}
              {x.note && <p className="mt-1 text-xs italic text-muted-foreground">"{x.note}"</p>}
            </div>
            <div className="flex items-center gap-2">
              {x.status === "pending" ? (<>
                <Button size="sm" onClick={() => accept(x)} data-testid={`court-referral-accept-${x.id}`}>Accept</Button>
                <Button size="sm" variant="outline" onClick={() => decline(x)} data-testid={`court-referral-decline-${x.id}`}>Decline</Button>
              </>) : x.status === "accepted" && !x.case_id ? (
                <Button size="sm" variant="outline" onClick={() => navigate(`/joint/new?referral=${x.id}`)} data-testid={`court-referral-continue-${x.id}`}>Invite parents</Button>
              ) : (
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${x.status === "declined" ? "bg-red-50 text-red-700" : x.status === "submitted" ? "bg-brand-purple/10 text-brand-purple" : "bg-align-green/15 text-green-900"}`} data-testid={`court-referral-status-${x.id}`}>{x.status === "submitted" ? "Submitted to court" : x.status}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
