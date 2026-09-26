import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";

export function UrgentMessages({ onOpen }) {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get("/court-dashboard/urgent-messages").then((r) => setItems(r.data.items)).catch(() => setItems([])); }, []);
  if (!items?.length) return null;
  return (
    <section className="mb-6 rounded-lg border-2 border-red-600 bg-red-50 p-4" data-testid="judge-urgent-list">
      <p className="flex items-center gap-2 text-sm font-bold text-red-700"><ShieldAlert className="h-4 w-4" /> Urgent safety messages awaiting your reply ({items.length})</p>
      <p className="text-xs text-red-800/80 mt-0.5">Flagged automatically from the professional's wording (advisory triage). Open the case thread to respond; the item clears when the Court replies.</p>
      <ul className="mt-3 space-y-2">
        {items.map((m) => (
          <li key={m.id} className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-red-200 bg-white p-3 text-sm" data-testid={`judge-urgent-${m.id}`}>
            <div className="flex-1 min-w-[220px]">
              <p className="text-[11px] text-muted-foreground"><span className="font-semibold text-foreground">Cause No. {m.cause_number || "—"}</span> · {m.from_name} · {m.at?.slice(0, 16).replace("T", " ")}</p>
              <p className="mt-0.5 line-clamp-2">{m.text}</p>
            </div>
            <Button size="sm" variant="outline" className="border-red-600 text-red-700" onClick={() => onOpen(m.referral_id)} data-testid={`judge-urgent-open-${m.id}`}>Open case thread</Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
