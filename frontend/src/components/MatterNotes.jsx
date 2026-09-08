import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Pencil, Trash2, History } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const fmt = (iso) => new Date(iso).toLocaleString();

function NoteItem({ n, rid, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(n.text);
  const [showHistory, setShowHistory] = useState(false);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/joint/reports/${rid}/notes/${n.id}`, { text: text.trim() });
      toast.success("Note updated");
      setEditing(false);
      onChanged();
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!window.confirm("Delete this private note? This cannot be undone.")) return;
    try {
      await api.delete(`/joint/reports/${rid}/notes/${n.id}`);
      toast.success("Note deleted");
      onChanged();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const revisions = n.revisions || [];
  return (
    <li className="border border-border rounded-md p-3 bg-muted/20" data-testid={`matter-note-${n.id}`}>
      {editing ? (
        <div>
          <textarea className="w-full min-h-20 border border-border rounded-md p-2 text-sm bg-white" value={text} onChange={(e) => setText(e.target.value)} data-testid={`matter-note-edit-input-${n.id}`} />
          <div className="flex gap-2 mt-2">
            <Button size="sm" onClick={save} disabled={!text.trim() || busy} data-testid={`matter-note-edit-save-${n.id}`}>{busy ? "Saving…" : "Save changes"}</Button>
            <Button size="sm" variant="ghost" onClick={() => { setEditing(false); setText(n.text); }} data-testid={`matter-note-edit-cancel-${n.id}`}>Cancel</Button>
          </div>
        </div>
      ) : (
        <>
          <p className="text-sm whitespace-pre-wrap" data-testid={`matter-note-text-${n.id}`}>{n.text}</p>
          <div className="flex items-center justify-between gap-2 mt-1.5 flex-wrap">
            <p className="text-[11px] text-muted-foreground">
              {fmt(n.created_at)}{n.updated_at && <span data-testid={`matter-note-edited-${n.id}`}> · edited {fmt(n.updated_at)}</span>}
            </p>
            <div className="flex gap-1">
              {revisions.length > 0 && (
                <Button size="sm" variant="ghost" className="h-7 px-2 gap-1 text-xs" onClick={() => setShowHistory((v) => !v)} data-testid={`matter-note-history-btn-${n.id}`}><History className="h-3 w-3" /> {revisions.length} revision{revisions.length === 1 ? "" : "s"}</Button>
              )}
              <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => setEditing(true)} aria-label="Edit note" data-testid={`matter-note-edit-btn-${n.id}`}><Pencil className="h-3 w-3" /></Button>
              <Button size="sm" variant="ghost" className="h-7 px-2 text-destructive" onClick={remove} aria-label="Delete note" data-testid={`matter-note-delete-btn-${n.id}`}><Trash2 className="h-3 w-3" /></Button>
            </div>
          </div>
          {showHistory && (
            <ol className="mt-2 border-l-2 border-border pl-3 space-y-1.5" data-testid={`matter-note-history-${n.id}`}>
              {[...revisions].reverse().map((r, i) => (
                <li key={i} className="text-xs">
                  <p className="text-muted-foreground">{fmt(r.at)}</p>
                  <p className="whitespace-pre-wrap line-through decoration-muted-foreground/50">{r.text}</p>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </li>
  );
}

export function MatterNotes({ rid }) {
  const [notes, setNotes] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => { api.get(`/joint/reports/${rid}/notes`).then((r) => setNotes(r.data)).catch((e) => toast.error(formatApiError(e))); };
  useEffect(() => { load(); }, [rid]);

  const save = async () => {
    setBusy(true);
    try {
      await api.post(`/joint/reports/${rid}/notes`, { text: draft.trim() });
      setDraft("");
      toast.success("Private note saved");
      load();
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };

  return (
    <div className="mt-3 border-t border-border pt-3" data-testid={`matter-notes-${rid}`}>
      <p className="text-xs text-muted-foreground mb-2">Private professional notes — visible only to you, never shared with parents or included in reports.</p>
      <textarea className="w-full min-h-20 border border-border rounded-md p-3 text-sm bg-background" placeholder="Observation from today's session…" value={draft} onChange={(e) => setDraft(e.target.value)} data-testid={`matter-note-input-${rid}`} />
      <Button size="sm" className="mt-2" onClick={save} disabled={!draft.trim() || busy} data-testid={`matter-note-save-btn-${rid}`}>{busy ? "Saving…" : "Save Note"}</Button>
      <ul className="mt-3 space-y-2" data-testid={`matter-notes-list-${rid}`}>
        {notes === null && <li className="text-xs text-muted-foreground">Loading…</li>}
        {notes && notes.length === 0 && <li className="text-xs text-muted-foreground" data-testid={`matter-notes-empty-${rid}`}>No notes yet.</li>}
        {(notes || []).map((n) => <NoteItem key={n.id} n={n} rid={rid} onChanged={load} />)}
      </ul>
    </div>
  );
}
