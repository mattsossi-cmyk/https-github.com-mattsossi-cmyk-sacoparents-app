import { useEffect, useRef, useState } from "react";
import { Loader2, Square, Volume2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function ListenButton({ text, label = "Listen", testId = "listen-btn", size = "sm", variant = "outline", className = "" }) {
  const [state, setState] = useState("idle");
  const audioRef = useRef(null);
  useEffect(() => () => { audioRef.current?.pause(); }, []);
  const stop = () => { audioRef.current?.pause(); audioRef.current = null; setState("idle"); };
  const play = async () => {
    if (state === "playing") return stop();
    setState("loading");
    try {
      const { data } = await api.post("/tts", { text: String(text || "").slice(0, 4000) });
      const a = new Audio(`${process.env.REACT_APP_BACKEND_URL}${data.url}`);
      audioRef.current = a;
      a.onended = () => setState("idle");
      a.onerror = () => { setState("idle"); toast.error("Audio playback failed"); };
      await a.play();
      setState("playing");
    } catch (e) { setState("idle"); toast.error(formatApiError(e)); }
  };
  return (
    <Button type="button" size={size} variant={variant} onClick={play} className={className} aria-label={label} data-testid={testId}>
      {state === "loading" ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : state === "playing" ? <Square className="h-4 w-4 mr-1" /> : <Volume2 className="h-4 w-4 mr-1" />}
      {state === "playing" ? "Stop" : label}
    </Button>
  );
}
