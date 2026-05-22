import React from "react";
import { Link } from "react-router-dom";
import { ShieldAlert, AlertTriangle, ExternalLink, X } from "lucide-react";
import { safetyResources } from "../lib/safety";

/**
 * Inline, dismissible safety card. Renders when `level` is "danger" or
 * "support". Designed to be discreet — never modal, never blocks input.
 */
export default function SafetyAlert({ level, onDismiss }) {
  const res = safetyResources(level);
  if (!res) return null;

  const isDanger = res.level === "danger";
  const palette = isDanger
    ? {
        wrap: "bg-[#C97B63]/10 border-[#C97B63]/40",
        icon: "text-[#C97B63]",
        title: "text-[#8B4A35]",
        body: "text-[#5C6B64]",
      }
    : {
        wrap: "bg-[#849D8E]/10 border-[#849D8E]/40",
        icon: "text-[#849D8E]",
        title: "text-[#2A3631]",
        body: "text-[#5C6B64]",
      };

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`my-4 rounded-2xl border ${palette.wrap} p-4 sm:p-5`}
      data-testid={`safety-alert-${res.level}`}
    >
      <div className="flex items-start gap-3">
        <div className={`shrink-0 ${palette.icon} pt-0.5`}>
          {isDanger ? <AlertTriangle size={20} /> : <ShieldAlert size={18} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className={`font-serif text-[16px] sm:text-[17px] ${palette.title} leading-snug`}>
              {res.title}
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                aria-label="Dismiss"
                className={`shrink-0 ${palette.body} hover:opacity-80 -mt-1 -mr-1 p-1`}
                data-testid={`safety-alert-dismiss-${res.level}`}
              >
                <X size={14} />
              </button>
            )}
          </div>
          <p className={`text-[13px] sm:text-[14px] ${palette.body} mt-1 leading-relaxed`}>
            {res.message}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {res.actions.map((a, i) => {
              const isPrimary = !!a.primary;
              const cls = isPrimary
                ? isDanger
                  ? "bg-[#C97B63] hover:bg-[#B56B53] text-white"
                  : "bg-[#849D8E] hover:bg-[#6f8576] text-white"
                : "bg-white hover:bg-[#F5F3E9] text-[#2A3631] border border-[#E8ECE9]";
              const className = `inline-flex items-center gap-1.5 text-[13px] px-3.5 py-2 rounded-full transition-colors ${cls}`;
              const testId = `safety-action-${res.level}-${i}`;
              if (a.to) {
                return (
                  <Link key={i} to={a.to} className={className} data-testid={testId}>
                    {a.label}
                  </Link>
                );
              }
              return (
                <a
                  key={i}
                  href={a.href}
                  target={a.external ? "_blank" : undefined}
                  rel={a.external ? "noopener noreferrer" : undefined}
                  className={className}
                  data-testid={testId}
                >
                  {a.label}
                  {a.external && <ExternalLink size={12} />}
                </a>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
