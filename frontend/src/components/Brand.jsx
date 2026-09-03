import { Heart } from "lucide-react";

export function BrandLogo({ size = "text-2xl", sub }) {
  return (
    <span className="inline-flex flex-col leading-none" data-testid="brand-logo">
      <span className={`inline-flex items-center gap-1.5 font-display font-extrabold tracking-tight ${size}`}>
        <Heart className="h-[0.85em] w-[0.85em] fill-brand-teal text-brand-teal" />
        <span className="text-brand-purple">SA</span>
        <span className="text-brand-teal">CoParents</span>
      </span>
      {sub && (
        <span className="italic text-green-800 text-sm mt-1 tracking-wide" data-testid="brand-sub">{sub}</span>
      )}
    </span>
  );
}
