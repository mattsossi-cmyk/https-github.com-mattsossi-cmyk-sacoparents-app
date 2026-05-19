import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogOut, Facebook, ShieldAlert, Menu, X } from "lucide-react";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

const navLinks = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/prep/child-goals", label: "Child Goals" },
  { to: "/prep/issues", label: "Issues" },
  { to: "/prep/priority", label: "Priority" },
  { to: "/prep/communication", label: "Communication" },
  { to: "/prep/readiness", label: "Readiness" },
  { to: "/summary", label: "Summary" },
  { to: "/resources", label: "Resources" },
];

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

  return (
    <div className="min-h-screen gentle-bg">
      <header className="border-b border-[#E8ECE9]/70 backdrop-blur-md bg-[#FDFAF3]/70 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-2">
          {/* Brand */}
          <Link to="/dashboard" className="flex items-center gap-2 sm:gap-3 min-w-0" data-testid="brand-logo">
            <img
              src="/sa-coparents-mark.png"
              alt="SA Coparents"
              className="w-11 h-11 sm:w-14 sm:h-14 rounded-xl object-contain bg-[#FDFAF3] ring-1 ring-[#E8ECE9] shrink-0"
            />
            <div className="leading-tight min-w-0">
              <div className="font-serif text-lg sm:text-xl truncate">SA Coparents</div>
              <div className="hidden sm:block text-[10px] uppercase tracking-[0.25em] text-[#8A9A92]">
                Mediation Prep
              </div>
            </div>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((l) => {
              const active = location.pathname.startsWith(l.to);
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  data-testid={`nav-${l.label.toLowerCase().replace(/\s/g, "-")}`}
                  className={`px-3 py-2 rounded-full text-sm transition-colors ${
                    active
                      ? "bg-[#E8ECE9] text-[#2A3631]"
                      : "text-[#5C6B64] hover:text-[#2A3631] hover:bg-[#F5F3E9]"
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
              to="/safety"
              className="inline-flex items-center gap-1.5 text-xs px-2.5 sm:px-3 py-1.5 rounded-full bg-[#C28771]/10 text-[#C28771] hover:bg-[#C28771]/15 transition-colors shrink-0"
              data-testid="header-safety-link"
              title="Safety & domestic violence resources"
            >
              <ShieldAlert size={12} />
              <span className="hidden xs:inline sm:inline">Safety</span>
            </Link>
            <div className="hidden lg:block text-right">
              <div className="text-sm text-[#2A3631] truncate max-w-[160px]">{user?.name}</div>
              <div className="text-xs text-[#8A9A92] truncate max-w-[160px]">{user?.email}</div>
            </div>
            {FB_URL && (
              <a
                href={FB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:grid w-9 h-9 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] place-items-center text-[#849D8E] transition-colors"
                aria-label="SA Coparents on Facebook"
                title="SA Coparents on Facebook"
                data-testid="header-facebook-link"
              >
                <Facebook size={16} />
              </a>
            )}
            <button
              onClick={handleLogout}
              data-testid="logout-button"
              className="hidden sm:grid w-9 h-9 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] place-items-center text-[#5C6B64] transition-colors"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
            {/* Mobile hamburger */}
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="md:hidden w-10 h-10 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] grid place-items-center text-[#2A3631] transition-colors"
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
            className="fixed inset-0 z-30 bg-[#2A3631]/30 md:hidden"
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />
          <nav
            className="fixed inset-x-0 top-[72px] z-40 md:hidden bg-[#FDFAF3] border-b border-[#E8ECE9] shadow-lg overflow-y-auto max-h-[calc(100vh-72px)]"
            data-testid="mobile-menu-drawer"
          >
            <div className="px-4 py-4 space-y-1">
              {navLinks.map((l) => {
                const active = location.pathname.startsWith(l.to);
                return (
                  <Link
                    key={l.to}
                    to={l.to}
                    data-testid={`mobile-nav-${l.label.toLowerCase().replace(/\s/g, "-")}`}
                    className={`block px-4 py-3 rounded-xl text-base transition-colors ${
                      active
                        ? "bg-[#849D8E]/15 text-[#2A3631] font-medium"
                        : "text-[#2A3631] hover:bg-[#F5F3E9]"
                    }`}
                  >
                    {l.label}
                  </Link>
                );
              })}
            </div>
            <div className="border-t border-[#E8ECE9] px-4 py-3">
              <Link
                to="/delete-account"
                className="block px-4 py-2.5 rounded-xl text-[13px] text-[#C97B63] hover:bg-[#C97B63]/10"
                data-testid="mobile-nav-delete-account"
              >
                Delete my account
              </Link>
            </div>
            <div className="border-t border-[#E8ECE9] px-4 py-4 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm text-[#2A3631] truncate">{user?.name}</div>
                <div className="text-xs text-[#8A9A92] truncate">{user?.email}</div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {FB_URL && (
                  <a
                    href={FB_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-10 h-10 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] grid place-items-center text-[#849D8E]"
                    aria-label="Facebook"
                  >
                    <Facebook size={18} />
                  </a>
                )}
                <button
                  onClick={handleLogout}
                  data-testid="mobile-logout-button"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] text-[#5C6B64]"
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
    </div>
  );
}
