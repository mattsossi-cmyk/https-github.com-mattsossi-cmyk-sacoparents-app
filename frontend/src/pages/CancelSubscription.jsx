import React from "react";
import { Link } from "react-router-dom";
import { Check, ArrowRight, Heart } from "lucide-react";

export default function CancelSubscription() {
  return (
    <div className="min-h-screen gentle-bg">
      <header className="max-w-3xl mx-auto px-5 sm:px-6 py-5 flex items-center justify-between">
        <Link
          to="/"
          className="flex items-center gap-2.5"
          data-testid="cancel-sub-brand"
        >
          <img
            src="/saco-hero-logo.jpg"
            alt="SA CoParents"
            className="w-10 h-10 rounded-full object-cover ring-2 ring-[#3D1A78]/20"
          />
          <div className="font-sans font-extrabold text-lg text-[#1A1330]">
            <span className="text-brand-gradient">SA</span> CoParents
          </div>
        </Link>
        <Link
          to="/"
          className="text-sm text-[#4B4567] hover:text-[#1A1330] font-semibold"
        >
          ← Home
        </Link>
      </header>

      <main className="max-w-2xl mx-auto px-5 sm:px-6 py-10 fade-up">
        <div className="card-soft p-8 sm:p-10">
          <div className="eyebrow text-[#3D1A78] mb-3">Subscriptions</div>
          <h1
            className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] mb-3 tracking-tight"
            data-testid="cancel-sub-heading"
          >
            There's nothing to cancel.
          </h1>
          <p className="text-[#4B4567] text-[15px] leading-relaxed">
            SA CoParents is <strong>free to use</strong>. We don't sell subscriptions,
            we don't run trials that convert to paid plans, and we don't store any
            payment information.
          </p>

          <div className="mt-7 grid sm:grid-cols-3 gap-3">
            <div className="rounded-2xl bg-[#EFE9F9] border border-[#E5E0EE] px-4 py-4 flex flex-col items-start gap-1.5">
              <Check size={16} className="text-[#3D1A78]" />
              <div className="text-[13px] font-bold text-[#1A1330]">Free forever</div>
              <p className="text-[12px] text-[#4B4567] leading-snug">
                Every feature, no paywall.
              </p>
            </div>
            <div className="rounded-2xl bg-[#EFE9F9] border border-[#E5E0EE] px-4 py-4 flex flex-col items-start gap-1.5">
              <Check size={16} className="text-[#3D1A78]" />
              <div className="text-[13px] font-bold text-[#1A1330]">No payments</div>
              <p className="text-[12px] text-[#4B4567] leading-snug">
                We never ask for a card.
              </p>
            </div>
            <div className="rounded-2xl bg-[#EFE9F9] border border-[#E5E0EE] px-4 py-4 flex flex-col items-start gap-1.5">
              <Check size={16} className="text-[#3D1A78]" />
              <div className="text-[13px] font-bold text-[#1A1330]">No ads</div>
              <p className="text-[12px] text-[#4B4567] leading-snug">
                Privacy by default.
              </p>
            </div>
          </div>

          <div className="mt-8 rounded-2xl bg-white border border-[#E5E0EE] p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <Heart size={18} className="text-[#3D1A78] mt-0.5 shrink-0" />
              <div>
                <div className="font-sans font-bold text-[#1A1330] mb-1">
                  Looking to stop using the app entirely?
                </div>
                <p className="text-[14px] text-[#4B4567] leading-relaxed">
                  If you want us to remove your account and all the answers you've
                  written, you can do that anytime — instantly, no questions asked.
                </p>
                <Link
                  to="/delete-account"
                  className="inline-flex items-center gap-2 mt-4 text-[14px] font-bold text-[#3D1A78] hover:underline"
                  data-testid="cancel-sub-delete-link"
                >
                  Delete my account <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>

          <p className="text-[12px] text-[#857E9C] mt-8 leading-relaxed">
            If a future paid tier is ever added, the cancel option will appear here.
            Until then, you'll never see a charge from us.
          </p>
        </div>

        <div className="text-center mt-8 text-[12px] text-[#857E9C]">
          Questions?{" "}
          <a
            href="mailto:mattsossi@bsossi.com"
            className="text-[#3D1A78] font-semibold hover:underline"
          >
            mattsossi@bsossi.com
          </a>
        </div>
      </main>
    </div>
  );
}
