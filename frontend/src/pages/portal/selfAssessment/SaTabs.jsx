import React from "react";

const TABS = [
  { key: "results", label: "My results", icon: "fa-chart-simple" },
  { key: "progress", label: "Progress over time", icon: "fa-chart-line" },
];

// Results / Progress over time switch shown once a Self-Assessment is finished.
export function SaTabs({ tab, onTab }) {
  return (
    <div role="tablist" className="grid grid-cols-2 gap-1 p-1 rounded-full bg-purple-50 border border-purple-100 mb-4">
      {TABS.map((t) => {
        const on = tab === t.key;
        return (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={on}
            data-testid={`sa-tab-${t.key}`}
            onClick={() => onTab(t.key)}
            className={`rounded-full py-2 px-3 text-[0.75rem] font-bold transition-colors ${on ? "bg-[#4c2889] text-white shadow" : "text-purple-900 hover:bg-white"}`}
          >
            <i className={`fa-solid ${t.icon} mr-1.5`} aria-hidden="true"></i>
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
