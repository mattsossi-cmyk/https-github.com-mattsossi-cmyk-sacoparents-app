import { useEffect, useState } from "react";
import { Eye } from "lucide-react";
import api from "@/lib/api";

// Parent-facing, read-only list of every recorded professional/admin opening of this parent's information.
export const WhoLooked = ({ rid }) => {
  const [data, setData] = useState(null);
  useEffect(() => { api.get(`/joint/reports/${rid}/safety-screening/who-looked`).then((r) => setData(r.data)).catch(() => setData({ events: [] })); }, [rid]);
  if (!data) return null;
  const fmt = (iso) => { try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); } catch { return iso; } };
  return (
    <section id="who-looked" className="rounded-2xl border border-[#3D1A78]/15 bg-white p-5" data-testid="who-looked">
      <h2 className="flex items-center gap-2 text-base font-bold text-[#3D1A78] md:text-lg"><Eye className="h-5 w-5" aria-hidden="true" /> Who has looked at my information</h2>
      <p className="mt-1 text-sm text-slate-600">{data.note}</p>
      {data.events?.length ? (
        <ul className="mt-3 divide-y divide-slate-100" data-testid="who-looked-list">
          {data.events.map((e, i) => (
            <li key={i} className="flex flex-col gap-0.5 py-2 text-sm sm:flex-row sm:items-baseline sm:justify-between" data-testid="who-looked-row">
              <span><span className="font-semibold">{e.viewer}</span> <span className="text-slate-500">· {e.viewer_role}</span></span>
              <span className="text-slate-600">{e.what} · <time dateTime={e.at}>{fmt(e.at)}</time></span>
            </li>
          ))}
        </ul>
      ) : <p className="mt-3 text-sm text-slate-500" data-testid="who-looked-empty">No one has opened your information yet.</p>}
    </section>
  );
};
