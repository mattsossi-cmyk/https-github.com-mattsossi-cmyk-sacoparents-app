import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, StickyNote } from "lucide-react";
import api from "@/lib/api";
import { Input } from "@/components/ui/input";

function highlight(text, q) {
  if (!q) return text;
  const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig"));
  return parts.map((p, i) => (p.toLowerCase() === q.toLowerCase() ? <mark key={i} className="bg-align-yellow/50 rounded px-0.5">{p}</mark> : p));
}

export function NoteSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);

  useEffect(() => {
    const needle = q.trim();
    if (needle.length < 2) { setResults(null); return; }
    const t = setTimeout(() => {
      api.get("/notes/search", { params: { q: needle } }).then((r) => setResults(r.data)).catch(() => setResults([]));
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <section className="bg-white border border-border rounded-lg p-5" data-testid="note-search-section">
      <div className="flex items-center gap-2 mb-3"><StickyNote className="h-4 w-4 text-brand-teal" /><h2 className="font-semibold">Search My Private Notes</h2></div>
      <div className="relative max-w-md">
        <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find an observation from any session…" className="pl-9 h-11" data-testid="note-search-input" />
      </div>
      {results !== null && (
        results.length === 0 ? (
          <p className="text-sm text-muted-foreground mt-3" data-testid="note-search-empty">No notes match “{q.trim()}”.</p>
        ) : (
          <ul className="mt-3 space-y-2" data-testid="note-search-results">
            {results.map((n) => (
              <li key={n.id} className="border border-border rounded-md px-4 py-3" data-testid={`note-search-result-${n.id}`}>
                <div className="flex items-center justify-between gap-2 flex-wrap text-xs text-muted-foreground">
                  <span><span className="font-semibold tracking-wider text-foreground">{n.case_code || "Case"}</span> · {n.subject_label}{n.child_ref ? ` · matter for ${n.child_ref}` : ""}{n.archived ? " · archived" : ""}</span>
                  <span>{new Date(n.updated_at || n.created_at).toLocaleString()}</span>
                </div>
                <p className="text-sm mt-1.5 whitespace-pre-wrap" data-testid={`note-search-text-${n.id}`}>{highlight(n.text, q.trim())}</p>
                <Link to={`/joint/${n.report_id}`} className="text-xs text-primary font-medium hover:underline mt-1.5 inline-block" data-testid={`note-search-open-${n.id}`}>Open matter →</Link>
              </li>
            ))}
          </ul>
        )
      )}
    </section>
  );
}
