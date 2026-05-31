import React from "react";
import { Facebook, Radio } from "lucide-react";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL || "https://www.facebook.com/SACoparent";

/**
 * Embeds Facebook's Page Plugin iframe.
 *
 * - When the page is LIVE, Facebook automatically surfaces the live video
 *   at the top of the timeline tab — no extra wiring needed.
 * - Uses both the `timeline` and `events` tabs so upcoming live sessions
 *   appear too.
 * - No FB SDK / no app ID needed — this is the public, anonymous embed.
 */
export default function FacebookFeed() {
  const encoded = encodeURIComponent(FB_URL);
  const src =
    `https://www.facebook.com/plugins/page.php` +
    `?href=${encoded}` +
    `&tabs=timeline%2Cevents` +
    `&width=500` +
    `&height=560` +
    `&small_header=false` +
    `&adapt_container_width=true` +
    `&hide_cover=false` +
    `&show_facepile=true` +
    `&hide_cta=false`;

  return (
    <section
      className="max-w-7xl mx-auto px-5 sm:px-6 py-16 sm:py-20"
      data-testid="facebook-feed-section"
    >
      <div className="grid lg:grid-cols-12 gap-10 items-center">
        {/* Copy / intro */}
        <div className="lg:col-span-5">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#1877F2]/10 text-[#1877F2] text-[11px] uppercase tracking-[0.2em] mb-4">
            <Radio size={12} />
            Live on Facebook
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#1A1330] tracking-tight leading-tight">
            Join the conversation —{" "}
            <span className="text-brand-gradient">@SACoparent</span>
          </h2>
          <p className="text-[#4B4567] mt-4 leading-relaxed max-w-md">
            Follow along for live sessions on co-parenting, mediation prep, and
            real questions from real parents. When we go live, you'll see it
            appear right here.
          </p>
          <a
            href={FB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 mt-6 px-5 py-2.5 rounded-full bg-[#1877F2] text-white text-sm font-semibold hover:bg-[#1565d8] active:scale-95 transition"
            data-testid="facebook-follow-link"
          >
            <Facebook size={14} /> Follow on Facebook
          </a>
          <p className="text-[11px] text-[#857E9C] mt-4 leading-relaxed">
            We never post about specific users. Everything you see is general
            parenting and co-parenting guidance.
          </p>
        </div>

        {/* iframe */}
        <div className="lg:col-span-7">
          <div
            className="rounded-2xl overflow-hidden bg-white border border-[#E5E0EE] shadow-sm"
            style={{ minHeight: 560 }}
          >
            <iframe
              title="SA Coparents on Facebook"
              src={src}
              width="500"
              height="560"
              style={{
                border: "none",
                overflow: "hidden",
                width: "100%",
                maxWidth: "500px",
                display: "block",
                margin: "0 auto",
              }}
              scrolling="no"
              frameBorder="0"
              allowFullScreen
              allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
              loading="lazy"
              data-testid="facebook-feed-iframe"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
