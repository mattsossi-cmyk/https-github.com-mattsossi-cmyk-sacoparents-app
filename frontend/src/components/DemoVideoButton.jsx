import { useState } from "react";
import { PlayCircle, Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const SRC = "/demo/sacoparentsalign-demo.mp4";

export const DemoVideoButton = ({ size = "sm", variant = "outline", className = "" }) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size={size} variant={variant} className={className} onClick={() => setOpen(true)} data-testid="watch-demo-btn"><PlayCircle className="h-4 w-4 mr-1" /> Watch the 3-minute demo</Button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={() => setOpen(false)} data-testid="demo-video-modal">
          <div className="w-full max-w-4xl rounded-xl bg-[#1d0f33] p-3 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-1 pb-2 text-white">
              <p className="text-sm font-semibold">How SA CoParents Align works — courts & professionals (2:50)</p>
              <div className="flex items-center gap-2">
                <a href={SRC} download className="inline-flex items-center gap-1 rounded-md border border-white/30 px-2 py-1 text-xs hover:bg-white/10" data-testid="demo-video-download"><Download className="h-3.5 w-3.5" /> Download MP4</a>
                <button type="button" onClick={() => setOpen(false)} className="rounded-md p-1 hover:bg-white/10" aria-label="Close video" data-testid="demo-video-close"><X className="h-4 w-4" /></button>
              </div>
            </div>
            <video src={SRC} controls autoPlay playsInline className="aspect-video w-full rounded-lg bg-black" data-testid="demo-video" />
          </div>
        </div>
      )}
    </>
  );
};
