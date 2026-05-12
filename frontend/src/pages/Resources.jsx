import React, { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { BookOpen, PlayCircle, Facebook, ExternalLink } from "lucide-react";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

function FacebookFeed() {
  if (!FB_URL) return null;
  const src = `https://www.facebook.com/plugins/page.php?href=${encodeURIComponent(
    FB_URL
  )}&tabs=timeline&width=340&height=520&small_header=false&adapt_container_width=true&hide_cover=false&show_facepile=true`;
  return (
    <div className="card-soft p-6" data-testid="resources-facebook-feed">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-[#9CB4C4]/20 text-[#5C6B64] grid place-items-center">
          <Facebook size={18} />
        </div>
        <div className="flex-1">
          <div className="font-serif text-xl text-[#2A3631]">SA Coparents on Facebook</div>
          <div className="text-xs text-[#8A9A92] uppercase tracking-[0.2em]">
            Live posts & videos
          </div>
        </div>
        <a
          href={FB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-[#849D8E] hover:underline inline-flex items-center gap-1"
          data-testid="resources-facebook-follow-link"
        >
          Follow <ExternalLink size={12} />
        </a>
      </div>
      <div className="rounded-2xl overflow-hidden bg-[#F5F3E9] border border-[#E8ECE9]">
        <iframe
          title="SA Coparents Facebook feed"
          src={src}
          width="340"
          height="520"
          style={{ border: "none", overflow: "hidden", width: "100%", display: "block" }}
          scrolling="no"
          frameBorder="0"
          allowFullScreen
          allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
        />
      </div>
    </div>
  );
}

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

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 grid sm:grid-cols-2 gap-5 self-start">
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
          <div className="lg:col-span-1">
            <FacebookFeed />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
