import React, { useState } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";

import { useAuth } from "../../context/AuthContext";

// Short Professional Access Notice for the dashboard; the parent can hide it (the footer link stays).
export function ProfessionalAccessCard() {
  const { user, loading } = useAuth();
  const [, rerender] = useState(0);
  const key = `sacoparents_pan_hidden:${user?.user_id || "guest"}`;
  if (loading || localStorage.getItem(key) === "1") return null;
  const hide = () => {
    localStorage.setItem(key, "1");
    rerender((n) => n + 1);
  };
  return (
    <section
      data-testid="professional-access-card"
      aria-labelledby="professional-access-card-title"
      className="relative rounded-2xl border border-purple-200 bg-[#F5F1FB] px-4 py-3 pr-11 text-[0.8125rem] leading-relaxed text-[#2A0F5F]"
    >
      <h2 id="professional-access-card-title" className="font-bold text-sm">
        <i className="fa-solid fa-user-shield mr-1.5" aria-hidden="true"></i>Who can see your information
      </h2>
      <p className="mt-1">
        Safety questions are answered privately on SACOparentsAlign, not in this app. Your co-parent never sees your answers. This
        app&apos;s reports show only &ldquo;Safety step: completed on SACOparentsAlign&rdquo; or &ldquo;Safety step: see SACOparentsAlign&rdquo;.
      </p>
      <Link
        to="/who-can-see-my-information"
        data-testid="professional-access-card-link"
        className="inline-block mt-1 font-semibold text-[#3D1A78] underline underline-offset-2"
      >
        Who can see my information
      </Link>
      <button
        type="button"
        onClick={hide}
        data-testid="professional-access-card-hide"
        aria-label="Hide this card"
        className="absolute top-2 right-2 w-9 h-9 grid place-items-center rounded-full text-[#4B4567] hover:bg-white transition-colors"
      >
        <X size={16} aria-hidden="true" />
      </button>
    </section>
  );
}
