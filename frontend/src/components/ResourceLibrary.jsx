import { useState } from "react";
import { toast } from "sonner";
import { BookmarkPlus, Building2, Trash2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";

const GROUPS = [["resources", "Resources"], ["tools", "Tools & platforms"], ["techniques", "Techniques"]];

function LibraryEditor({ id, library, onSave, canEdit = true, placeholderPrefix }) {
  const [drafts, setDrafts] = useState({});
  const add = (k) => { const v = (drafts[k] || "").trim(); if (!v) return; onSave({ ...library, [k]: [...(library[k] || []), v] }); setDrafts({ ...drafts, [k]: "" }); };
  const remove = (k, i) => onSave({ ...library, [k]: library[k].filter((_, j) => j !== i) });
  return GROUPS.map(([k, label]) => (
    <div key={k} className="mt-3" data-testid={`${id}-group-${k}`}>
      <p className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">{label}</p>
      <ul className="mt-1 space-y-1">
        {(library?.[k] || []).map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-xs" data-testid={`${id}-item-${k}`}><span className="flex-1">{item}</span>{canEdit && <button type="button" onClick={() => remove(k, i)} aria-label="Remove" data-testid={`${id}-remove-${k}`}><Trash2 className="h-3.5 w-3.5 text-muted-foreground" /></button>}</li>
        ))}
        {(library?.[k] || []).length === 0 && <li className="text-xs italic text-muted-foreground">None yet.</li>}
      </ul>
      {canEdit && (
        <div className="mt-1.5 flex gap-2">
          <input value={drafts[k] || ""} onChange={(e) => setDrafts({ ...drafts, [k]: e.target.value })} onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add(k))} placeholder={`${placeholderPrefix} ${label.toLowerCase()} entry…`} className="h-8 flex-1 rounded-md border border-input bg-white px-2 text-xs" data-testid={`${id}-input-${k}`} />
          <button type="button" onClick={() => add(k)} className="h-8 rounded-md border border-border px-2 text-xs hover:bg-secondary" data-testid={`${id}-add-${k}`}>Save</button>
        </div>
      )}
    </div>
  ));
}

const count = (lib) => GROUPS.reduce((n, [k]) => n + (lib?.[k]?.length || 0), 0);

export function ResourceLibrary({ library, orgLibrary, organization, onChange, onOrgChange }) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("mine");
  const save = async (url, next, cb, msg) => {
    try { const { data } = await api.put(url, next); cb(data); toast.success(msg); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const total = count(library) + count(orgLibrary);
  return (
    <div className="mt-4 rounded-md border border-dashed border-border p-3" data-testid="resource-library">
      <button type="button" onClick={() => setOpen(!open)} className="flex w-full items-center justify-between text-left text-xs font-semibold" data-testid="resource-library-toggle">
        <span className="inline-flex items-center gap-1.5"><BookmarkPlus className="h-3.5 w-3.5" /> Saved resource libraries <span className="font-normal text-muted-foreground">({total} item{total === 1 ? "" : "s"} — auto-appear in every case's checklist)</span></span>
        <span className="text-muted-foreground">{open ? "Hide" : "Manage"}</span>
      </button>
      {open && (
        <>
          <div className="mt-3 flex gap-1 text-xs" role="tablist">
            <button type="button" onClick={() => setTab("mine")} className={`rounded-full px-3 py-1 ${tab === "mine" ? "bg-brand-purple text-white" : "border border-border"}`} data-testid="resource-library-tab-mine">My library ({count(library)})</button>
            <button type="button" onClick={() => setTab("org")} className={`inline-flex items-center gap-1 rounded-full px-3 py-1 ${tab === "org" ? "bg-brand-purple text-white" : "border border-border"}`} data-testid="resource-library-tab-org"><Building2 className="h-3 w-3" /> {organization ? `${organization} (${count(orgLibrary)})` : "Organization"}</button>
          </div>
          {tab === "mine" && <LibraryEditor id="resource-library" library={library} placeholderPrefix="Add a local" onSave={(next) => save("/me/resource-library", next, onChange, "Library saved")} />}
          {tab === "org" && (organization ? (
            <>
              <p className="mt-2 text-[11px] text-muted-foreground" data-testid="org-library-note">Shared with every professional whose profile lists <strong>{organization}</strong>. Edits here update the shared list for all of them.</p>
              <LibraryEditor id="org-library" library={orgLibrary} placeholderPrefix="Add a shared" onSave={(next) => save("/org/resource-library", next, onOrgChange, "Organization library saved")} />
            </>
          ) : <p className="mt-2 text-xs italic text-muted-foreground" data-testid="org-library-missing">Add an organization to your professional profile to share a curated library with colleagues.</p>)}
        </>
      )}
    </div>
  );
}
