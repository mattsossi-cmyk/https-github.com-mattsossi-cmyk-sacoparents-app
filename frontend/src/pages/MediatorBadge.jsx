import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Copy,
  Check,
  Download,
  Award,
  Heart,
  Sparkles,
  Code2,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const SITE_ORIGIN = "https://sacoparentsapp.online";

const VARIANTS = [
  {
    id: "light",
    label: "Horizontal · light",
    file: "/badges/sa-coparents-recommended-light.svg",
    width: 320,
    height: 88,
  },
  {
    id: "dark",
    label: "Horizontal · dark",
    file: "/badges/sa-coparents-recommended-dark.svg",
    width: 320,
    height: 88,
  },
  {
    id: "seal",
    label: "Vertical seal",
    file: "/badges/sa-coparents-recommended-seal.svg",
    width: 180,
    height: 200,
  },
];

function ensureProtocol(url) {
  const trimmed = (url || "").trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function escAttr(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export default function MediatorBadge() {
  const [name, setName] = useState("");
  const [practiceUrl, setPracticeUrl] = useState("");
  const [email, setEmail] = useState("");
  const [variantId, setVariantId] = useState("light");
  const [copied, setCopied] = useState(false);
  const [logged, setLogged] = useState(false);

  const variant = VARIANTS.find((v) => v.id === variantId) || VARIANTS[0];
  const badgeUrl = `${SITE_ORIGIN}${variant.file}`;

  const referralUrl = useMemo(() => {
    const slug = (name || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 40);
    return slug
      ? `${SITE_ORIGIN}/?ref=${encodeURIComponent(slug)}`
      : SITE_ORIGIN;
  }, [name]);

  const altText = name
    ? `Recommended by SA CoParents — Mediation Prep · ${name}`
    : "Recommended by SA CoParents — Mediation Prep";

  const embedHtml = useMemo(() => {
    const safeRef = escAttr(referralUrl);
    const safeBadge = escAttr(badgeUrl);
    const safeAlt = escAttr(altText);
    return `<a href="${safeRef}" target="_blank" rel="noopener" aria-label="${safeAlt}">\n  <img src="${safeBadge}" alt="${safeAlt}" width="${variant.width}" height="${variant.height}" loading="lazy" style="border:0;max-width:100%;height:auto;" />\n</a>`;
  }, [referralUrl, badgeUrl, altText, variant.width, variant.height]);

  const canSubmit =
    name.trim().length > 0 && practiceUrl.trim().length > 0;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(embedHtml);
      setCopied(true);
      toast.success("Embed code copied.");
      // Best-effort log so the SA CoParents team can see who's promoting the app.
      if (canSubmit && !logged) {
        try {
          await api.post("/mediator/badge", {
            name: name.trim(),
            practice_url: ensureProtocol(practiceUrl),
            variant: variant.id,
            email: email.trim() || null,
          });
          setLogged(true);
        } catch (err) {
          logError("badge log failed", err);
        }
      }
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      logError("clipboard failed", err);
      toast.error("Couldn't copy — please copy manually from the box.");
    }
  };

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = variant.file;
    link.download = `${variant.id}-sa-coparents-recommended.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen gentle-bg">
      {/* Light marketing-style header */}
      <header className="max-w-6xl mx-auto px-5 sm:px-6 py-5 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5" data-testid="badge-page-brand">
          <img
            src="/saco-hero-logo.jpg"
            alt="SA CoParents"
            className="w-10 h-10 rounded-full object-cover ring-2 ring-[#3D1A78]/20"
          />
          <div className="font-sans font-extrabold text-base text-[#1A1330]">
            <span className="text-brand-gradient">SA</span> Coparents
          </div>
        </Link>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-[#4B4567] hover:text-[#1A1330]"
          data-testid="badge-back-link"
        >
          <ArrowLeft size={14} /> Back
        </Link>
      </header>

      <div className="max-w-6xl mx-auto px-5 sm:px-6 pb-20" data-testid="mediator-badge-page">
        {/* Hero */}
        <div className="card-soft p-8 sm:p-10 relative overflow-hidden mb-8">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-[#D4C5F0]/40" />
          <div className="relative max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#3D1A78]/10 text-[#3D1A78] text-[11px] uppercase tracking-[0.2em] mb-4">
              <Award size={12} />
              For mediators
            </div>
            <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight">
              Give your families a calmer way to prepare.
            </h1>
            <p className="text-[#4B4567] mt-4 leading-relaxed">
              SA CoParents helps parents arrive at mediation child-centered,
              regulated, and ready to talk. If you recommend it, embed this badge
              on your practice site — your clients land directly in the app, and
              your name shows up on their screen as the mediator who pointed them
              here.
            </p>
            <div className="mt-5 flex items-center gap-5 text-[12px] text-[#4B4567] flex-wrap">
              <span className="inline-flex items-center gap-1.5">
                <Heart size={12} className="text-[#3D1A78]" /> Free for mediators
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Sparkles size={12} className="text-[#3D1A78]" /> No account needed
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Code2 size={12} className="text-[#3D1A78]" /> Drop-in HTML
              </span>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* LEFT — form + style picker */}
          <div className="space-y-6">
            <div className="card-soft p-6">
              <div className="eyebrow mb-4">Your details</div>
              <div className="space-y-4">
                <div>
                  <label htmlFor="mediator-name" className="text-xs text-[#4B4567] font-semibold mb-1.5 block">
                    Your name or practice
                  </label>
                  <input
                    id="mediator-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Jane Doe Mediation"
                    className="input-soft"
                    data-testid="mediator-name-input"
                    autoFocus
                  />
                </div>
                <div>
                  <label htmlFor="mediator-url" className="text-xs text-[#4B4567] font-semibold mb-1.5 block">
                    Your website
                  </label>
                  <input
                    id="mediator-url"
                    type="url"
                    value={practiceUrl}
                    onChange={(e) => setPracticeUrl(e.target.value)}
                    placeholder="janedoemediation.com"
                    className="input-soft"
                    data-testid="mediator-url-input"
                  />
                </div>
                <div>
                  <label htmlFor="mediator-email" className="text-xs text-[#4B4567] font-semibold mb-1.5 block">
                    Email (optional)
                  </label>
                  <input
                    id="mediator-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="So we can thank you & send referral stats"
                    className="input-soft"
                    data-testid="mediator-email-input"
                  />
                </div>
              </div>
            </div>

            <div className="card-soft p-6">
              <div className="eyebrow mb-4">Choose a style</div>
              <div className="grid sm:grid-cols-3 gap-3">
                {VARIANTS.map((v) => (
                  <button
                    key={v.id}
                    type="button"
                    onClick={() => setVariantId(v.id)}
                    className={`rounded-xl px-3 py-3 text-left transition border ${
                      variantId === v.id
                        ? "border-[#3D1A78] bg-[#EFE9F9] shadow-sm"
                        : "border-[#E5E0EE] bg-white hover:border-[#3D1A78]/50"
                    }`}
                    data-testid={`variant-${v.id}`}
                  >
                    <div className="text-[11px] uppercase tracking-[0.15em] text-[#857E9C] mb-1">
                      Style
                    </div>
                    <div className="text-sm font-semibold text-[#1A1330]">
                      {v.label}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT — preview + embed code */}
          <div className="space-y-6">
            <div className="card-soft p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="eyebrow">Live preview</div>
                <button
                  type="button"
                  onClick={handleDownload}
                  className="text-xs text-[#3D1A78] hover:underline inline-flex items-center gap-1"
                  data-testid="badge-download-svg"
                >
                  <Download size={12} /> Download SVG
                </button>
              </div>
              <div
                className={`rounded-2xl p-6 grid place-items-center ${
                  variantId === "dark" ? "bg-[#1A1330]" : "bg-[#F8F7FC]"
                }`}
                data-testid="badge-preview"
              >
                <a
                  href={referralUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block"
                  data-testid="badge-preview-link"
                >
                  <img
                    src={variant.file}
                    alt={altText}
                    width={variant.width}
                    height={variant.height}
                    style={{ maxWidth: "100%", height: "auto" }}
                  />
                </a>
              </div>
              {name && (
                <div className="text-xs text-[#857E9C] mt-3 text-center">
                  Clicks open{" "}
                  <span className="text-[#3D1A78] font-medium break-all">
                    {referralUrl}
                  </span>
                </div>
              )}
            </div>

            <div className="card-soft p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="eyebrow">Embed code</div>
                <button
                  type="button"
                  onClick={handleCopy}
                  disabled={!canSubmit}
                  className="btn-gradient text-sm inline-flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="copy-embed-button"
                >
                  {copied ? (
                    <>
                      <Check size={14} /> Copied
                    </>
                  ) : (
                    <>
                      <Copy size={14} /> Copy HTML
                    </>
                  )}
                </button>
              </div>
              {!canSubmit && (
                <div className="text-xs text-[#857E9C] mb-3" data-testid="embed-disabled-hint">
                  Add your name and website above to enable copy.
                </div>
              )}
              <pre
                className="bg-[#1A1330] text-[#E5E0EE] text-[12px] leading-relaxed p-4 rounded-xl overflow-x-auto whitespace-pre"
                data-testid="embed-code-block"
              >
                <code>{embedHtml}</code>
              </pre>
              <div className="mt-4 text-[12px] text-[#4B4567] leading-relaxed">
                Paste this snippet anywhere on your website — your "About"
                page, footer, or a "Resources" sidebar. It's a single{" "}
                <code className="bg-[#EFE9F9] text-[#3D1A78] px-1 rounded">
                  &lt;a&gt;
                </code>{" "}
                wrapping an SVG. No JavaScript required.
              </div>
            </div>

            {/* FAQ-style trust block */}
            <div className="rounded-2xl bg-gradient-to-br from-[#EFE9F9] to-[#D5F2F2]/40 p-6 border border-[#E5E0EE]">
              <div className="eyebrow mb-2">A few honest notes</div>
              <ul className="text-sm text-[#4B4567] space-y-2 leading-relaxed">
                <li>
                  • This is <strong>not</strong> a paid partnership. The badge
                  simply signals you've found the tool useful for your clients.
                </li>
                <li>
                  • We don't collect data on your visitors or share your client
                  list. The referral slug only helps us see which mediators are
                  active.
                </li>
                <li>
                  • If you'd rather link without the badge, the plain URL is{" "}
                  <span className="text-[#3D1A78] font-medium">
                    {SITE_ORIGIN}
                  </span>
                  .
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
