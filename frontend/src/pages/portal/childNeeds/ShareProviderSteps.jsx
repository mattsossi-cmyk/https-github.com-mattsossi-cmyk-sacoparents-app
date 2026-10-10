import React from "react";
import { Link } from "react-router-dom";

import CONTENT from "../childNeedsContent.json";
import { ProSeeLink } from "../../../components/privacy/ProSeeLink";

export const TITLES = Object.fromEntries(CONTENT.categories.map((c) => [c.key, c.card_title]));
const rowCls = (on) =>
  `w-full flex items-start gap-3 text-left rounded-lg border-2 px-3.5 py-2.5 transition-colors ${on ? "border-[#4A154B] bg-[#F4EEF5]" : "border-[#E2E8F0] bg-white hover:border-[#611663]"}`;

export function ProviderPicker({ providers, pickedId, onPick }) {
  if (providers === null) return <p data-testid="share-provider-loading" className="text-sm text-slate-500"><i className="fa-solid fa-spinner fa-spin mr-1.5"></i>Loading your professionals…</p>;
  if (providers.length === 0) {
    return (
      <div data-testid="share-provider-empty" className="rounded-lg bg-[#FBF9FC] border border-[#E2E8F0] p-4 text-sm text-slate-600">
        <p>No professional has accepted one of your invitations yet. Invite your child's school, doctor or therapist first. Once they accept, they'll show up here.</p>
        <Link to="/share/professional" data-testid="share-provider-invite-link" className="inline-block mt-3 font-bold text-[#4A154B] underline underline-offset-2">
          Share with a Professional
        </Link>
      </div>
    );
  }
  return (
    <div role="radiogroup" className="space-y-2">
      {providers.map((p) => (
        <button key={p.provider_id} type="button" role="radio" aria-checked={pickedId === p.provider_id} data-testid={`share-provider-${p.provider_id}`} onClick={() => onPick(p.provider_id)} className={rowCls(pickedId === p.provider_id)}>
          <i className={`fa-solid ${pickedId === p.provider_id ? "fa-circle-dot text-[#4A154B]" : "fa-circle text-slate-300"} mt-0.5`}></i>
          <span className="min-w-0">
            <span className="block text-sm font-bold text-slate-900">{p.name}</span>
            <span className="block text-[12px] text-slate-500 break-words">{[p.role_label, p.organization, p.email].filter(Boolean).join(" · ")}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

export function FormTicks({ completed, picked, onToggle, onAll }) {
  const all = completed.every((k) => picked.includes(k));
  return (
    <div className="space-y-2">
      {completed.map((k) => (
        <label key={k} data-testid={`share-form-${k}`} className={`${rowCls(picked.includes(k))} cursor-pointer items-center`}>
          <input type="checkbox" data-testid={`share-form-${k}-tick`} checked={picked.includes(k)} onChange={() => onToggle(k)} className="w-4 h-4 accent-[#4A154B]" />
          <span className="text-sm font-semibold text-slate-800">{TITLES[k]}</span>
        </label>
      ))}
      {completed.length > 1 && (
        <button type="button" data-testid="share-form-select-all" onClick={onAll} className="text-[12px] font-bold text-[#611663] hover:underline">
          {all ? "Clear all" : "Select all (full report)"}
        </button>
      )}
    </div>
  );
}

export function ConfirmStep({ provider, keys }) {
  return (
    <div data-testid="share-confirm" className="space-y-3 text-sm">
      <div className="rounded-lg border border-[#E2E8F0] p-3.5">
        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Who gets it</p>
        <p data-testid="share-confirm-provider" className="font-bold text-slate-900">{provider.name}</p>
        <p className="text-[12px] text-slate-500 break-words">{[provider.role_label, provider.organization, provider.email].filter(Boolean).join(" · ")}</p>
        <p className="mt-3 text-[11px] font-bold uppercase tracking-wider text-slate-500">What they get (one PDF)</p>
        <ul data-testid="share-confirm-forms" className="list-disc pl-5 text-slate-800">
          {keys.map((k) => <li key={k}>{TITLES[k]}</li>)}
        </ul>
      </div>
      <p data-testid="share-confirm-reminder" className="rounded-lg bg-amber-50 border border-amber-200 text-amber-900 p-3 text-[12.5px] leading-relaxed">
        <i className="fa-solid fa-triangle-exclamation mr-1.5"></i>
        The email won&rsquo;t contain the report. {provider.name} gets a private link and a one-time code to open it, and can download it after that. Once downloaded, it can&rsquo;t be unsent, but you can cancel the link before then.
      </p>
      <ProSeeLink testid="share-confirm-pros-see-link" area="child-needs" className="text-[12.5px]" />
    </div>
  );
}
