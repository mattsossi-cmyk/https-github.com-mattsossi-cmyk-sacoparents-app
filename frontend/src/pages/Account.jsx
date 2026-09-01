/**
 * Account — dedicated settings hub.
 *
 * Currently hosts:
 *   * Basic account info (name + email)
 *   * Communication preferences (HB 300 marketing opt-in)
 *   * Deep links out to the more specialised pages
 *     (Data & Retention, HB 300 Notice, Privacy Policy)
 *
 * Deliberately compact. Additional preference blocks (theme,
 * notification cadence, etc.) can drop in as sibling sections.
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, User as UserIcon, Shield, Database, FileText } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import MarketingConsentToggle from "../components/account/MarketingConsentToggle";


function LinkTile({ to, icon, label, desc, testid }) {
  return (
    <Link
      to={to}
      data-testid={testid}
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#FBFAFD] transition-colors flex items-start gap-3"
    >
      <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-sm font-semibold text-[#1A1330]">{label}</div>
        <div className="text-xs text-[#4B4567] mt-0.5 leading-relaxed">{desc}</div>
      </div>
    </Link>
  );
}


export default function Account() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen gentle-bg" data-testid="account-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="account-back-link"
        >
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>

        <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
          Your Account
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          Settings &amp; preferences.
        </h1>
        <p className="text-sm text-[#4B4567] mt-2 max-w-xl leading-relaxed">
          Manage how SA CoParents talks to you and how your data is
          handled. Every preference change is logged so you always have
          a paper trail.
        </p>

        {/* Basic identity */}
        <section
          className="mt-8 rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5"
          data-testid="account-identity"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]">
              <UserIcon size={15} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
                Identity
              </div>
              <div className="text-sm font-semibold text-[#1A1330] mt-0.5">
                {user?.name || "—"}
              </div>
              <div
                className="text-xs text-[#4B4567] truncate"
                data-testid="account-email"
              >
                {user?.email || ""}
              </div>
            </div>
          </div>
        </section>

        {/* Communication preferences (HB 300 marketing toggle) */}
        <section className="mt-4">
          <MarketingConsentToggle />
        </section>

        {/* Related settings pages */}
        <section className="mt-4 grid sm:grid-cols-2 gap-3">
          <LinkTile
            to="/data-retention"
            icon={<Database size={15} />}
            label="Data &amp; Retention"
            desc="How long each type of data lives — and how to export or delete it."
            testid="account-data-retention-link"
          />
          <LinkTile
            to="/hb300-notice"
            icon={<Shield size={15} />}
            label="Texas HB 300 Notice"
            desc="How we treat co-parenting data as Protected Health Information."
            testid="account-hb300-link"
          />
          <LinkTile
            to="/privacy"
            icon={<FileText size={15} />}
            label="Privacy Policy"
            desc="Full policy: what we collect, why, and your rights."
            testid="account-privacy-link"
          />
        </section>
      </div>
    </div>
  );
}
