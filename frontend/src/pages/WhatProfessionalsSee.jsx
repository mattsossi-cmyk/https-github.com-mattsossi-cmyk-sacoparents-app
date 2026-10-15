import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Scale, ShieldCheck } from "lucide-react";

import { ATTORNEY_REVIEW_PENDING, CASE_EXCEPTION, COURT_POINTS, METHODS, SHARING_NOTICES, SHORT_VERSION } from "../lib/proVisibility";
import { useHashScroll } from "../lib/useHashScroll";

const UPDATED = "June 2026";

function ReviewTag({ testid }) {
  if (!ATTORNEY_REVIEW_PENDING) return null;
  return (
    <span data-testid={testid} className="inline-flex items-center gap-1 rounded-full bg-amber-100 border border-amber-300 text-amber-900 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5">
      <Scale size={10} /> Attorney review
    </span>
  );
}

function H2({ id, children, tag }) {
  return (
    <h2 id={id} className="scroll-mt-6 font-serif text-2xl text-[#1A1330] mt-12 mb-4 flex flex-wrap items-center gap-3">
      {children}
      {tag}
    </h2>
  );
}

function Bullets({ items, testid }) {
  return (
    <ul data-testid={testid} className="space-y-2">
      {items.map((t) => (
        <li key={t} className="flex items-start gap-2.5 text-[15px] text-[#4B4567] leading-relaxed">
          <i className="fa-solid fa-circle-check text-[#2DB5B5] text-[13px] mt-1.5" aria-hidden="true"></i>
          <span>{t}</span>
        </li>
      ))}
    </ul>
  );
}

function MethodCard({ m }) {
  return (
    <section id={m.key} data-testid={`pros-see-method-${m.key}`} className="scroll-mt-6 rounded-2xl border border-[#E5E0EE] bg-white p-5 sm:p-6 transition-shadow hover:shadow-md">
      <div className="flex flex-wrap items-center gap-3 mb-1">
        <span className="w-9 h-9 rounded-xl bg-[#F5F1FB] text-[#3D1A78] grid place-items-center">
          <i className={`fa-solid ${m.icon}`} aria-hidden="true"></i>
        </span>
        <h3 className="font-bold text-[#1A1330] text-lg leading-tight">{m.title}</h3>
        {m.review && <ReviewTag testid={`pros-see-review-${m.key}`} />}
      </div>
      <p className="text-[13px] text-[#857E9C] mb-3">{m.lead}</p>
      <Bullets items={m.points} />
    </section>
  );
}

function NoticeCard({ id, n }) {
  return (
    <div id={id} data-testid={`pros-see-assessment-${id}`} className="scroll-mt-6 rounded-2xl border border-[#E5E0EE] bg-[#FBFAFE] p-5">
      <h3 className="font-bold text-[#1A1330] mb-2">{n.title}</h3>
      <dl className="grid gap-2 text-[14px] text-[#4B4567] leading-relaxed">
        <div><dt className="inline font-semibold text-[#1A1330]">Who sees it: </dt><dd className="inline">{n.stays}</dd></div>
        <div><dt className="inline font-semibold text-[#1A1330]">What can leave: </dt><dd className="inline">{n.leaves}</dd></div>
        <div><dt className="inline font-semibold text-[#1A1330]">AI help: </dt><dd className="inline">{n.ai}</dd></div>
      </dl>
    </div>
  );
}

function Controls() {
  const cls = "text-[#2A0F5F] font-semibold underline underline-offset-2";
  return (
    <ul className="space-y-2 text-[15px] text-[#4B4567] leading-relaxed list-disc pl-5">
      <li>See and cancel documents you've sent, and turn off professional access, on <Link to="/shared-with-professionals" data-testid="pros-see-link-shared" className={cls}>Shared with professionals</Link>.</li>
      <li>Read the full <Link to="/privacy" data-testid="pros-see-link-policy" className={cls}>Privacy Policy</Link> and <Link to="/privacy#your-rights" data-testid="pros-see-link-rights" className={cls}>your data rights</Link>.</li>
      <li>Delete your account and everything in it from <Link to="/delete-account" data-testid="pros-see-link-delete" className={cls}>Delete account</Link>.</li>
    </ul>
  );
}

export default function WhatProfessionalsSee() {
  useHashScroll();
  return (
    <div className="min-h-screen gentle-bg" data-testid="pros-see-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6" data-testid="pros-see-back-link">
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>
        <div className="eyebrow mb-3">Privacy, in plain language</div>
        <h1 data-testid="pros-see-title" className="font-serif text-4xl sm:text-5xl text-[#1A1330] mb-3 leading-tight">What professionals can see</h1>
        <p className="text-sm text-[#857E9C] mb-6">Last updated: {UPDATED}</p>
        {ATTORNEY_REVIEW_PENDING && (
        <div data-testid="pros-see-draft-label" role="note" className="rounded-2xl border-2 border-dashed border-amber-300 bg-amber-50 p-4 flex items-start gap-3 mb-8">
          <Scale size={18} className="text-amber-800 shrink-0 mt-0.5" />
          <p className="text-[13px] text-amber-950 leading-relaxed">
            <strong>Draft, pending attorney review.</strong> This page describes how the app works today. Sections marked
            &ldquo;Attorney review&rdquo; are being checked by our attorney. It isn&rsquo;t legal advice.
          </p>
        </div>
        )}
        <H2 id="short-version">The short version</H2>
        <p data-testid="pros-see-case-exception" role="note" className="mb-4 rounded-2xl border border-[#D9CCF0] bg-[#F5F1FB] px-4 py-3 text-[15px] text-[#2A0F5F] leading-relaxed">
          <i className="fa-solid fa-briefcase mr-2" aria-hidden="true"></i>
          <strong>Case invitations and court codes.</strong> {CASE_EXCEPTION}
        </p>
        <Bullets items={SHORT_VERSION} testid="pros-see-short-version" />
        <H2 id="how">How something reaches a professional</H2>
        <div className="grid gap-4">{METHODS.map((m) => <MethodCard key={m.key} m={m} />)}</div>
        <H2 id="court" tag={<ReviewTag testid="pros-see-review-court" />}>What may appear in a court report</H2>
        <Bullets items={COURT_POINTS} testid="pros-see-court-points" />
        <H2 id="by-assessment">Assessment by assessment</H2>
        <div className="grid gap-3">{Object.entries(SHARING_NOTICES).map(([id, n]) => <NoticeCard key={id} id={id} n={n} />)}</div>
        <H2 id="controls">Your controls</H2>
        <Controls />
        <p className="mt-10 text-xs text-[#857E9C] flex items-center gap-1.5">
          <ShieldCheck size={12} /> Private by default. Shared by choice.
        </p>
      </div>
    </div>
  );
}
