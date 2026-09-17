import { useState } from "react";
import { toast } from "sonner";
import { BookmarkPlus, Trash2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";

const GROUPS = [["resources", "Resources"], ["tools", "Tools & platforms"], ["techniques", "Techniques"]];

export function ResourceLibrary({ library, onChange }) {
  const [open, setOpen] = useState(false);
  const [drafts, setDrafts] = useState({});
  const save = async (next) => {
    try { const { data } = await api.put("/me/resource-library", next); onChange(data); toast.success("Library saved"); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const add = (k) => { const v = (drafts[k] || "").trim(); if (!v) return; save({ ...library, [k]: [...(library[k] || []), v] }); setDrafts({ ...drafts, [k]: "" }); };
  const remove = (k, i) => save({ ...library, [k]: library[k].filter((_, j) => j !== i) });
  const total = GROUPS.reduce((n, [k]) => n + (library?.[k]?.length || 0), 0);
  return (
    <div className="mt-4 rounded-md border border-dashed border-border p-3" data-testid="resource-library">
      <button type="button" onClick={() => setOpen(!open)} className="flex w-full items-center justify-between text-left text-xs font-semibold" data-testid="resource-library-toggle">
        <span className="inline-flex items-center gap-1.5"><BookmarkPlus className="h-3.5 w-3.5" /> My saved resource library <span className="font-normal text-muted-foreground">({total} item{total === 1 ? "" : "s"} — auto-appear in every case's checklist)</span></span>
        <span className="text-muted-foreground">{open ? "Hide" : "Manage"}</span>
      </button>
      {open && GROUPS.map(([k, label]) => (
        <div key={k} className="mt-3" data-testid={`resource-library-group-${k}`}>
          <p className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">{label}</p>
          <ul className="mt-1 space-y-1">
            {(library?.[k] || []).map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs" data-testid={`resource-library-item-${k}`}><span className="flex-1">{item}</span><button type="button" onClick={() => remove(k, i)} aria-label="Remove" data-testid={`resource-library-remove-${k}`}><Trash2 className="h-3.5 w-3.5 text-muted-foreground" /></button></li>
            ))}
          </ul>
          <div className="mt-1.5 flex gap-2">
            <input value={drafts[k] || ""} onChange={(e) => setDrafts({ ...drafts, [k]: e.target.value })} onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add(k))} placeholder={`Add a local ${label.toLowerCase()} entry…`} className="h-8 flex-1 rounded-md border border-input bg-white px-2 text-xs" data-testid={`resource-library-input-${k}`} />
            <button type="button" onClick={() => add(k)} className="h-8 rounded-md border border-border px-2 text-xs hover:bg-secondary" data-testid={`resource-library-add-${k}`}>Save</button>
          </div>
        </div>
      ))}
    </div>
  );
}
