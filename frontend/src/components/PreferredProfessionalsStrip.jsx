/**
 * PreferredProfessionalsStrip — small directory row shown near the
 * hero on `/for-professionals`. Purpose: a mediator / attorney /
 * therapist landing on the page sees at a glance that real
 * practitioners already use the tool.
 *
 * Data source: the existing PUBLIC `GET /api/professionals` endpoint
 * (no auth required). If the endpoint fails or returns zero rows the
 * strip renders NOTHING — we never want a broken tile on a marketing
 * page.
 *
 * Kept deliberately compact: name + credentials + city/state + a
 * single email CTA. No bios, no LinkedIn, no photos — the full
 * public directory already exists at `/professionals` for parents.
 */
import React, { useEffect, useState } from "react";
import { MapPin, Mail } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

export default function PreferredProfessionalsStrip() {
  const [professionals, setProfessionals] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/professionals")
      .then((r) => {
        if (cancelled) return;
        const list = Array.isArray(r?.data?.professionals) ? r.data.professionals : [];
        setProfessionals(list);
      })
      .catch((err) => {
        if (cancelled) return;
        logError("preferred professionals fetch failed", err);
        // Silent — the whole strip stays hidden below.
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Skip render until data is in and non-empty. We deliberately do NOT
  // reserve layout space so the page never shows a broken skeleton.
  if (!loaded || professionals.length === 0) return null;

  return (
    <section
      className="px-5 sm:px-8 py-10 sm:py-12 bg-[#FAF8FD] border-b border-[#E5E0EE]"
      data-testid="for-pros-preferred-strip"
    >
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-5">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Practitioners already using SA CoParents
            </div>
            <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug mt-1">
              Preferred professionals
            </h2>
          </div>
          <a
            href="/professionals"
            className="text-xs font-semibold text-[#3D1A78] hover:underline"
            data-testid="for-pros-preferred-strip-directory-link"
          >
            View full directory →
          </a>
        </div>

        <ul
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
          data-testid="for-pros-preferred-strip-list"
        >
          {professionals.slice(0, 6).map((p) => (
            <li
              key={p.professional_id}
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4 flex flex-col"
              data-testid={`for-pros-preferred-card-${p.professional_id}`}
            >
              <div className="font-serif text-[16px] text-[#1A1330] leading-snug">
                {p.name}
              </div>
              {p.credentials && (
                <div className="text-[11px] text-[#4B4567] mt-1 leading-relaxed">
                  {p.credentials}
                </div>
              )}
              <div className="mt-2 flex items-center gap-1 text-[11px] text-[#857E9C]">
                <MapPin size={11} />
                {(p.city && p.state)
                  ? `${p.city}, ${p.state}`
                  : (p.city || p.state || "United States")}
              </div>
              {p.email && (
                <a
                  href={`mailto:${p.email}?subject=SA%20CoParents%20-%20Professional%20enquiry`}
                  className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-semibold text-[#3D1A78] hover:underline"
                  data-testid={`for-pros-preferred-card-${p.professional_id}-email`}
                >
                  <Mail size={12} /> {p.email}
                </a>
              )}
            </li>
          ))}
        </ul>

        <p
          className="mt-4 text-[11px] text-[#857E9C] leading-relaxed"
          data-testid="for-pros-preferred-strip-fineprint"
        >
          Practitioners listed above have opted into the SA CoParents
          directory. Interested in being listed? Contact us via the
          email link above.
        </p>
      </div>
    </section>
  );
}
