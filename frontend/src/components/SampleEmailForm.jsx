import { useState } from "react";
import { Mail } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function SampleEmailForm({ endpoint, label, idPrefix }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const send = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSending(true);
    try { await api.post(endpoint, { email: email.trim() }); toast.success(`${label} sent to ${email.trim()}`); setEmail(""); setOpen(false); }
    catch (err) { toast.error(formatApiError(err)); }
    finally { setSending(false); }
  };
  if (!open) return <Button variant="outline" size="sm" onClick={() => setOpen(true)} data-testid={`${idPrefix}-email-btn`}><Mail className="h-4 w-4 mr-1" /> Email me</Button>;
  return (
    <form onSubmit={send} className="flex gap-2" data-testid={`${idPrefix}-email-form`}>
      <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="h-9 flex-1 min-w-0 rounded-md border border-input bg-white px-2 text-sm" data-testid={`${idPrefix}-email-input`} />
      <Button size="sm" type="submit" disabled={sending} data-testid={`${idPrefix}-email-send`}>{sending ? "Sending…" : "Send"}</Button>
    </form>
  );
}
