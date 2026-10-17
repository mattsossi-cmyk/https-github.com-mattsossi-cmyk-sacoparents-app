import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Phone, MessageSquare, Globe, LogOut, Languages } from "lucide-react";

import { api } from "../lib/api";
import { HELP_COPY, initialHelpLang, saveHelpLang } from "../lib/helpCopy";
import { isNative } from "../lib/native";
import { US_STATES, stateName } from "../lib/usStates";

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

function ServiceCard({ s, t }) {
  return (
    <li className="rounded-xl border border-[#E5E0EE] bg-white p-4" data-testid={`help-service-${s.id}`}>
      <p className="font-semibold text-[#1A1330] text-sm">{s.name}</p>
      {s.description && <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">{s.description}</p>}
      <div className="flex flex-wrap gap-3 mt-2 text-sm">
        {s.phone && <a href={`tel:${s.phone.replace(/[^\d+]/g, "")}`} className="inline-flex items-center gap-1 font-semibold text-[#3D1A78]"><Phone size={13} />{s.phone}</a>}
        {s.text && <span className="inline-flex items-center gap-1 text-[#3D1A78]"><MessageSquare size={13} />{s.text}</span>}
        {s.url && <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[#3D1A78] underline"><Globe size={13} />{t.website}</a>}
      </div>
    </li>
  );
}

function LocalServices({ t }) {
  const [all, setAll] = useState(null);
  const [state, setState] = useState("");
  // The whole list is loaded at once, so the chosen state never leaves the device.
  useEffect(() => {
    api.get("/help/local-services").then((r) => setAll(r.data.services)).catch(() => setAll([]));
  }, []);
  const shown = useMemo(() => (all || []).filter((s) => s.state === state), [all, state]);
  return (
    <section className="mt-8" data-testid="help-local">
      <h2 className="text-base md:text-lg font-bold text-[#1A1330]">{t.local}</h2>
      <label className="block text-xs font-semibold text-[#4B4567] mt-3" htmlFor="help-state">{t.chooseState}</label>
      <select id="help-state" value={state} onChange={(e) => setState(e.target.value)} data-testid="help-state-select" className="mt-1 w-full rounded-xl border border-[#D9D3EA] bg-white px-3 py-2.5 text-sm">
        <option value="">{t.selectState}</option>
        {US_STATES.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
      </select>
      {state && (
        shown.length ? (
          <ul className="mt-4 space-y-3" data-testid="help-local-list">{shown.map((s) => <ServiceCard key={s.id} s={s} t={t} />)}</ul>
        ) : (
          <p className="mt-4 text-sm text-[#4B4567]" data-testid="help-local-empty">
            {t.noLocal(stateName(state))}
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
  const [lang, setLang] = useState(initialHelpLang);
  const t = HELP_COPY[lang];
  const other = lang === "en" ? "es" : "en";
  const switchLang = () => {
    setLang(other);
    saveHelpLang(other);
  };
  return (
    <main data-testid="get-help-page" lang={lang} className="min-h-screen gentle-bg py-8 sm:py-12 pb-28">
      {covered && <div className="fixed inset-0 z-[100] bg-white" data-testid="help-privacy-cover" aria-hidden="true" />}
      <div className="max-w-xl mx-auto px-4">
        <div className="flex justify-end">
          <button type="button" onClick={switchLang} lang={other} aria-label={t.switchLabel} data-testid="help-lang-toggle" className="inline-flex min-h-6 items-center gap-1.5 rounded-full border border-[#D9D3EA] bg-white px-3 py-1.5 text-xs font-bold text-[#3D1A78] transition-colors hover:bg-[#F8F7FC]">
            <Languages size={14} aria-hidden="true" /> {t.switchTo}
          </button>
        </div>
        <h1 className="mt-2 font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight" data-testid="help-title">{t.title}</h1>
        <p className="text-sm text-[#4B4567] mt-2">{t.subtitle}</p>
        <a href="tel:911" data-testid="help-911" className="mt-6 flex items-center justify-between rounded-2xl bg-[#B71F70] px-5 py-4 text-white">
          <span><span className="block text-xs uppercase tracking-wider font-bold opacity-90">{t.danger}</span><span className="text-lg font-extrabold">{t.call911}</span></span>
          <Phone size={22} />
        </a>
        <section className="mt-4 rounded-2xl border border-[#E5E0EE] bg-white p-5" data-testid="help-hotline">
          <p className="font-semibold text-[#1A1330]">{t.hotline}</p>
          <p className="text-xs text-[#4B4567] mt-1">{t.hotlineSub}</p>
          <div className="mt-3 flex flex-col sm:flex-row gap-2">
            <a href="tel:18007997233" data-testid="help-hotline-call" className="inline-flex items-center justify-center gap-2 rounded-full bg-[#3D1A78] px-4 py-2.5 text-sm font-bold text-white"><Phone size={14} />1-800-799-7233</a>
            <a href="sms:88788?&body=START" data-testid="help-hotline-text" className="inline-flex items-center justify-center gap-2 rounded-full border border-[#3D1A78] px-4 py-2.5 text-sm font-bold text-[#3D1A78]"><MessageSquare size={14} />{t.textLine}</a>
          </div>
        </section>
        <LocalServices t={t} />
        <section className="mt-8" data-testid="help-device-guide">
          <h2 className="text-base md:text-lg font-bold text-[#1A1330]">{t.guideTitle}</h2>
          <ul className="mt-3 space-y-2 list-disc pl-5 text-sm text-[#3B3552]">{t.guide.map((g) => <li key={g}>{g}</li>)}</ul>
        </section>
        <p className="mt-8 text-sm">
          <Link to="/safety" data-testid="help-more-resources" className="font-semibold text-[#3D1A78] underline underline-offset-2">{t.more}</Link>
        </p>
      </div>
      <button type="button" onClick={quickExit} data-testid="help-quick-exit" className="fixed bottom-5 right-5 z-50 inline-flex items-center gap-2 rounded-full bg-[#1A1330] px-5 py-3 text-sm font-bold text-white shadow-lg hover:bg-black">
        <LogOut size={16} aria-hidden="true" /> {t.quickExit}
      </button>
    </main>
  );
}
