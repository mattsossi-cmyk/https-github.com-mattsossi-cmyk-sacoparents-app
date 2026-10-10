import React from "react";

// Rarely / Sometimes / Often / Consistently grid for consecutive "rating" questions.
export function RatingMatrix({ label, fields, scale, values, onChange }) {
  return (
    <div>
      <p className="text-[13px] font-bold text-slate-700 mb-1.5">{label}</p>
      <div className="overflow-x-auto">
        <table data-testid="child-needs-rating-matrix" className="w-full border-collapse text-[12px]">
          <thead>
            <tr>
              <th className="text-left py-2 pr-2 w-[38%] sm:w-1/2 font-semibold text-slate-500">Indicator</th>
              {scale.map((s) => (
                <th key={s} className="py-2 px-0.5 text-center font-semibold text-slate-500 text-[9.5px] sm:text-[11px]">
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fields.map((f) => (
              <tr key={f.id} data-field={f.id} className="border-t border-slate-200">
                <td className="py-2.5 pr-2 font-medium text-slate-800">{f.label}</td>
                {scale.map((s) => (
                  <td key={s} className="text-center">
                    <input
                      type="radio"
                      name={f.id}
                      value={s}
                      checked={values[f.id] === s}
                      onChange={() => onChange(f.id, s)}
                      data-testid={`child-needs-rate-${f.id}-${s.toLowerCase()}`}
                      aria-label={`${f.label}: ${s}`}
                      className="w-4 h-4 accent-[#4A154B] cursor-pointer"
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
