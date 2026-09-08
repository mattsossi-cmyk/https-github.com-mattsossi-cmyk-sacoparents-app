import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

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
        {(notes || []).map((n) => (
          <li key={n.id} className="border border-border rounded-md p-3 bg-muted/20" data-testid={`matter-note-${n.id}`}>
            <p className="text-sm whitespace-pre-wrap">{n.text}</p>
            <p className="text-[11px] text-muted-foreground mt-1">{new Date(n.created_at).toLocaleString()}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
