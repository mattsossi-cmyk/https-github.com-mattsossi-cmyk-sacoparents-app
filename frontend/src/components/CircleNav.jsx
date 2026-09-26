import { Link } from "react-router-dom";
import {
  HeartHandshake, Shield, ScrollText, Heart, GraduationCap, Stethoscope, Brain, Lock,
} from "lucide-react";

const ALL_SUBJECTS = "communication,schedule,education,medical,psychological,activities,transitions,decision_making,holidays,technology,routine,mediation,co_parenting,child_needs,special_needs";

const BUBBLES = [
  { key: "education", label: "Educational", color: "bg-brand-blue", icon: GraduationCap },
  { key: "medical", label: "Medical", color: "bg-brand-green", icon: Stethoscope },
  { key: "psychological", label: "Psychological", color: "bg-brand-orange", icon: Brain },
  { key: "co_parenting", label: "General Coparenting Assessment", color: "bg-brand-teal", icon: Heart },
];

function MainBadge({ to, ring, color, icon: Icon, title, tagline, notice, action, pill, testid, img }) {
  if (img) {
    return (
      <Link to={to} className="group block" data-testid={testid}>
        <div className="relative h-44 w-44 lg:h-56 lg:w-56 rounded-full overflow-hidden bg-white shadow-xl group-hover:scale-105 group-hover:shadow-2xl transition-all duration-200">
          <img src={img} alt={title.join(" ")} className="h-full w-full object-cover" data-testid={`${testid}-img`} />
        </div>
        {action && <div className="mt-2 flex justify-center"><span className={`px-3 py-1 rounded-full text-[9px] lg:text-[10px] font-bold text-white whitespace-nowrap ${pill} group-hover:brightness-110 transition`} data-testid={`${testid}-action`}>{action}</span></div>}
        {notice && <div className="mt-1.5 max-w-[11rem] lg:max-w-[14rem] text-center text-[9px] text-muted-foreground italic leading-tight flex items-center justify-center gap-1" data-testid={`${testid}-notice`}><Lock className="h-2.5 w-2.5 shrink-0" /> {notice}</div>}
      </Link>
    );
  }
  return (
    <Link to={to} className="group block" data-testid={testid}>
      <div className={`h-44 w-44 lg:h-56 lg:w-56 rounded-full bg-white border-[10px] ${ring} shadow-xl flex flex-col items-center justify-center text-center p-4 group-hover:scale-105 group-hover:shadow-2xl transition-all duration-200`}>
        <Icon className={`h-10 w-10 lg:h-12 lg:w-12 ${color} mb-2`} />
        <div className={`font-extrabold leading-tight ${color} text-sm lg:text-base tracking-wide`}>
          {title.map((t) => (
            <div key={t}>{t}</div>
          ))}
        </div>
        <div className="flex items-center gap-2 my-1.5">
          <span className={`h-px w-8 ${color.replace("text-", "bg-")}`} />
          <span className={`h-1.5 w-1.5 rounded-full ${color.replace("text-", "bg-")}`} />
          <span className={`h-px w-8 ${color.replace("text-", "bg-")}`} />
        </div>
        <div className={`text-[10px] lg:text-[11px] font-medium leading-snug ${color}`}>
          {tagline.map((t) => (
            <div key={t}>{t}</div>
          ))}
        </div>
        {notice && (
          <div className="mt-1.5 text-[8px] lg:text-[9px] text-muted-foreground italic leading-tight flex items-center justify-center gap-1" data-testid={`${testid}-notice`}>
            <Lock className="h-2.5 w-2.5 shrink-0" /> {notice}
          </div>
        )}
        {action && (
          <span className={`mt-2 px-3 py-1 rounded-full text-[9px] lg:text-[10px] font-bold text-white ${pill} group-hover:brightness-110 transition`} data-testid={`${testid}-action`}>{action}</span>
        )}
      </div>
    </Link>
  );
}

export function CircleNav({ isPro }) {
  const safetyTo = isPro ? "/joint/new?subject=safety" : "/dashboard?contact=professional";
  const badges = (
    <>
      <MainBadge
        to={`/joint/new?subjects=${ALL_SUBJECTS}`}
        ring="border-brand-purple"
        color="text-brand-purple"
        icon={HeartHandshake}
        title={["UNIFORM", "ASSESSMENT"]}
        tagline={["Understand. Align.", "Support Your Child."]}
        notice="Private by default — shared only by your choice"
        action="Start Assessment"
        pill="bg-brand-purple"
        testid="circle-uniform"
        img="/badge-uniform.png"
      />
      <MainBadge
        to="/joint/new?kind=agreement"
        ring="border-brand-green"
        color="text-brand-green"
        icon={ScrollText}
        title={["CO-PARENTING", "AGREEMENT"]}
        tagline={["Merge Foundation Statements.", "Build Your Agreement."]}
        notice="Foundation Statements merge from sacoparentsapp.online"
        action="Build Agreement"
        pill="bg-brand-green"
        testid="circle-agreement"
      />
      <MainBadge
        to={safetyTo}
        ring="border-red-700"
        color="text-red-700"
        icon={Shield}
        title={["FAMILY VIOLENCE", "ASSESSMENT"]}
        tagline={["Prioritize Safety.", "Plan for Protection."]}
        notice="Shared only with your designated professional"
        action="Request Professional"
        pill="bg-red-700"
        testid="circle-safety"
        img="/badge-safety.png"
      />
    </>
  );
  return (
    <div data-testid="circle-nav">
      <div className="relative hidden md:block h-[620px]" data-testid="circle-nav-desktop">
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none" data-testid="circle-nav-ring" aria-hidden="true">
          <ellipse cx="50" cy="50" rx="47" ry="46" fill="none" stroke="#5B2A86" strokeOpacity="0.25" strokeWidth="1.5" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex gap-6 lg:gap-10 z-10">
          {badges}
        </div>
        {BUBBLES.map((b, i) => {
          const angle = (i / BUBBLES.length) * 2 * Math.PI - Math.PI / 2;
          const x = 50 + 47 * Math.cos(angle);
          const y = 50 + 46 * Math.sin(angle);
          return (
            <Link
              key={b.key}
              to={`/joint/new?subject=${b.key}`}
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
        <div className="flex flex-wrap justify-center gap-5">
          {badges}
        </div>
        <div className="grid grid-cols-2 gap-5 justify-items-center max-w-md mx-auto">
          {BUBBLES.map((b) => (
            <Link key={b.key} to={`/joint/new?subject=${b.key}`} data-testid={`bubble-mobile-${b.key}`}>
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
      <p className="mt-3 text-center">
        <Link to="/hub/complete" className="text-sm text-primary font-medium hover:underline" data-testid="circle-nav-complete-link">
          View the Complete Joint Alignment Report →
        </Link>
      </p>
    </div>
  );
}
