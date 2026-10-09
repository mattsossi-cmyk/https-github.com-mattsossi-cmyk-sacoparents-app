import React from "react";
import { createPortal } from "react-dom";

import { GuideChat } from "../guide/GuideChat";
import { Hero, PageHeader, SafetyBanner, useLockScroll } from "../selfAssessment/SaChrome";
import { ArtPicture } from "./ArtPicture";

// Full-screen Self Journey option page (Communication Builder / Court Path layout): work on the left,
// picture with tap spots + remembered Guide chat on the right. Phones: picture first, then work, then chat.
export function JourneyPage({ tp, hero, art, onArt, artState = {}, chat, chatProps, onBack, onQuickExit, hidden = false, footer, children }) {
  useLockScroll(!hidden);
  return createPortal(
    <div
      id={`${tp}-page`}
      data-testid={`${tp}-page`}
      className={`fixed inset-0 z-50 overflow-y-auto bg-gradient-to-b from-[#F3EFFE] to-[#EBE5FA] text-slate-800 pb-12 ${hidden ? "hidden" : ""}`}
    >
      <SafetyBanner tp={tp} />
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <PageHeader tp={tp} onBack={onBack} onQuickExit={onQuickExit} backLabel="Back" />
        <Hero tp={tp} textClassName="hidden lg:block" {...hero} />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="contents lg:block lg:col-start-8 lg:col-span-5 lg:row-start-1 lg:space-y-6">
            <div className="order-first">
              <ArtPicture tp={`${tp}-art`} art={art} onAction={onArt} {...artState} />
            </div>
            <div className="order-last">
              <GuideChat chat={chat} tp={tp} {...chatProps} />
            </div>
          </div>
          <div className="lg:col-start-1 lg:col-span-7 lg:row-start-1 space-y-6 min-w-0">{children}</div>
        </div>
        <p data-testid={`${tp}-footer`} className="mt-12 text-center text-xs text-[#5f6368] font-medium">
          &copy; SA CoParents &bull; {footer} &bull; Powered by Emergent AI &bull; General guidance, not legal advice
        </p>
      </div>
    </div>,
    document.body
  );
}
