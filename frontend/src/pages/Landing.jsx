import React from "react";
import { Link } from "react-router-dom";
import { Heart, Compass, Users, ArrowRight, Facebook } from "lucide-react";

const HERO_BG = "https://images.unsplash.com/photo-1745059759163-77394a0d1770?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGdlbnRsZSUyMHNoYXBlcyUyMHNhZ2UlMjBzYW5kfGVufDB8fHx8MTc3ODU4OTIwN3ww&ixlib=rb-4.1.0&q=85";
const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

export default function Landing() {
  return (
    <div className="min-h-screen gentle-bg">
      {/* Top bar */}
      <header className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full bg-[#849D8E] grid place-items-center text-white font-serif">
            S
          </div>
          <div className="leading-tight">
            <div className="font-serif text-xl">SA Coparents</div>
            <div className="text-[10px] uppercase tracking-[0.25em] text-[#8A9A92]">
              Relational Mediation Prep
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="text-sm text-[#5C6B64] hover:text-[#2A3631]"
            data-testid="nav-sign-in"
          >
            Sign in
          </Link>
          <Link to="/register" className="btn-sage text-sm" data-testid="nav-get-started">
            Get started
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-10 pb-20 relative">
        <div
          className="absolute inset-x-0 top-0 h-[460px] -z-0 opacity-60 rounded-3xl"
          style={{
            backgroundImage: `url(${HERO_BG})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            maskImage: "linear-gradient(180deg, rgba(0,0,0,1) 40%, rgba(0,0,0,0) 100%)",
            WebkitMaskImage: "linear-gradient(180deg, rgba(0,0,0,1) 40%, rgba(0,0,0,0) 100%)",
          }}
        />
        <div className="relative z-10 grid lg:grid-cols-12 gap-10 items-center pt-12 fade-up">
          <div className="lg:col-span-7">
            <div className="eyebrow mb-5">A quieter way to prepare</div>
            <h1 className="font-serif text-5xl sm:text-6xl lg:text-7xl leading-[1.02] text-[#2A3631]">
              Mediation, prepared with <em className="text-[#849D8E]">care</em>.
            </h1>
            <p className="text-lg text-[#5C6B64] mt-6 max-w-xl leading-relaxed">
              Move from emotionally reactive to child-centered. SA Coparents guides you
              through a calm, structured preparation so your mediation session focuses on
              what matters most — your child.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                to="/register"
                className="btn-sage inline-flex items-center gap-2"
                data-testid="hero-start-button"
              >
                Start preparation <ArrowRight size={16} />
              </Link>
              <Link to="/login" className="btn-soft" data-testid="hero-continue-button">
                Continue my progress
              </Link>
            </div>
            <p className="text-sm text-[#8A9A92] italic mt-6 max-w-md">
              “Healthy co-parenting begins with preparation, reflection, and a focus on your
              child's emotional well-being.”
            </p>
          </div>

          <div className="lg:col-span-5">
            <div className="card-soft p-8 relative overflow-hidden">
              <div className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-[#E5D9C5]/40" />
              <div className="absolute -bottom-16 -left-10 w-40 h-40 rounded-full bg-[#849D8E]/15" />
              <div className="relative">
                <div className="eyebrow mb-3">What you'll do</div>
                <h2 className="font-serif text-2xl text-[#2A3631] mb-6">
                  Five steps approach.
                </h2>
                <ul className="space-y-4 text-[#2A3631]">
                  {[
                    "Define the goals you have for your children.",
                    "Map the issues that you have, calmly and clearly.",
                    "Rank what matters most, and where you can flex.",
                    "Reflect on your communication patterns.",
                    "Generate a summary.",
                  ].map((t, i) => (
                    <li key={t} className="flex gap-3 items-start">
                      <span className="w-7 h-7 rounded-full bg-[#849D8E]/15 text-[#849D8E] grid place-items-center text-sm font-medium shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Philosophy strip */}
      <section className="max-w-7xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Heart,
              title: "Child-centered",
              text: "Every prompt orients toward your child's emotional safety.",
            },
            {
              icon: Compass,
              title: "Structured, not clinical",
              text: "A guided wizard so nothing important is forgotten on the day.",
            },
            {
              icon: Users,
              title: "Non-judgmental",
              text: "No winners or losers — only a relational path forward.",
            },
          ].map(({ icon: Icon, title, text }) => (
            <div key={title} className="card-soft p-7">
              <div className="w-10 h-10 rounded-full bg-[#F5F3E9] grid place-items-center text-[#849D8E] mb-4">
                <Icon size={18} />
              </div>
              <div className="font-serif text-2xl text-[#2A3631] mb-2">{title}</div>
              <p className="text-[#5C6B64] leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-[#E8ECE9] py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-[#8A9A92]">
            © SA Coparents — Relational Mediation Prep
          </div>
          {FB_URL && (
            <a
              href={FB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-[#5C6B64] hover:text-[#2A3631] transition-colors group"
              data-testid="landing-footer-facebook-link"
            >
              <span className="w-8 h-8 rounded-full bg-[#F5F3E9] grid place-items-center text-[#849D8E] group-hover:bg-[#E8ECE9] transition-colors">
                <Facebook size={14} />
              </span>
              Follow SA Coparents on Facebook
            </a>
          )}
        </div>
      </footer>
    </div>
  );
}
