import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogOut, Facebook, ShieldAlert, Menu, X, Settings, LogIn } from "lucide-react";

import GuestBanner from "./GuestBanner";
import AppFooter from "./AppFooter";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

function BrandMark({ className = "" }) {
  return (
    <svg
      width={44}
      height={44}
      viewBox="0 0 64 64"
      className={`w-11 h-11 sm:w-12 sm:h-12 ${className}`}
      aria-hidden
    >
      <defs>
        <linearGradient id="navBmGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3D1A78" />
          <stop offset="55%" stopColor="#5E2DB5" />
          <stop offset="100%" stopColor="#2DB5B5" />
        </linearGradient>
      </defs>
      <path
        d="M32 56 C12 42, 4 30, 12 18 C18 9, 28 10, 32 18 C36 10, 46 9, 52 18 C60 30, 52 42, 32 56 Z"
        fill="url(#navBmGrad)"
      />
      <circle cx="24" cy="26" r="4" fill="white" opacity="0.95" />
      <circle cx="40" cy="26" r="4" fill="white" opacity="0.95" />
      <path d="M22 36 Q32 44 42 36" stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.9" />
    </svg>
  );
}

const navLinks = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/prep/child-goals", label: "Child Goals" },
  { to: "/prep/issues", label: "Issues" },
  { to: "/prep/priority", label: "Priority" },
  { to: "/prep/communication", label: "Communication" },
  { to: "/prep/readiness", label: "Readiness" },
  { to: "/summary", label: "Summary" },
  { to: "/progress", label: "Progress" },
  { to: "/shared-with-professionals", label: "Shared with pros" },
];

const ADMIN_EMAILS = new Set(["mattsossi@bsossi.com"]);

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  // Auto-close mobile drawer when route changes.
  useEffect(() => setMenuOpen(false), [location.pathname]);

  // Prevent body scroll while drawer is open.
  useEffect(() => {
    if (menuOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
    return undefined;
  }, [menuOpen]);

  const handleLogout = async () => {
    setMenuOpen(false);
    await logout();
    navigate("/");
  };

  const isAdmin = user?.email && ADMIN_EMAILS.has(user.email.toLowerCase());
  const linksForUser = isAdmin
    ? [...navLinks, { to: "/admin", label: "Admin" }]
    : navLinks;

  return (
    <div className="min-h-screen gentle-bg">
      <GuestBanner />
      <header className="border-b border-[#E5E0EE]/70 backdrop-blur-md bg-[#F8F7FC]/70 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-2">
          {/* Brand */}
          <Link to="/dashboard" className="flex items-center gap-2 sm:gap-3 shrink-0" data-testid="brand-logo">
            <img
              src="/saco-hero-logo.jpg"
              alt="SA CoParents"
              className="w-11 h-11 sm:w-12 sm:h-12 rounded-full object-cover ring-2 ring-[#3D1A78]/20 shrink-0"
            />
            <div className="leading-tight">
              <div className="font-sans font-extrabold text-base sm:text-lg whitespace-nowrap text-[#1A1330]">
                <span className="text-brand-gradient">SA</span> CoParents
              </div>
              <div className="hidden xl:block text-[0.625rem] uppercase tracking-[0.2em] text-[#6E6787]">
                Mediation Prep
              </div>
            </div>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {linksForUser.map((l) => {
              const active = location.pathname.startsWith(l.to);
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  data-testid={`nav-${l.label.toLowerCase().replace(/\s/g, "-")}`}
                  className={`px-3 py-2 rounded-full text-sm transition-colors ${
                    active
                      ? "bg-[#E5E0EE] text-[#1A1330]"
                      : "text-[#4B4567] hover:text-[#1A1330] hover:bg-[#EFE9F9]"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>

          {/* Right-side actions */}
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/help"
              className="inline-flex items-center gap-1.5 text-xs px-2.5 sm:px-3 py-1.5 rounded-full bg-[#C28771]/10 text-[#9A5D47] hover:bg-[#C28771]/15 transition-colors shrink-0"
              data-testid="header-get-help-link"
              title="Get help"
            >
              <ShieldAlert size={12} />
              <span className="hidden xs:inline sm:inline">Get help</span>
            </Link>
            <div className="hidden lg:block text-right">
              <div className="text-sm text-[#1A1330] truncate max-w-[160px]">{user?.name}</div>
              <div className="text-xs text-[#6E6787] truncate max-w-[160px]">{user?.email}</div>
            </div>
            {FB_URL && (
              <a
                href={FB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:grid w-9 h-9 rounded-full bg-[#EFE9F9] hover:bg-[#E5E0EE] place-items-center text-[#3D1A78] transition-colors"
                aria-label="SA CoParents on Facebook"
                title="SA CoParents on Facebook"
                data-testid="header-facebook-link"
              >
                <Facebook size={16} />
              </a>
            )}
            <Link
              to="/account"
              data-testid="header-account-link"
              className="hidden sm:grid w-9 h-9 rounded-full bg-[#EFE9F9] hover:bg-[#E5E0EE] place-items-center text-[#4B4567] transition-colors"
              aria-label="Account settings"
              title="Account settings"
            >
              <Settings size={16} />
            </Link>
            {/* Sign in pill — demo/guest users only. Real accounts already
                have a session, so this would just be noise for them.
                Routes to /login where they can also switch to /claim if
                they want to save the current demo work into a real account. */}
            {user?.is_guest && (
              <Link
                to="/login"
                data-testid="header-signin-link"
                className="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-full bg-[#3D1A78] text-white text-xs font-semibold hover:bg-[#2f1360] transition-colors"
                title="Sign in to your existing account"
              >
                <LogIn size={14} />
                <span className="hidden sm:inline">Sign in</span>
              </Link>
            )}
            <button
              onClick={handleLogout}
              data-testid="logout-button"
              className="hidden sm:grid w-9 h-9 rounded-full bg-[#EFE9F9] hover:bg-[#E5E0EE] place-items-center text-[#4B4567] transition-colors"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
            {/* Mobile hamburger */}
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="md:hidden w-10 h-10 rounded-full bg-[#EFE9F9] hover:bg-[#E5E0EE] grid place-items-center text-[#1A1330] transition-colors"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              data-testid="mobile-menu-button"
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile drawer */}
      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-30 bg-[#1A1330]/30 md:hidden"
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />
          <nav
            className="fixed inset-x-0 top-[72px] z-40 md:hidden bg-[#F8F7FC] border-b border-[#E5E0EE] shadow-lg overflow-y-auto max-h-[calc(100vh-72px)]"
            data-testid="mobile-menu-drawer"
          >
            <div className="px-4 py-4 space-y-1">
              {linksForUser.map((l) => {
                const active = location.pathname.startsWith(l.to);
                return (
                  <Link
                    key={l.to}
                    to={l.to}
                    data-testid={`mobile-nav-${l.label.toLowerCase().replace(/\s/g, "-")}`}
                    className={`block px-4 py-3 rounded-xl text-base transition-colors ${
                      active
                        ? "bg-[#3D1A78]/15 text-[#1A1330] font-medium"
                        : "text-[#1A1330] hover:bg-[#EFE9F9]"
                    }`}
                  >
                    {l.label}
                  </Link>
                );
              })}
            </div>
            <div className="border-t border-[#E5E0EE] px-4 py-3">
              <Link
                to="/delete-account"
                className="block px-4 py-2.5 rounded-xl text-[0.8125rem] text-[#9A5D47] hover:bg-[#C97B63]/10"
                data-testid="mobile-nav-delete-account"
              >
                Delete my account
              </Link>
            </div>
            <div className="border-t border-[#E5E0EE] px-4 py-4 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm text-[#1A1330] truncate">{user?.name}</div>
                <div className="text-xs text-[#6E6787] truncate">{user?.email}</div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {FB_URL && (
                  <a
                    href={FB_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-10 h-10 rounded-full bg-[#EFE9F9] hover:bg-[#E5E0EE] grid place-items-center text-[#3D1A78]"
                    aria-label="Facebook"
                  >
                    <Facebook size={18} />
                  </a>
                )}
                {user?.is_guest && (
                  <Link
                    to="/login"
                    onClick={() => setMenuOpen(false)}
                    data-testid="mobile-signin-link"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#3D1A78] text-white"
                  >
                    <LogIn size={14} />
                    <span className="text-sm font-semibold">Sign in</span>
                  </Link>
                )}
                <button
                  onClick={handleLogout}
                  data-testid="mobile-logout-button"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#EFE9F9] hover:bg-[#E5E0EE] text-[#4B4567]"
                >
                  <LogOut size={14} />
                  <span className="text-sm">Sign out</span>
                </button>
              </div>
            </div>
          </nav>
        </>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-10">{children}</main>
      <AppFooter />
    </div>
  );
}
