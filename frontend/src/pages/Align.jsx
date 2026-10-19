import React from "react";
import { Link } from "react-router-dom";

/**
 * SA CoParents Align — the professional's view (holding page,
 * iter244 Phase A).
 *
 * NORTH_STAR.md commits to a rigid two-site split: the parent-
 * facing app (sacoparentsapp.online) and the professional-facing
 * view (sacoparentsalign.com). This page scaffolds the Align
 * entry at `/align` so routing is enforced NOW, even though prod
 * still ships both sites from one domain. DNS/domain split comes
 * in Phase E (DevOps).
 *
 * Everything a mediator / attorney / coordinator needs is already
 * built — this page just acts as a professional-language front
 * door that links them into the right surface instead of forcing
 * them through the parent-journey shell at `/`.
 */
export default function Align() {
  return (
    <div
      className="min-h-screen bg-slate-50"
      data-testid="align-landing"
    >
      {/* Header — intentionally different visual language from the
          parent portal. Slate + navy, not purple/rose. */}
      <header className="bg-slate-900 text-white px-6 py-5 border-b-4 border-emerald-500">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="shrink-0 w-11 h-11 rounded-lg bg-emerald-500 text-slate-900 flex items-center justify-center">
            <i className="fa-solid fa-scale-balanced text-xl"></i>
          </div>
          <div>
            <div className="text-[0.625rem] uppercase tracking-widest text-emerald-400 font-bold">
              Professional Workspace
            </div>
            <h1 className="text-xl font-bold tracking-tight">
              SA CoParents Align
            </h1>
            <p className="text-xs text-slate-300">
              The mediator, attorney, and coordinator view of a
              family's parent journey.
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Role explainer. Separates Align from the parent app in
            one line so a parent who lands here by mistake knows
            immediately to go to /. */}
        <section
          className="bg-white rounded-xl border border-slate-200 p-5"
          data-testid="align-role-explainer"
        >
          <div className="text-[0.625rem] uppercase tracking-widest text-slate-500 font-bold">
            Looking for the parent portal?
          </div>
          <p className="text-sm text-slate-700 leading-snug mt-1">
            Align is for professionals reviewing a case. If you're a
            parent working on your own co-parenting situation,{" "}
            <Link
              to="/"
              data-testid="align-parent-portal-link"
              className="text-purple-700 underline underline-offset-2 font-semibold"
            >
              head to the SA CoParents App instead
            </Link>
            .
          </p>
        </section>

        {/* Professional entry tiles — pointing at the surfaces that
            already exist. No new routes built here; this is a
            re-framing of what's already shipped. */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            to="/admin"
            data-testid="align-tile-admin"
            className="bg-white rounded-xl border border-slate-200 p-5 hover:border-emerald-400 hover:shadow-sm transition group"
          >
            <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <i className="fa-solid fa-chart-line"></i>
            </div>
            <h3 className="text-sm font-bold text-slate-900 mt-3">
              Case Dashboard
            </h3>
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              Analytics overview, recent users, daily signups, and
              consent-adoption digest.
            </p>
            <div className="mt-3 text-[0.6875rem] font-bold text-emerald-700 group-hover:underline">
              Open dashboard →
            </div>
          </Link>

          <Link
            to="/joint-reports"
            data-testid="align-tile-joint-reports"
            className="bg-white rounded-xl border border-slate-200 p-5 hover:border-emerald-400 hover:shadow-sm transition group"
          >
            <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <i className="fa-solid fa-file-signature"></i>
            </div>
            <h3 className="text-sm font-bold text-slate-900 mt-3">
              Joint Reports
            </h3>
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              Review a case's Co-Parenting Agreement, Joint
              Agreement, or Professional Intro PDF.
            </p>
            <div className="mt-3 text-[0.6875rem] font-bold text-emerald-700 group-hover:underline">
              Open joint reports →
            </div>
          </Link>

          <Link
            to="/admin/reviewers"
            data-testid="align-tile-reviewers"
            className="bg-white rounded-xl border border-slate-200 p-5 hover:border-emerald-400 hover:shadow-sm transition group"
          >
            <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <i className="fa-solid fa-user-check"></i>
            </div>
            <h3 className="text-sm font-bold text-slate-900 mt-3">
              Reviewer Workbench
            </h3>
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              Signature verification, pathway briefings, and
              court-report attestations.
            </p>
            <div className="mt-3 text-[0.6875rem] font-bold text-emerald-700 group-hover:underline">
              Open workbench →
            </div>
          </Link>

          <Link
            to="/samples"
            data-testid="align-tile-samples"
            className="bg-white rounded-xl border border-slate-200 p-5 hover:border-emerald-400 hover:shadow-sm transition group"
          >
            <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <i className="fa-solid fa-file-pdf"></i>
            </div>
            <h3 className="text-sm font-bold text-slate-900 mt-3">
              Sample Reports
            </h3>
            <p className="text-xs text-slate-600 mt-1 leading-snug">
              Preview Co-Parenting, Educational, Medical, and
              Psychological report formats before referring a
              family in.
            </p>
            <div className="mt-3 text-[0.6875rem] font-bold text-emerald-700 group-hover:underline">
              Browse samples →
            </div>
          </Link>
        </section>

        {/* Compliance footer — HB 300 / HIPAA language is correct
            here because professionals need to see it. Parent-side
            copy would never surface this. */}
        <footer
          className="pt-6 border-t border-slate-200 text-[0.6875rem] text-slate-500 leading-snug space-y-1"
          data-testid="align-compliance-footer"
        >
          <p>
            SA CoParents Align is a professional interface governed by
            Texas HB 300 and HIPAA (where a BAA is in force). PHI access
            is logged. Breach runbooks are available via the compliance
            tile in the Case Dashboard.
          </p>
          <p>
            Created by Matt Sossi, Founder of SA CoParents (San Antonio,
            Texas). Future production domain:
            <span className="font-mono"> sacoparentsalign.com</span>.
          </p>
        </footer>
      </main>
    </div>
  );
}
