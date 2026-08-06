/**
 * VerifyBriefing — public page reached by scanning the QR in the
 * footer of any Four-Dimension Briefing PDF. It asks the backend
 * whether the given briefing id was issued by SA CoParents.
 *
 * Privacy: the public response is intentionally minimal — issued
 * yes/no + issue date only. No scores, tiers, names, or audience
 * are exposed. This protects survivors if a QR image leaks and
 * matches the product decision recorded in briefing_verify_routes.py.
 */
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle2, ShieldAlert, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const formatIssuedOn = (iso) => {
  if (!iso) return "";
  try {
    const d = new Date(`${iso}T00:00:00Z`);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      year: "numeric", month: "long", day: "numeric", timeZone: "UTC",
    });
  } catch {
    return iso;
  }
};

export default function VerifyBriefing() {
  const { sig_id: sigId } = useParams();
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get(
          `/verify/briefing/${encodeURIComponent(sigId)}`
        );
        if (!cancelled) setState({ loading: false, data: res.data, error: null });
      } catch (err) {
        logError("verify briefing", err);
        if (!cancelled) {
          setState({
            loading: false,
            data: null,
            error:
              err?.response?.data?.detail ||
              "Could not check this briefing right now.",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [sigId]);

  const issued = !!(state.data && state.data.issued);

  return (
    <div
      className="min-h-screen bg-[#FCFBFE] flex flex-col items-center px-4 py-12"
      data-testid="verify-briefing-root"
    >
      <div className="w-full max-w-lg">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] underline mb-6"
          data-testid="verify-briefing-back"
        >
          ← SA CoParents
        </Link>

        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Briefing Verification
          </div>
          <h1 className="mt-1 font-serif text-2xl text-[#1A1330]">
            Was this Four-Dimension Briefing issued by SA CoParents?
          </h1>

          {state.loading && (
            <div
              className="mt-6 text-sm text-[#4B4567] inline-flex items-center gap-2"
              data-testid="verify-briefing-loading"
            >
              <Loader2 className="animate-spin" size={14} /> Checking the briefing id…
            </div>
          )}

          {!state.loading && issued && (
            <div
              className="mt-6 rounded-2xl border-2 border-[#B5DFC5] bg-[#F1F9F4] p-4 sm:p-5"
              data-testid="verify-briefing-ok"
            >
              <div className="flex items-start gap-3">
                <CheckCircle2 size={22} className="text-[#1F5C3B] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-[#1F5C3B]">
                    Yes — this briefing id was issued by SA CoParents.
                  </div>
                  <p className="text-xs text-[#1F5C3B] mt-1">
                    Issued on{" "}
                    <span className="font-semibold" data-testid="verify-briefing-date">
                      {formatIssuedOn(state.data.issued_on)}
                    </span>{" "}
                    (UTC).
                  </p>
                </div>
              </div>
              <div className="mt-4 text-[10px] text-[#4B4567]">
                Briefing ID:{" "}
                <span className="font-mono" data-testid="verify-briefing-id">
                  {state.data.sig_id}
                </span>
              </div>
            </div>
          )}

          {!state.loading && state.data && !issued && (
            <div
              className="mt-6 rounded-2xl border-2 border-[#EFB4B4] bg-[#F8D7D7] p-4 sm:p-5"
              data-testid="verify-briefing-not-issued"
            >
              <div className="flex items-start gap-3">
                <ShieldAlert size={22} className="text-[#B02A2A] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-[#B02A2A]">
                    Not recognised
                  </div>
                  <p className="text-xs text-[#B02A2A] mt-1">
                    This id is not on record as a briefing issued by SA
                    CoParents. It may have been mistyped, or the QR may have
                    come from a document that was not generated on this
                    platform.
                  </p>
                </div>
              </div>
              <div className="mt-3 text-[10px] text-[#4B4567]">
                Checked id:{" "}
                <span className="font-mono">{state.data.sig_id}</span>
              </div>
            </div>
          )}

          {!state.loading && state.error && (
            <div
              className="mt-6 text-sm text-[#B02A2A]"
              data-testid="verify-briefing-error"
            >
              {state.error}
            </div>
          )}

          <p className="mt-6 text-[11px] text-[#4B4567] italic">
            This check only confirms that a briefing id was issued here and
            when. It does not attest to the truth of any content in the
            report, nor does it constitute a clinical, legal, or
            evidentiary endorsement. SA CoParents reports are informational
            and not legal advice.
          </p>
        </div>
      </div>
    </div>
  );
}
