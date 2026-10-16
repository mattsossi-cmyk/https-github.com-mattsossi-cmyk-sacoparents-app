import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { useCaseSettings } from "../lib/useCaseSettings";

function SettingRow({ item, i }) {
  return (
    <li className="py-3.5 border-t border-[#F0EDF6] first:border-t-0" data-testid={`case-setting-${i}`}>
      <p className="text-xs font-bold uppercase tracking-wider text-[#857E9C]">{item.label}</p>
      <p className="text-sm text-[#1A1330] mt-1">{item.value}</p>
    </li>
  );
}

export default function CaseSettingsPage() {
  const settings = useCaseSettings();
  const navigate = useNavigate();
  return (
    <main data-testid="case-settings-page" className="min-h-screen gentle-bg py-8 sm:py-12">
      <div className="max-w-xl mx-auto px-4">
        <button type="button" onClick={() => navigate(-1)} data-testid="case-settings-back" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] mb-6">
          <ArrowLeft size={15} /> Back
        </button>
        <h1 className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight">Your case settings</h1>
        <p className="text-sm text-[#4B4567] mt-2">These are the features turned on for your case right now. Both parents have the same settings.</p>
        {settings?.set_by_label && (
          <p data-testid="case-settings-set-by" className="mt-4 inline-block rounded-full bg-[#F3EFFE] px-3 py-1 text-xs font-semibold text-[#3D1A78]">
            {settings.set_by_label}
          </p>
        )}
        <div className="card-soft mt-6 p-5 sm:p-6">
          {!settings ? (
            <p className="text-sm text-[#857E9C]" data-testid="case-settings-loading">Loading…</p>
          ) : (
            <ul data-testid="case-settings-list">
              {settings.settings.map((item, i) => (
                <SettingRow key={item.label} item={item} i={i} />
              ))}
            </ul>
          )}
        </div>
        <p className="text-xs text-[#857E9C] mt-5">
          Questions about these settings? Ask your professional. <Link to="/help" className="underline">Get help</Link>
        </p>
      </div>
    </main>
  );
}
