import React from "react";
import { Link } from "react-router-dom";
import { useOwnFooterLink } from "../lib/footerLink";
import { useAccessLogLink } from "../lib/useCheckinLink";
import { ShieldCheck, LifeBuoy, FlaskConical, Accessibility as A11yIcon, HardDrive, FileText, UserCheck, Eye } from "lucide-react";

/**
 * AppFooter — persistent slim footer for authenticated / in-app pages.
 * Marketing footer stays on Landing.jsx; this one shows on the shell so
 * privacy, methodology, retention, and accessibility are always one tap away.
 */
export default function AppFooter() {
  useOwnFooterLink();
  // Align's access log, only for parents linked to Align (with their SA case code when they have one).
  const whoHasLooked = useAccessLogLink();
  return (
    <footer
      className="mt-16 border-t border-[#E5E0EE] bg-white/60 backdrop-blur-sm"
      data-testid="app-footer"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="flex flex-wrap gap-x-6 gap-y-3 items-center justify-center text-[0.8125rem] text-[#4B4567]">
          <FooterLink to="/privacy-notice" icon={<ShieldCheck size={13} />} testId="footer-privacy">Privacy Notice</FooterLink>
          <FooterLink to="/who-can-see-my-information" icon={<UserCheck size={13} />} testId="footer-who-can-see">Who can see my information</FooterLink>
          {whoHasLooked && (
            <a href={whoHasLooked} target="_blank" rel="noopener noreferrer" data-testid="footer-who-has-looked"
               className="inline-flex items-center gap-1.5 text-[#4B4567] hover:text-[#3D1A78] hover:underline underline-offset-2">
              <Eye size={13} />
              Who has looked at my information
            </a>
          )}
          <FooterLink to="/terms" icon={<FileText size={13} />} testId="footer-terms">Terms</FooterLink>
          <FooterLink to="/data-retention" icon={<HardDrive size={13} />} testId="footer-data-retention">Data retention</FooterLink>
          <FooterLink to="/methodology" icon={<FlaskConical size={13} />} testId="footer-methodology">Methodology</FooterLink>
          <FooterLink to="/accessibility" icon={<A11yIcon size={13} />} testId="footer-accessibility">Accessibility</FooterLink>
          <FooterLink to="/help" icon={<LifeBuoy size={13} />} testId="footer-get-help">Get help</FooterLink>
        </div>
        <p className="text-[0.6875rem] text-[#6E6787] text-center mt-4 max-w-3xl mx-auto leading-relaxed">
          SA CoParents is an educational and preparation tool. It is not legal
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
