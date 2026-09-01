import { Heart } from "lucide-react";

export function BrandLogo({ size = "text-2xl" }) {
  return (
    <span className={`inline-flex items-center gap-1.5 font-display font-extrabold tracking-tight ${size}`} data-testid="brand-logo">
      <Heart className="h-[0.85em] w-[0.85em] fill-brand-teal text-brand-teal" />
      <span className="text-brand-purple">SA</span>
      <span className="text-brand-teal">CoParents</span>
    </span>
  );
}
