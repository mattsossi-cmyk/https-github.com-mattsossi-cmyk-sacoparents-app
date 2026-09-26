import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Globe, ExternalLink, Link as LinkIcon } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PublicProCard } from "@/components/PublicProCard";

export const PublicListingCard = () => {
  const { user, refresh } = useAuth();
  const [state, setState] = useState(null);
  const [edit, setEdit] = useState(false);
  const [form, setForm] = useState({ bio: "", phone: "", website: "", zip: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user?.role === "professional" && user?.approved) api.get("/me/public-listing").then((r) => { setState(r.data); setForm({ bio: r.data.card.bio, phone: r.data.card.phone, website: r.data.card.website, zip: r.data.card.zip }); }).catch(() => {});
  }, [user]);
  if (!state) return null;

  const save = async (listed) => {
    setBusy(true);
    try {
      const { data } = await api.put("/me/public-listing", { listed, ...form });
      setState(data); setEdit(false); await refresh();
      toast.success(listed ? "You're now listed on sacoparentsalign.com" : "Removed from the public directory");
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="mb-6 rounded-lg border border-accent/40 bg-accent/5 p-4" data-testid="public-listing-card">
      <div className="flex flex-wrap items-center gap-3">
        <Globe className="h-5 w-5 shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">{state.listed ? "You're listed on sacoparentsalign.com" : "Get listed on sacoparentsalign.com"}</p>
          {state.hidden && <p className="text-xs font-medium text-red-700" data-testid="public-listing-hidden-notice">Your listing is currently hidden by the administrator{state.hidden_reason ? `: ${state.hidden_reason}` : ""}. Update your details to request a review.</p>}
          <p className="text-xs text-muted-foreground">{state.listed ? "Parents and courts can find you in the public Find a Professional directory." : "Let parents and courts find you in the public Find a Professional directory. Voluntary — you can un-list at any time."}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {state.listed && <Link to="/find-a-professional" className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline" data-testid="public-listing-view-link">View listing <ExternalLink className="h-3 w-3" /></Link>}
          {state.listed && !state.hidden && <Button variant="outline" size="sm" onClick={() => { navigator.clipboard?.writeText(`${window.location.origin}/find-a-professional/${user.id}`); toast.success("Share link copied"); }} data-testid="public-listing-copy-link-btn"><LinkIcon className="h-4 w-4" /> Copy share link</Button>}
          <Button variant="outline" size="sm" onClick={() => setEdit((v) => !v)} data-testid="public-listing-edit-btn">{edit ? "Cancel" : state.listed ? "Edit details" : "Preview & add details"}</Button>
          {state.listed
            ? <Button variant="outline" size="sm" onClick={() => save(false)} disabled={busy} data-testid="public-listing-unlist-btn">Un-list me</Button>
            : <Button size="sm" onClick={() => save(true)} disabled={busy} className="bg-accent hover:bg-accent/90 text-white" data-testid="public-listing-list-btn">{busy ? "Listing…" : "List me on sacoparentsalign.com"}</Button>}
        </div>
      </div>
      {edit && (
        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_320px]" data-testid="public-listing-form">
          <div className="grid gap-2 sm:grid-cols-3">
            <Input placeholder="Practice ZIP" value={form.zip} onChange={set("zip")} maxLength={10} data-testid="public-listing-zip" />
            <Input placeholder="Phone (optional)" value={form.phone} onChange={set("phone")} maxLength={40} data-testid="public-listing-phone" />
            <Input placeholder="Website (optional)" value={form.website} onChange={set("website")} maxLength={200} data-testid="public-listing-website" />
            <Textarea placeholder="Short bio — who you work with and how (max 600 characters). No custody recommendations or guarantees." value={form.bio} onChange={set("bio")} maxLength={600} className="sm:col-span-3 min-h-[70px]" data-testid="public-listing-bio" />
            <div className="sm:col-span-3"><Button size="sm" onClick={() => save(true)} disabled={busy} className="bg-accent hover:bg-accent/90 text-white" data-testid="public-listing-save-btn">{busy ? "Saving…" : state.listed ? "Save changes" : "Save & list me"}</Button></div>
          </div>
          <div data-testid="public-listing-preview">
            <p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">Preview — how your public card will look</p>
            <PublicProCard p={{ ...state.card, ...form, website: form.website && !/^https?:\/\//i.test(form.website) ? `https://${form.website}` : form.website }} testId="public-listing-preview-card" />
          </div>
        </div>
      )}
    </div>
  );
};
