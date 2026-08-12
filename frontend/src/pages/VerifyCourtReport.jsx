import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Toaster } from "../components/ui/sonner";
import { CheckCircle2, Scale, ShieldCheck } from "lucide-react";

/**
 * Public Court-Report verify + co-sign page.
 * URL: /verify/court-report/:sig_id
 * Rendered without app auth — sig_id IS the ticket.
 */
export default function VerifyCourtReport() {
  const { sig_id } = useParams();
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewerName, setReviewerName] = useState("");
  const [reviewerRole, setReviewerRole] = useState("");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get(`/verify/court-report/${sig_id}`);
        if (!cancelled) setMeta(r.data);
      } catch (e) {
        if (!cancelled) setMeta({ issued: false });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sig_id]);

  const submit = async () => {
    if (!reviewerName.trim() || !reviewerRole.trim()) {
      toast.error("Please provide your printed name and role before co-signing.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/verify/court-report/${sig_id}/cosign`, {
        reviewer_name: reviewerName.trim(),
        reviewer_role: reviewerRole.trim(),
        reviewer_notes: reviewerNotes.trim(),
      });
      toast.success("Co-signature recorded. You can now download the co-signed PDF.");
      const r = await api.get(`/verify/court-report/${sig_id}`);
      setMeta(r.data);
    } catch (e) {
      const status = e?.response?.status;
      if (status === 409) {
        toast.error("This report has already been co-signed.");
      } else {
        toast.error(e?.response?.data?.detail || "Couldn't record the co-signature.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center text-[#4B4567]">
        Loading…
      </div>
    );
  }

  if (!meta?.issued) {
    return (
      <div className="min-h-screen grid place-items-center px-6 py-16">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-bold text-[#1A1330] mb-2">Signature not recognised</h1>
          <p className="text-sm text-[#4B4567]">
            This link does not correspond to a court report issued by SA CoParents.
            If you received this link from a parent, ask them to reissue a fresh
            QR from their assessment.
          </p>
        </div>
      </div>
    );
  }

  const cosigned = !!meta.cosigned;
  const pdfUrl = `${process.env.REACT_APP_BACKEND_URL || ""}/api/verify/court-report/${sig_id}/pdf`;

  return (
    <div className="min-h-screen bg-[#FAF9FD] text-[#1A1330] px-4 sm:px-6 py-10">
      <Toaster />
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-[#3D1A78] font-bold mb-2">
          <ShieldCheck size={14} />
          Trauma-Informed Safety and Functioning Lens · Court Report
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 leading-tight">
          Reviewer Co-Sign Portal
        </h1>
        <div className="rounded-2xl border border-[#3D1A78]/25 bg-[#F5F1FB] p-4 mb-6 text-sm leading-relaxed">
          <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-1">
            Read this first
          </div>
          This report is a guided self-reflection resource — <strong>not a clinical, forensic, legal, or professional evaluation</strong>. Co-signing acknowledges you have <em>discussed the findings with the parent</em>, not that you endorse them as an evaluation.
        </div>

        <div className="rounded-3xl bg-white border border-[#E5E0EE] shadow-sm p-6 sm:p-8 mb-6">
          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#857E9C] font-bold mb-1">Parent</div>
              <div className="font-semibold" data-testid="cosign-parent-name">{meta.parent_name || "-"}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#857E9C] font-bold mb-1">Issued</div>
              <div className="font-semibold" data-testid="cosign-issued-on">{meta.issued_on || "-"}</div>
            </div>
          </div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#857E9C] font-bold mb-2">Findings at a glance</div>
          <div className="space-y-2 mb-4">
            {Object.entries(meta.findings_headlines || {}).map(([k, v]) => (
              <div key={k} className="text-sm text-[#1A1330]" data-testid={`cosign-headline-${k.replace(/_/g, "-")}`}>
                <span className="font-semibold">{k.replace(/_/g, " ")}: </span>
                {v}
              </div>
            ))}
          </div>
        </div>

        {cosigned ? (
          <div
            className="rounded-3xl bg-white border-2 border-[#1F7A3A]/30 p-6 mb-6"
            data-testid="cosign-completed-panel"
          >
            <div className="flex items-center gap-2 text-[#1F7A3A] mb-2">
              <CheckCircle2 size={16} />
              <div className="text-[10px] uppercase tracking-[0.2em] font-bold">Co-signed</div>
            </div>
            <div className="text-sm mb-1"><strong>{meta.cosigner?.name}</strong> — {meta.cosigner?.role}</div>
            {meta.cosigner?.notes && (
              <p className="text-sm text-[#4B4567] italic mt-2">"{meta.cosigner.notes}"</p>
            )}
            <div className="text-xs text-[#857E9C] mt-2">Signed at {meta.cosigner?.cosigned_at}</div>
          </div>
        ) : (
          <div className="rounded-3xl bg-white border border-[#E5E0EE] p-6 sm:p-8 mb-6" data-testid="cosign-form-panel">
            <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-3">Add your co-signature</div>
            <label className="block text-xs text-[#4B4567] mb-1">Printed name</label>
            <input
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              placeholder="e.g. Dr Alex Reviewer"
              data-testid="cosign-name-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
            <label className="block text-xs text-[#4B4567] mb-1">Role</label>
            <input
              type="text"
              value={reviewerRole}
              onChange={(e) => setReviewerRole(e.target.value)}
              placeholder="e.g. Accredited family mediator, DV advocate"
              data-testid="cosign-role-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
            <label className="block text-xs text-[#4B4567] mb-1">Notes (optional)</label>
            <textarea
              value={reviewerNotes}
              onChange={(e) => setReviewerNotes(e.target.value)}
              placeholder="e.g. Reviewed with parent on 12 Aug 2026. Confirmed alignment with local DV service."
              rows={4}
              maxLength={2000}
              data-testid="cosign-notes-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
            <button
              type="button"
              onClick={submit}
              disabled={submitting}
              data-testid="cosign-submit-button"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-60"
            >
              {submitting ? "Recording…" : "Record co-signature"}
            </button>
          </div>
        )}

        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="cosign-download-pdf"
          className="inline-flex items-center gap-2 rounded-full bg-[#1A1330] text-white px-5 py-2.5 text-sm font-semibold shadow-md hover:bg-[#3D1A78]"
        >
          <Scale size={14} />
          Download the {cosigned ? "co-signed " : ""}court report
        </a>
      </div>
    </div>
  );
}
