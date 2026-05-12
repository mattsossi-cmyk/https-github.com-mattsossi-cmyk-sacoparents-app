import React, { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { BookOpen, PlayCircle } from "lucide-react";

export default function Resources() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("All");

  useEffect(() => {
    api.get("/mediation/resources").then((r) => setItems(r.data || [])).catch(() => {});
  }, []);

  const categories = ["All", ...Array.from(new Set(items.map((i) => i.category)))];
  const shown = filter === "All" ? items : items.filter((i) => i.category === filter);

  return (
    <AppShell>
      <div className="fade-up">
        <div className="eyebrow mb-3">Library</div>
        <h1 className="font-serif text-4xl sm:text-5xl text-[#2A3631] mb-3">
          Resource Center
        </h1>
        <p className="text-[#5C6B64] mb-8 max-w-2xl">
          Short, useful reads and videos for the everyday work of co-parenting.
        </p>

        <div className="flex flex-wrap gap-2 mb-6">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setFilter(c)}
              data-testid={`resource-filter-${c.toLowerCase().replace(/\s/g, "-")}`}
              className={`px-4 py-2 rounded-full text-sm transition-colors ${
                filter === c
                  ? "bg-[#849D8E] text-white"
                  : "bg-[#F5F3E9] text-[#2A3631] hover:bg-[#E8ECE9]"
              }`}
            >
              {c}
            </button>
          ))}
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {shown.map((r) => {
            const Icon = r.kind === "video" ? PlayCircle : BookOpen;
            return (
              <div
                key={r.id}
                className="card-soft p-6 hover:-translate-y-0.5 transition-transform"
                data-testid={`resource-card-${r.id}`}
              >
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-9 h-9 rounded-full bg-[#849D8E]/15 text-[#849D8E] grid place-items-center">
                    <Icon size={16} />
                  </div>
                  <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A9A92]">
                    {r.category}
                  </div>
                </div>
                <div className="font-serif text-xl text-[#2A3631] mb-1">{r.title}</div>
                <p className="text-sm text-[#5C6B64]">{r.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
