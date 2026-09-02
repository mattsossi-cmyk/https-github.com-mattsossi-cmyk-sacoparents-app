import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, ShieldAlert } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

const MAIN_TOPICS = [
  "co_parenting", "education", "medical", "psychological", "communication",
  "child_needs", "schedule", "special_needs", "activities", "transitions",
];
const SAFETY_TOPICS = ["safety", "risk", "safety_communication", "safeguards"];

function circlePos(index, total, radiusPct) {
  const angle = (2 * Math.PI * index) / total - Math.PI / 2;
  return {
    left: `${50 + radiusPct * Math.cos(angle)}%`,
    top: `${50 + radiusPct * Math.sin(angle)}%`,
  };
}

function TopicCircle({ label, selected, onClick, style, testId, danger }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={style}
      className={`absolute -translate-x-1/2 -translate-y-1/2 w-[17%] aspect-square rounded-full flex items-center justify-center text-center p-1.5 text-[10px] lg:text-xs font-semibold leading-tight border-2 transition-[transform,background-color,border-color,color,box-shadow] duration-200 hover:scale-105 ${
        selected
          ? danger
            ? "bg-red-700 text-white border-red-700 shadow-lg scale-105"
            : "bg-primary text-primary-foreground border-primary shadow-lg scale-105"
          : danger
            ? "bg-white text-red-800 border-red-200 hover:border-red-500 shadow-sm"
            : "bg-white text-foreground border-border hover:border-primary/50 shadow-sm"
      }`}
      data-testid={testId}
    >
      {label}
    </button>
  );
}

export default function Hub() {
  const [subjectMap, setSubjectMap] = useState({});
  const [selected, setSelected] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/joint/config")
      .then((r) => setSubjectMap(Object.fromEntries(r.data.subjects.map((s) => [s.key, s.label]))))
      .catch((e) => toast.error(formatApiError(e)));
  }, []);

  const toggle = (key) => {
    setSelected((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  };

  const go = () => {
    if (selected.length === 1) navigate(`/joint/new?subject=${selected[0]}`);
    else if (selected.length > 1) navigate(`/joint/new?subjects=${selected.join(",")}`);
  };

  const selectedLabels = selected.map((k) => subjectMap[k] || k).join(" + ");

  const cluster = (topics, prefix, danger) => (
    <>
      {topics.map((key, i) => (
        <TopicCircle
          key={key}
          label={subjectMap[key] || key}
          selected={selected.includes(key)}
          onClick={() => toggle(key)}
          style={circlePos(i, topics.length, 40)}
          testId={`${prefix}-${key}`}
          danger={danger}
        />
      ))}
    </>
  );

  return (
    <div className="min-h-screen bg-background" data-testid="hub-page">
      <header className="bg-white border-b border-border no-print">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="hub-back-link">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="text-center mb-10">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-brand-purple" data-testid="hub-heading">Joint Report Hub</h1>
          <p className="mt-3 text-muted-foreground max-w-2xl mx-auto" data-testid="hub-subtext">
            One issue → a Focused Joint Report. Several issues → a Customized Joint Report.
            Everything → the Complete Joint Alignment Report.
          </p>
        </div>

        <div className="hidden md:block relative aspect-square max-w-2xl mx-auto" data-testid="hub-main-cluster">
          {cluster(MAIN_TOPICS, "hub-topic")}
          <button
            type="button"
            onClick={() => navigate("/hub/complete")}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[34%] aspect-square rounded-full bg-primary text-primary-foreground flex flex-col items-center justify-center text-center p-6 shadow-xl hover:scale-[1.03] transition-transform duration-200"
            data-testid="hub-complete-circle"
          >
            <span className="text-[10px] uppercase tracking-widest opacity-80">Complete Family View</span>
            <span className="font-display font-extrabold text-base lg:text-xl leading-tight mt-1.5">JOINT ALIGNMENT REPORT</span>
            <span className="text-[10px] lg:text-xs opacity-80 mt-1.5 flex items-center gap-1">All assessments <ArrowRight className="h-3 w-3" /></span>
          </button>
        </div>

        <div className="hidden md:block relative aspect-square max-w-md mx-auto mt-16" data-testid="hub-safety-cluster">
          {cluster(SAFETY_TOPICS, "hub-safety-topic", true)}
          <button
            type="button"
            onClick={() => navigate(`/joint/new?subjects=${SAFETY_TOPICS.join(",")}`)}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[42%] aspect-square rounded-full bg-red-700 text-white flex flex-col items-center justify-center text-center p-5 shadow-xl hover:scale-[1.03] transition-transform duration-200"
            data-testid="hub-safety-circle"
          >
            <ShieldAlert className="h-5 w-5 mb-1.5 opacity-90" />
            <span className="font-display font-extrabold text-sm lg:text-base leading-tight">FAMILY VIOLENCE & SAFETY ASSESSMENT</span>
            <span className="text-[9px] lg:text-[11px] opacity-80 mt-1.5">Safety pathway</span>
          </button>
        </div>

        <div className="md:hidden space-y-8" data-testid="hub-mobile">
          <button type="button" onClick={() => navigate("/hub/complete")} className="w-full rounded-2xl bg-primary text-primary-foreground p-6 text-center shadow-lg" data-testid="hub-complete-mobile">
            <span className="block text-[10px] uppercase tracking-widest opacity-80">Complete Family View</span>
            <span className="block font-display font-extrabold text-xl mt-1">JOINT ALIGNMENT REPORT</span>
          </button>
          <div className="grid grid-cols-2 gap-3">
            {MAIN_TOPICS.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => toggle(key)}
                className={`rounded-full px-3 py-3 text-xs font-semibold border-2 transition-colors ${selected.includes(key) ? "bg-primary text-primary-foreground border-primary" : "bg-white border-border"}`}
                data-testid={`hub-topic-${key}`}
              >
                {subjectMap[key] || key}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => navigate(`/joint/new?subjects=${SAFETY_TOPICS.join(",")}`)} className="w-full rounded-2xl bg-red-700 text-white p-6 text-center shadow-lg" data-testid="hub-safety-mobile">
            <span className="block font-display font-extrabold text-lg">FAMILY VIOLENCE & SAFETY</span>
            <span className="block text-xs opacity-80 mt-1">Safety-focused pathway</span>
          </button>
          <div className="grid grid-cols-2 gap-3">
            {SAFETY_TOPICS.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => toggle(key)}
                className={`rounded-full px-3 py-3 text-xs font-semibold border-2 transition-colors ${selected.includes(key) ? "bg-red-700 text-white border-red-700" : "bg-white border-border"}`}
                data-testid={`hub-safety-topic-${key}`}
              >
                {subjectMap[key] || key}
              </button>
            ))}
          </div>
        </div>

        <div className="max-w-2xl mx-auto mt-12 bg-white border border-border rounded-lg p-6 text-center" data-testid="hub-action-bar">
          {selected.length === 0 && (
            <p className="text-sm text-muted-foreground" data-testid="hub-hint">
              Select any smaller circle to create a Focused Joint Report, select several for a Customized Joint Report, or choose a large circle.
            </p>
          )}
          {selected.length === 1 && (
            <>
              <h2 className="text-2xl font-semibold" data-testid="hub-action-title">Create a Focused Joint Report</h2>
              <p className="text-sm text-muted-foreground mt-2 mb-5">
                Compare both parents' responses about <strong>{selectedLabels}</strong> and identify alignment, differences, options, resources, and questions for discussion.
              </p>
              <Button className="gap-2" onClick={go} data-testid="hub-create-btn">Create Focused Joint Report <ArrowRight className="h-4 w-4" /></Button>
            </>
          )}
          {selected.length > 1 && (
            <>
              <h2 className="text-2xl font-semibold" data-testid="hub-action-title">Create a Customized Joint Report</h2>
              <p className="text-sm text-muted-foreground mt-2 mb-5" data-testid="hub-action-subjects">
                {selected.length} subjects selected: <strong>{selectedLabels}</strong>
              </p>
              <Button className="gap-2" onClick={go} data-testid="hub-create-btn">Create Customized Joint Report <ArrowRight className="h-4 w-4" /></Button>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
