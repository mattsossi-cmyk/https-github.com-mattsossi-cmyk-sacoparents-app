/**
 * SampleCoParentingLanding.jsx — Iter193 · public sample marketing page.
 *
 * Wraps the public `/api/insights/samples/co-parenting-alignment-report.pdf`
 * in a proper SA CoParents landing experience with a hero, a
 * three-highlight explainer, an embedded PDF preview iframe, and a
 * "start your own" CTA. Sharing this URL in Slack or email produces
 * a clickable card, not a raw PDF blob — mediators can preview
 * before committing to a case.
 *
 * Public: no auth required. Lives outside the AppShell to keep the
 * marketing surface distinct from the authenticated product.
 */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Download, FileText, Users, MessageSquareText, Handshake,
  ShieldCheck, Sparkles,
} from "lucide-react";


const API = process.env.REACT_APP_BACKEND_URL;
const SAMPLE_URL = `${API}/api/insights/samples/co-parenting-alignment-report.pdf`;


function brandedSampleUrl({ firm, color }) {
  const params = new URLSearchParams();
  if ((firm || "").trim()) params.set("firm", firm.trim());
  if ((color || "").trim()) params.set("primary_color", color.trim());
  const qs = params.toString();
  return qs ? `${SAMPLE_URL}?${qs}` : SAMPLE_URL;
}


function Highlight({ Icon, title, body }) {
  return (
    <div className="rounded-3xl bg-white/70 backdrop-blur-sm border border-[#EEE8F7] p-5">
      <div className="rounded-full bg-[#F5EFFB] text-[#3D1A78] p-2.5 w-fit">
        <Icon size={18} />
      </div>
      <h3 className="mt-3 font-serif text-lg text-[#1A1330]">{title}</h3>
      <p className="mt-2 text-sm text-[#4B4567] leading-relaxed">{body}</p>
    </div>
  );
}


export default function SampleCoParentingLanding() {
  // Iter194 · optional firm branding preview so mediators can
  // eyeball a lead-magnet version before copying the URL.
  const [firm, setFirm] = useState("");
  const [color, setColor] = useState("");
  const [applied, setApplied] = useState({ firm: "", color: "" });
  const previewUrl = brandedSampleUrl(applied);
  const rawShareUrl = brandedSampleUrl({ firm, color });
  const isBranded = Boolean(applied.firm || applied.color);

  const applyBranding = () => {
    setApplied({ firm, color });
  };
  const clearBranding = () => {
    setFirm("");
    setColor("");
    setApplied({ firm: "", color: "" });
  };
  const copyShareUrl = async () => {
    try {
      await navigator.clipboard.writeText(rawShareUrl);
    } catch {
      // Best-effort copy — the input right below the button is the
      // visible fallback.
    }
  };

  return (
    <div
      className="min-h-screen bg-gradient-to-b from-[#FAF6FF] via-white to-[#F5EFFB]"
      data-testid="sample-coparenting-landing"
    >
      {/* Simple public header — no AppShell, no auth. */}
      <header className="max-w-6xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <span className="font-serif text-lg text-[#1A1330]">
            <strong className="text-[#3D1A78]">SA</strong> CoParents
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <Link
            to="/signup"
            className="hidden sm:inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] hover:underline"
            data-testid="sample-coparenting-signin-link"
          >
            Sign in
          </Link>
          <Link
            to="/signup"
            className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold"
            data-testid="sample-coparenting-header-cta"
          >
            Start your own <ArrowRight size={14} />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 pb-14">
        <div className="max-w-3xl">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2">
            <FileText size={12} />
            Sample · Co-Parenting Agreement
          </div>
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#1A1330] leading-[1.05] mt-3">
            Step One — <span className="text-[#3D1A78]">Alignment
            Before Agreement.</span>
          </h1>
          <p className="mt-5 text-lg text-[#4B4567] leading-relaxed max-w-2xl">
            This is the exact report a mediator, attorney, or family
            therapist receives when both parents complete SA CoParents
            reflections. Ten neutral sections. Verbatim quotes. No
            recommendations about which parent is right.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href={previewUrl}
              download={
                isBranded
                  ? "sacoparents-alignment-report-branded-sample.pdf"
                  : "sacoparents-alignment-report-sample.pdf"
              }
              className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-5 py-2.5 text-sm font-semibold"
              data-testid="sample-coparenting-download-btn"
            >
              <Download size={14} /> Download the sample PDF
            </a>
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-white px-5 py-2.5 text-sm font-semibold"
              data-testid="sample-coparenting-cta-btn"
            >
              Start your own reflection <ArrowRight size={14} />
            </Link>
          </div>
          <p className="mt-4 text-xs text-[#857E9C] italic max-w-xl">
            Fictional data — Alex R. &amp; Sam R. co-parenting a
            9-year-old named Maya. No real names, no real PII.
          </p>
        </div>
      </section>

      {/* Three-highlight explainer */}
      <section
        className="max-w-6xl mx-auto px-4 sm:px-6 pb-10"
        data-testid="sample-coparenting-highlights"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Highlight
            Icon={Users}
            title="Written by both parents"
            body="Each parent answers six child-focused prompts privately. Nothing is shared until both have finished."
          />
          <Highlight
            Icon={MessageSquareText}
            title="Verbatim, not summarised"
            body={
              'Section 2 surfaces "Both parents mentioned X" bullets. ' +
              "Section 3 shows each parent's answer side-by-side. " +
              "Their voice — not our paraphrase."
            }
          />
          <Highlight
            Icon={Handshake}
            title="Neutral by design"
            body="Never picks a side. Never makes custody recommendations. Every professional we've spoken to wanted more of this and less of the other kind of report."
          />
        </div>
      </section>

      {/* Iter194 · mediator branding form — optional, tucked between
          highlights and the preview iframe so mediators can generate
          a lead-magnet URL without leaving the page. */}
      <section
        className="max-w-6xl mx-auto px-4 sm:px-6 pb-8"
        data-testid="sample-coparenting-branding"
      >
        <div className="rounded-3xl border border-[#D6CFE8] bg-white p-5 sm:p-6">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            <Sparkles size={12} /> For mediators · Brand this sample
          </div>
          <h3 className="mt-2 font-serif text-xl text-[#1A1330]">
            Send it under your firm's name.
          </h3>
          <p className="mt-1 text-sm text-[#4B4567] max-w-2xl leading-relaxed">
            Add your firm name and (optionally) a brand colour. We render
            a fresh PDF on the fly — no upload, no login, no PII on the
            document besides the fictional Alex &amp; Sam. Copy the URL
            and drop it into your intake sequence.
          </p>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-[1fr,180px,auto,auto] gap-3">
            <input
              type="text"
              value={firm}
              maxLength={80}
              onChange={(e) => setFirm(e.target.value)}
              placeholder="Firm name — e.g. Acme Family Mediation LLP"
              className="rounded-full border border-[#D6CFE8] px-4 py-2.5 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/25"
              data-testid="sample-coparenting-firm-input"
            />
            <div className="flex items-center gap-2 rounded-full border border-[#D6CFE8] px-3 py-1">
              <label className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C] shrink-0">
                Accent
              </label>
              <input
                type="color"
                value={color || "#3d1a78"}
                onChange={(e) => setColor(e.target.value)}
                aria-label="Accent color"
                className="h-8 w-10 rounded cursor-pointer bg-transparent"
                data-testid="sample-coparenting-color-input"
              />
              <input
                type="text"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                placeholder="#3D1A78"
                maxLength={7}
                className="w-20 text-xs bg-transparent focus:outline-none"
                data-testid="sample-coparenting-color-hex"
              />
            </div>
            <button
              type="button"
              onClick={applyBranding}
              disabled={!firm.trim() && !color.trim()}
              className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="sample-coparenting-branding-apply"
            >
              Preview branded PDF
            </button>
            <button
              type="button"
              onClick={clearBranding}
              className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5EFFB] px-4 py-2.5 text-sm font-semibold"
              data-testid="sample-coparenting-branding-clear"
            >
              Reset
            </button>
          </div>
          {isBranded && (
            <div
              className="mt-4 flex items-center gap-2 rounded-2xl bg-[#F5EFFB] p-3"
              data-testid="sample-coparenting-branding-share"
            >
              <input
                type="text"
                readOnly
                value={rawShareUrl}
                onFocus={(e) => e.currentTarget.select()}
                className="flex-1 min-w-0 bg-transparent text-xs text-[#3D1A78] font-mono focus:outline-none"
                data-testid="sample-coparenting-branding-share-url"
              />
              <button
                type="button"
                onClick={copyShareUrl}
                className="rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.14em] shrink-0 hover:bg-[#EDE3FA]"
                data-testid="sample-coparenting-branding-share-copy"
              >
                Copy URL
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Embedded PDF preview — most browsers render inline, others get
          the download prompt via the iframe fallback. */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-16">
        <div className="rounded-3xl border-2 border-[#D6CFE8] bg-white shadow-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#EEE8F7] bg-[#FAF6FF]">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2">
              <FileText size={12} /> Preview · 17-page sample
              {isBranded && (
                <span className="text-[#1F5C3B]">· branded</span>
              )}
            </div>
            <a
              href={previewUrl}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-semibold text-[#3D1A78] hover:underline inline-flex items-center gap-1"
              data-testid="sample-coparenting-open-new-tab"
            >
              Open in new tab <ArrowRight size={12} />
            </a>
          </div>
          <iframe
            src={previewUrl}
            title="SA CoParents · Co-Parenting Agreement sample"
            className="w-full"
            style={{ height: "820px" }}
            data-testid="sample-coparenting-pdf-iframe"
          />
        </div>
      </section>

      {/* Bottom CTA + safety note */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-20">
        <div className="rounded-3xl bg-gradient-to-br from-[#3D1A78] to-[#2a0f5f] text-white p-8 sm:p-10 relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-white/10 pointer-events-none" />
          <div className="relative max-w-2xl">
            <h2 className="font-serif text-3xl sm:text-4xl leading-tight">
              Ready to run this with your co-parent?
            </h2>
            <p className="mt-3 text-sm sm:text-base text-[#EBE2FA] leading-relaxed">
              Sign up in under a minute. Answer the six prompts at your
              own pace. Invite your co-parent when you're ready. Nothing
              is shared until both of you finish.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 rounded-full bg-white text-[#3D1A78] hover:bg-[#F5EFFB] px-5 py-2.5 text-sm font-semibold"
                data-testid="sample-coparenting-footer-cta"
              >
                Start your own report <ArrowRight size={14} />
              </Link>
              <a
                href={SAMPLE_URL}
                download="sacoparents-alignment-report-sample.pdf"
                className="inline-flex items-center gap-2 rounded-full border border-white/40 text-white hover:bg-white/10 px-5 py-2.5 text-sm font-semibold"
              >
                <Download size={14} /> Share the sample with a co-parent
              </a>
            </div>
            <p className="mt-6 text-xs text-[#EBE2FA]/80 flex items-start gap-1.5 max-w-xl">
              <ShieldCheck size={12} className="mt-0.5 shrink-0" />
              <span>
                Safety-sensitive subjects (physical or emotional safety)
                are gated behind explicit dual-consent — the joint report
                never auto-merges Safety answers.
              </span>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
