import { useEffect, useRef, useState } from "react";
import { PlayCircle, Download, X, MessageSquareText } from "lucide-react";
import { Button } from "@/components/ui/button";

const SRC = "/demo/sacoparentsalign-demo.mp4";
const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

const ReadAlong = ({ captions, time, onSeek }) => {
  const idx = captions.reduce((a, c, i) => (time + 0.3 >= c.t ? i : a), -1);
  const ref = useRef(null);
  useEffect(() => { ref.current?.querySelector(`[data-idx="${idx}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [idx]);
  return (
    <aside className="flex h-56 flex-col rounded-lg bg-white/5 lg:h-auto lg:w-80 lg:shrink-0" data-testid="demo-read-along">
      <p className="flex items-center gap-1.5 border-b border-white/10 px-3 py-2 text-xs font-bold uppercase tracking-widest text-[#9AD9D9]"><MessageSquareText className="h-3.5 w-3.5" /> Read along</p>
      <ol ref={ref} className="flex-1 space-y-1 overflow-y-auto p-2 text-sm">
        {captions.map((c, i) => (
          <li key={c.t} data-idx={i}>
            <button type="button" onClick={() => onSeek(c.t)} className={`flex w-full gap-2 rounded-md px-2 py-1.5 text-left leading-snug transition-colors ${i === idx ? "bg-[#9AD9D9] text-[#1d0f33] font-semibold" : "text-white/75 hover:bg-white/10"}`} data-testid={`demo-caption-${i}`} aria-current={i === idx ? "true" : undefined}>
              <span className="w-9 shrink-0 text-xs opacity-70 pt-0.5">{fmt(c.t)}</span><span>{c.text}</span>
            </button>
          </li>
        ))}
      </ol>
    </aside>
  );
};

export const DemoVideoButton = ({ size = "sm", variant = "outline", className = "" }) => {
  const [open, setOpen] = useState(false);
  const [captions, setCaptions] = useState([]);
  const [time, setTime] = useState(0);
  const vid = useRef(null);
  useEffect(() => { if (open && !captions.length) fetch("/demo/captions.json").then((r) => r.json()).then(setCaptions).catch(() => {}); }, [open, captions.length]);
  return (
    <>
      <Button size={size} variant={variant} className={className} onClick={() => setOpen(true)} data-testid="watch-demo-btn"><PlayCircle className="h-4 w-4 mr-1" /> Watch the 3-minute demo</Button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3 sm:p-4" onClick={() => setOpen(false)} data-testid="demo-video-modal">
          <div className="w-full max-w-6xl rounded-xl bg-[#1d0f33] p-3 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between gap-2 px-1 pb-2 text-white">
              <p className="text-sm font-semibold">How SA CoParents Align works — courts & professionals (2:50)</p>
              <div className="flex items-center gap-2">
                <a href={SRC} download className="inline-flex items-center gap-1 rounded-md border border-white/30 px-2 py-1 text-xs hover:bg-white/10" data-testid="demo-video-download"><Download className="h-3.5 w-3.5" /> Download MP4</a>
                <button type="button" onClick={() => setOpen(false)} className="rounded-md p-1 hover:bg-white/10" aria-label="Close video" data-testid="demo-video-close"><X className="h-4 w-4" /></button>
              </div>
            </div>
            <div className="flex flex-col gap-3 lg:flex-row">
              <video ref={vid} src={SRC} controls autoPlay muted playsInline onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)} onError={() => {}} className="aspect-video w-full min-w-0 flex-1 rounded-lg bg-black" data-testid="demo-video" />
              <ReadAlong captions={captions} time={time} onSeek={(t) => { const el = vid.current; if (!el) return; el.currentTime = t; setTime(t); const p = el.play(); if (p?.catch) p.catch(() => {}); }} />
            </div>
          </div>
        </div>
      )}
    </>
  );
};
