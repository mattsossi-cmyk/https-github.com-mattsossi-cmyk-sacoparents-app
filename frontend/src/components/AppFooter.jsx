import React from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, LifeBuoy, FlaskConical, Accessibility as A11yIcon, HardDrive, FileText } from "lucide-react";

/**
 * AppFooter — persistent slim footer for authenticated / in-app pages.
 * Marketing footer stays on Landing.jsx; this one shows on the shell so
 * privacy, methodology, retention, and accessibility are always one tap away.
 */
export default function AppFooter() {
  return (
    <footer
      className="mt-16 border-t border-[#E5E0EE] bg-white/60 backdrop-blur-sm"
      data-testid="app-footer"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="flex flex-wrap gap-x-6 gap-y-3 items-center justify-center text-[13px] text-[#4B4567]">
          <FooterLink to="/privacy" icon={<ShieldCheck size={13} />} testId="footer-privacy">Privacy</FooterLink>
          <FooterLink to="/terms" icon={<FileText size={13} />} testId="footer-terms">Terms</FooterLink>
          <FooterLink to="/data-retention" icon={<HardDrive size={13} />} testId="footer-data-retention">Data retention</FooterLink>
          <FooterLink to="/methodology" icon={<FlaskConical size={13} />} testId="footer-methodology">Methodology</FooterLink>
          <FooterLink to="/accessibility" icon={<A11yIcon size={13} />} testId="footer-accessibility">Accessibility</FooterLink>
          <FooterLink to="/safety" icon={<LifeBuoy size={13} />} testId="footer-safety">Crisis resources</FooterLink>
        </div>
        <p className="text-[11px] text-[#857E9C] text-center mt-4 max-w-3xl mx-auto leading-relaxed">
          SA Coparents is an educational and preparation tool. It is not legal
          advice, therapy, or a substitute for professional mediation. Always
          consult qualified family-law and mental-health professionals for
          your situation.
        </p>
      </div>
    </footer>
  );
}

function FooterLink({ to, icon, children, testId }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1.5 text-[#4B4567] hover:text-[#3D1A78] hover:underline underline-offset-2"
      data-testid={testId}
    >
      {icon}
      {children}
    </Link>
  );
}
