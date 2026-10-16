import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Phone, MessageSquare, Globe, LogOut } from "lucide-react";

import { api } from "../lib/api";
import { isNative } from "../lib/native";
import { US_STATES, stateName } from "../lib/usStates";

const GUIDE = [
  "Use a phone, computer and email account that only you can get into. Change passwords someone else might know.",
  "Turn off location sharing you don't need, and check which apps and people can see where you are.",
  "Look for linked devices, email forwarding rules or recovery numbers you don't recognize.",
  "Sign out when you're done, especially on a shared device.",
  "Your browser keeps a history. Use a private window, or clear your history if that's safe for you.",
  "Quick exit opens the calendar right away, and Back won't bring you here.",
];

// Hides the page while the app is in the background, so app-switcher previews don't show it.
function usePrivacyCover() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const hide = () => setHidden(true);
    const show = () => setHidden(document.visibilityState === "hidden");
    document.addEventListener("visibilitychange", show);
    window.addEventListener("blur", hide);
    window.addEventListener("focus", show);
    window.addEventListener("pagehide", hide);
    return () => {
      document.removeEventListener("visibilitychange", show);
      window.removeEventListener("blur", hide);
      window.removeEventListener("focus", show);
      window.removeEventListener("pagehide", hide);
    };
  }, []);
  return hidden;
}

// In the installed app, blocks screenshots and blurs the app-switcher preview while this page is open.
function useNativePrivacyScreen() {
  useEffect(() => {
    if (!isNative()) return undefined;
    let mod = null;
    import("@capacitor/privacy-screen")
      .then((m) => {
        mod = m;
        return m.PrivacyScreen.enable({ android: { preventScreenshots: true, privacyModeOnActivityHidden: "splash" }, ios: { blurEffect: "light" } });
      })
      .catch(() => {});
    return () => {
      mod?.PrivacyScreen.disable().catch(() => {});
    };
  }, []);
}

function ServiceCard({ s }) {
  return (
    <li className="rounded-xl border border-[#E5E0EE] bg-white p-4" data-testid={`help-service-${s.id}`}>
      <p className="font-semibold text-[#1A1330] text-sm">{s.name}</p>
      {s.description && <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">{s.description}</p>}
      <div className="flex flex-wrap gap-3 mt-2 text-sm">
        {s.phone && <a href={`tel:${s.phone.replace(/[^\d+]/g, "")}`} className="inline-flex items-center gap-1 font-semibold text-[#3D1A78]"><Phone size={13} />{s.phone}</a>}
        {s.text && <span className="inline-flex items-center gap-1 text-[#3D1A78]"><MessageSquare size={13} />{s.text}</span>}
        {s.url && <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[#3D1A78] underline"><Globe size={13} />Website</a>}
      </div>
    </li>
  );
}

function LocalServices() {
  const [all, setAll] = useState(null);
  const [state, setState] = useState("");
  // The whole list is loaded at once, so the chosen state never leaves the device.
  useEffect(() => {
    api.get("/help/local-services").then((r) => setAll(r.data.services)).catch(() => setAll([]));
  }, []);
  const shown = useMemo(() => (all || []).filter((s) => s.state === state), [all, state]);
  return (
    <section className="mt-8" data-testid="help-local">
      <h2 className="text-base md:text-lg font-bold text-[#1A1330]">Local services</h2>
      <label className="block text-xs font-semibold text-[#4B4567] mt-3" htmlFor="help-state">Choose your state</label>
      <select id="help-state" value={state} onChange={(e) => setState(e.target.value)} data-testid="help-state-select" className="mt-1 w-full rounded-xl border border-[#D9D3EA] bg-white px-3 py-2.5 text-sm">
        <option value="">Select a state</option>
        {US_STATES.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
      </select>
      {state && (
        shown.length ? (
          <ul className="mt-4 space-y-3" data-testid="help-local-list">{shown.map((s) => <ServiceCard key={s.id} s={s} />)}</ul>
        ) : (
          <p className="mt-4 text-sm text-[#4B4567]" data-testid="help-local-empty">
            No local services are listed for {stateName(state)} yet. The National Domestic Violence Hotline can connect you with help near you.
          </p>
        )
      )}
    </section>
  );
}

export default function GetHelp() {
  const navigate = useNavigate();
  const covered = usePrivacyCover();
  useNativePrivacyScreen();
  const quickExit = () => navigate("/calendar", { replace: true });
  return (
    <main data-testid="get-help-page" className="min-h-screen gentle-bg py-8 sm:py-12 pb-28">
      {covered && <div className="fixed inset-0 z-[100] bg-white" data-testid="help-privacy-cover" aria-hidden="true" />}
      <div className="max-w-xl mx-auto px-4">
        <h1 className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight">Get help</h1>
        <p className="text-sm text-[#4B4567] mt-2">Free, confidential help is available any time.</p>
        <a href="tel:911" data-testid="help-911" className="mt-6 flex items-center justify-between rounded-2xl bg-[#B71F70] px-5 py-4 text-white">
          <span><span className="block text-xs uppercase tracking-wider font-bold opacity-90">In danger right now</span><span className="text-lg font-extrabold">Call 911</span></span>
          <Phone size={22} />
        </a>
        <section className="mt-4 rounded-2xl border border-[#E5E0EE] bg-white p-5" data-testid="help-hotline">
          <p className="font-semibold text-[#1A1330]">National Domestic Violence Hotline</p>
          <p className="text-xs text-[#4B4567] mt-1">24/7, free and confidential.</p>
          <div className="mt-3 flex flex-col sm:flex-row gap-2">
            <a href="tel:18007997233" data-testid="help-hotline-call" className="inline-flex items-center justify-center gap-2 rounded-full bg-[#3D1A78] px-4 py-2.5 text-sm font-bold text-white"><Phone size={14} />1-800-799-7233</a>
            <a href="sms:88788?&body=START" data-testid="help-hotline-text" className="inline-flex items-center justify-center gap-2 rounded-full border border-[#3D1A78] px-4 py-2.5 text-sm font-bold text-[#3D1A78]"><MessageSquare size={14} />Text START to 88788</a>
          </div>
        </section>
        <LocalServices />
        <section className="mt-8" data-testid="help-device-guide">
          <h2 className="text-base md:text-lg font-bold text-[#1A1330]">Keeping your device and account private</h2>
          <ul className="mt-3 space-y-2 list-disc pl-5 text-sm text-[#3B3552]">{GUIDE.map((g) => <li key={g}>{g}</li>)}</ul>
        </section>
        <p className="mt-8 text-sm">
          <Link to="/safety" data-testid="help-more-resources" className="font-semibold text-[#3D1A78] underline underline-offset-2">More hotlines and resources</Link>
        </p>
      </div>
      <button type="button" onClick={quickExit} data-testid="help-quick-exit" className="fixed bottom-5 right-5 z-50 inline-flex items-center gap-2 rounded-full bg-[#1A1330] px-5 py-3 text-sm font-bold text-white shadow-lg hover:bg-black">
        <LogOut size={16} /> Quick exit
      </button>
    </main>
  );
}
