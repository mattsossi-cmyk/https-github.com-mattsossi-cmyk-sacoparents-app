import { Link } from "react-router-dom";
import {
  HeartHandshake, Shield, Heart, GraduationCap, Stethoscope, Brain,
  Calendar, RefreshCcw, ShieldAlert, Layers, Lock,
} from "lucide-react";

const ALL_SUBJECTS = "communication,school,medical,psychological,schedule,routine,conflict";

const BUBBLES = [
  { key: "communication", label: "Communication", color: "bg-brand-teal", icon: Heart },
  { key: "school", label: "School", color: "bg-brand-blue", icon: GraduationCap },
  { key: "medical", label: "Medical", color: "bg-brand-green", icon: Stethoscope },
  { key: "psychological", label: "Psychological", color: "bg-brand-orange", icon: Brain },
  { key: "schedule", label: "Time & Schedule", color: "bg-brand-teal", icon: Calendar },
  { key: "routine", label: "Routines", color: "bg-brand-blue", icon: RefreshCcw },
  { key: "conflict", label: "Conflict", color: "bg-brand-green", icon: ShieldAlert },
  { key: "__complete", label: "Complete Report", color: "bg-brand-purple", icon: Layers, to: "/hub/complete" },
];

function MainBadge({ to, ring, color, icon: Icon, title, tagline, notice, testid }) {
  return (
    <Link to={to} className="group block" data-testid={testid}>
      <div className={`h-52 w-52 lg:h-64 lg:w-64 rounded-full bg-white border-[10px] ${ring} shadow-xl flex flex-col items-center justify-center text-center p-5 group-hover:scale-105 group-hover:shadow-2xl transition-all duration-200`}>
        <Icon className={`h-12 w-12 lg:h-14 lg:w-14 ${color} mb-2`} />
        <div className={`font-extrabold leading-tight ${color} text-base lg:text-lg tracking-wide`}>
          {title.map((t) => (
            <div key={t}>{t}</div>
          ))}
        </div>
        <div className="flex items-center gap-2 my-2">
          <span className={`h-px w-10 ${color.replace("text-", "bg-")}`} />
          <span className={`h-1.5 w-1.5 rounded-full ${color.replace("text-", "bg-")}`} />
          <span className={`h-px w-10 ${color.replace("text-", "bg-")}`} />
        </div>
        <div className={`text-[11px] lg:text-xs font-medium leading-snug ${color}`}>
          {tagline.map((t) => (
            <div key={t}>{t}</div>
          ))}
        </div>
        {notice && (
          <div className="mt-2 text-[9px] lg:text-[10px] text-muted-foreground italic leading-tight flex items-center justify-center gap-1" data-testid={`${testid}-notice`}>
            <Lock className="h-2.5 w-2.5 shrink-0" /> {notice}
          </div>
        )}
      </div>
    </Link>
  );
}

export function CircleNav({ isPro }) {
  const safetyTo = isPro ? "/joint/new?subject=safety" : "/dashboard?contact=professional";
  return (
    <div data-testid="circle-nav">
      <div className="relative hidden md:block h-[620px]" data-testid="circle-nav-desktop">
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none" data-testid="circle-nav-ring" aria-hidden="true">
          <ellipse cx="50" cy="50" rx="47" ry="46" fill="none" stroke="#5B2A86" strokeOpacity="0.25" strokeWidth="1.5" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex gap-8 lg:gap-12 z-10">
          <MainBadge
            to={`/joint/new?subjects=${ALL_SUBJECTS}`}
            ring="border-brand-purple"
            color="text-brand-purple"
            icon={HeartHandshake}
            title={["UNIFORM", "ASSESSMENT"]}
            tagline={["Understand. Align.", "Support Your Child."]}
            notice="Private by default — shared only by your choice"
            testid="circle-uniform"
          />
          <MainBadge
            to={safetyTo}
            ring="border-brand-teal"
            color="text-brand-teal"
            icon={Shield}
            title={["FAMILY VIOLENCE", "ASSESSMENT"]}
            tagline={["Prioritize Safety.", "Plan for Protection."]}
            notice="Shared only with your designated professional"
            testid="circle-safety"
          />
        </div>
        {BUBBLES.map((b, i) => {
          const angle = (i / BUBBLES.length) * 2 * Math.PI - Math.PI / 2;
          const x = 50 + 47 * Math.cos(angle);
          const y = 50 + 46 * Math.sin(angle);
          return (
            <Link
              key={b.key}
              to={b.to || `/joint/new?subject=${b.key}`}
              className="absolute -translate-x-1/2 -translate-y-1/2 group"
              style={{ left: `${x}%`, top: `${y}%` }}
              data-testid={`bubble-${b.key}`}
            >
              <div className={`h-24 w-24 lg:h-28 lg:w-28 rounded-full ${b.color} flex flex-col items-center justify-center text-white shadow-md group-hover:scale-110 group-hover:shadow-lg transition-all duration-200 p-2`}>
                <b.icon className="h-6 w-6 mb-1" />
                <span className="text-[10px] lg:text-[11px] font-bold text-center leading-tight">{b.label}</span>
              </div>
            </Link>
          );
        })}
      </div>

      <div className="md:hidden space-y-8" data-testid="circle-nav-mobile">
        <div className="flex justify-center gap-5">
          <MainBadge
            to={`/joint/new?subjects=${ALL_SUBJECTS}`}
            ring="border-brand-purple"
            color="text-brand-purple"
            icon={HeartHandshake}
            title={["UNIFORM", "ASSESSMENT"]}
            tagline={["Understand. Align.", "Support Your Child."]}
            notice="Private by default — shared only by your choice"
            testid="circle-uniform-mobile"
          />
          <MainBadge
            to={safetyTo}
            ring="border-brand-teal"
            color="text-brand-teal"
            icon={Shield}
            title={["FAMILY VIOLENCE", "ASSESSMENT"]}
            tagline={["Prioritize Safety.", "Plan for Protection."]}
            notice="Shared only with your designated professional"
            testid="circle-safety-mobile"
          />
        </div>
        <div className="grid grid-cols-3 gap-5 justify-items-center">
          {BUBBLES.map((b) => (
            <Link key={b.key} to={b.to || `/joint/new?subject=${b.key}`} data-testid={`bubble-mobile-${b.key}`}>
              <div className={`h-24 w-24 rounded-full ${b.color} flex flex-col items-center justify-center text-white shadow-md p-2`}>
                <b.icon className="h-6 w-6 mb-1" />
                <span className="text-[10px] font-bold text-center leading-tight">{b.label}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      <p className="mt-6 max-w-2xl mx-auto text-center text-xs text-muted-foreground flex items-center justify-center gap-1.5 px-4" data-testid="circle-nav-confidentiality">
        <Lock className="h-3.5 w-3.5 shrink-0" />
        Every focused report starts by privately inviting your co-parent — individual answers are never shown to the other parent; only the generated report is shared. Family violence assessments go only to your designated professional.
      </p>
    </div>
  );
}
