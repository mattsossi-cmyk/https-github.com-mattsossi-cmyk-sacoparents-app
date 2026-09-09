/**
 * EcosystemStrip — the compact 3-node band showing the relationship
 * between the two sibling sites and the child-focused outcome.
 *
 * Renders in TWO placements today:
 *  1. Landing.jsx — directly under the Hero (large / expanded copy).
 *  2. Dashboard.jsx — under the Four-Circle Front Door (compact
 *     variant so it doesn't compete with the primary picker).
 *
 * Pass `variant="compact"` on the dashboard to shrink typography and
 * hide the heading strip; the ecosystem itself is unchanged.
 */
import React from "react";
import { Heart, Briefcase, Award, ArrowRight, ArrowDown } from "lucide-react";

export function EcosystemStrip({ variant = "default" }) {
  const isCompact = variant === "compact";
  return (
    <section
      id="ecosystem-flow"
      className={
        isCompact
          ? "relative py-4 sm:py-5"
          : "relative py-12 sm:py-14 bg-[#FBFAFE] border-b border-[#EFE9F9]"
      }
      data-testid="ecosystem-flow"
      data-variant={variant}
    >
      <div className={isCompact ? "" : "max-w-6xl mx-auto px-4 sm:px-6"}>
        {!isCompact && (
          <div className="text-center max-w-2xl mx-auto mb-8">
            <div className="text-[11px] tracking-[0.28em] uppercase font-bold text-[#3D1A78] mb-3">
              The SA CoParents Ecosystem
            </div>
            <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug">
              Two sibling tools. One child-focused outcome.
            </h2>
          </div>
        )}

        <div
          className={
            isCompact
              ? "grid md:grid-cols-[1fr_auto_1fr_auto_1fr] items-stretch gap-2 md:gap-2"
              : "grid md:grid-cols-[1fr_auto_1fr_auto_1fr] items-stretch gap-4 md:gap-3"
          }
        >
          <article
            className={
              (isCompact
                ? "rounded-2xl border border-[#3D1A78]/25 bg-white p-3 sm:p-4 flex flex-col"
                : "rounded-2xl border-2 border-[#3D1A78]/25 bg-white p-5 sm:p-6 flex flex-col")
            }
            data-testid="ecosystem-node-parents"
          >
            <div className="text-[9px] sm:text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              sacoparentsapp.online
            </div>
            <div className="mt-1 flex items-center gap-2">
              <Heart size={isCompact ? 14 : 16} className="text-[#3D1A78]" />
              <div
                className={
                  isCompact
                    ? "font-serif text-[15px] text-[#1A1330]"
                    : "font-serif text-lg text-[#1A1330]"
                }
              >
                For Parents
              </div>
            </div>
            <div
              className={
                isCompact
                  ? "mt-1.5 text-[11px] text-[#4B4567] leading-relaxed"
                  : "mt-3 text-[13px] text-[#4B4567] leading-relaxed"
              }
            >
              Reflect · Identify Needs · Build Foundation · Prepare
            </div>
          </article>

          <div
            className="hidden md:flex items-center justify-center text-[#3D1A78]"
            aria-hidden
          >
            <ArrowRight size={isCompact ? 16 : 20} strokeWidth={2.2} />
          </div>
          <div
            className="md:hidden flex items-center justify-center text-[#3D1A78]"
            aria-hidden
          >
            <ArrowDown size={isCompact ? 14 : 18} strokeWidth={2.2} />
          </div>

          <article
            className={
              isCompact
                ? "rounded-2xl border border-[#2DB5B5]/30 bg-white p-3 sm:p-4 flex flex-col"
                : "rounded-2xl border-2 border-[#2DB5B5]/30 bg-white p-5 sm:p-6 flex flex-col"
            }
            data-testid="ecosystem-node-professionals"
          >
            <div className="text-[9px] sm:text-[10px] uppercase tracking-[0.22em] font-bold text-[#0E7A7A]">
              sacoparentsalign.com
            </div>
            <div className="mt-1 flex items-center gap-2">
              <Briefcase size={isCompact ? 14 : 16} className="text-[#0E7A7A]" />
              <div
                className={
                  isCompact
                    ? "font-serif text-[15px] text-[#1A1330]"
                    : "font-serif text-lg text-[#1A1330]"
                }
              >
                For Professionals
              </div>
            </div>
            <div
              className={
                isCompact
                  ? "mt-1.5 text-[11px] text-[#4B4567] leading-relaxed"
                  : "mt-3 text-[13px] text-[#4B4567] leading-relaxed"
              }
            >
              Invite · Compare · Identify Alignment · Guide Conversation
            </div>
          </article>

          <div
            className="hidden md:flex items-center justify-center text-[#3D1A78]"
            aria-hidden
          >
            <ArrowRight size={isCompact ? 16 : 20} strokeWidth={2.2} />
          </div>
          <div
            className="md:hidden flex items-center justify-center text-[#3D1A78]"
            aria-hidden
          >
            <ArrowDown size={isCompact ? 14 : 18} strokeWidth={2.2} />
          </div>

          <article
            className={
              isCompact
                ? "rounded-2xl border border-[#B85B00]/30 bg-white p-3 sm:p-4 flex flex-col"
                : "rounded-2xl border-2 border-[#B85B00]/30 bg-white p-5 sm:p-6 flex flex-col"
            }
            data-testid="ecosystem-node-result"
          >
            <div className="text-[9px] sm:text-[10px] uppercase tracking-[0.22em] font-bold text-[#B85B00]">
              The Result
            </div>
            <div className="mt-1 flex items-center gap-2">
              <Award size={isCompact ? 14 : 16} className="text-[#B85B00]" />
              <div
                className={
                  isCompact
                    ? "font-serif text-[15px] text-[#1A1330]"
                    : "font-serif text-lg text-[#1A1330]"
                }
              >
                Better Child-Focused Agreements
              </div>
            </div>
            <div
              className={
                isCompact
                  ? "mt-1.5 text-[11px] text-[#4B4567] leading-relaxed"
                  : "mt-3 text-[13px] text-[#4B4567] leading-relaxed"
              }
            >
              Clearer priorities, shared understanding, healthier outcomes
              for the child.
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}

export default EcosystemStrip;
