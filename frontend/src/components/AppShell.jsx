import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogOut, Facebook, ShieldAlert } from "lucide-react";

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

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen gentle-bg">
      <header className="border-b border-[#E8ECE9]/70 backdrop-blur-md bg-[#FDFAF3]/70 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-3" data-testid="brand-logo">
            <img
              src="/sa-coparents-mark.png"
              alt="SA Coparents"
              className="w-14 h-14 rounded-xl object-contain bg-[#FDFAF3] ring-1 ring-[#E8ECE9]"
            />
            <div className="leading-tight">
              <div className="font-serif text-xl">SA Coparents</div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-[#8A9A92]">
                Mediation Prep
              </div>
            </div>
          </Link>
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
          <div className="flex items-center gap-3">
            <Link
              to="/safety"
              className="hidden sm:inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-[#C28771]/10 text-[#C28771] hover:bg-[#C28771]/15 transition-colors"
              data-testid="header-safety-link"
              title="Safety & domestic violence resources"
            >
              <ShieldAlert size={12} />
              Safety
            </Link>
            <div className="hidden sm:block text-right">
              <div className="text-sm text-[#2A3631]">{user?.name}</div>
              <div className="text-xs text-[#8A9A92]">{user?.email}</div>
            </div>
            {FB_URL && (
              <a
                href={FB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="w-9 h-9 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] grid place-items-center text-[#849D8E] transition-colors"
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
              className="w-9 h-9 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] grid place-items-center text-[#5C6B64] transition-colors"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-10">{children}</main>
    </div>
  );
}
