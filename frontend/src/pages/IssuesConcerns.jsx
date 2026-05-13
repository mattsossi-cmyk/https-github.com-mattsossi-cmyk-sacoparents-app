import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";
import { logError } from "../lib/logger";
import { ShieldAlert } from "lucide-react";

const CATEGORIES = [
  {
    key: "parenting_schedule",
    label: "Parenting schedule",
    fields: [
      { key: "exchanges", label: "Exchanges" },
      { key: "weekdays", label: "Weekdays / weekends" },
      { key: "summer", label: "Summer" },
      { key: "holidays", label: "Holidays" },
    ],
  },
  {
    key: "communication",
    label: "Communication",
    fields: [
      { key: "texting", label: "Texting expectations" },
      { key: "response", label: "Response times" },
      { key: "emergency", label: "Emergency communication" },
    ],
  },
  {
    key: "child_needs",
    label: "Child needs",
    fields: [
      { key: "school", label: "School" },
      { key: "therapy", label: "Therapy" },
      { key: "medical", label: "Medical" },
      { key: "activities", label: "Activities" },
    ],
  },
  {
    key: "financial",
    label: "Financial",
    fields: [
      { key: "expenses", label: "Expenses" },
      { key: "child_support", label: "Child support concerns" },
      { key: "shared_costs", label: "Shared costs" },
    ],
  },
  {
    key: "household_rules",
    label: "Household rules",
    fields: [
      { key: "discipline", label: "Discipline" },
      { key: "screen_time", label: "Screen time" },
      { key: "bedtime", label: "Bedtime" },
      { key: "homework", label: "Homework" },
    ],
  },
];

export default function IssuesConcerns() {
  const navigate = useNavigate();
  const [completed, setCompleted] = useState({});
  const [data, setData] = useState({
    parenting_schedule: {},
    communication: {},
    child_needs: {},
    financial: {},
    household_rules: {},
    safety_concerns: "",
  });
  const [open, setOpen] = useState("parenting_schedule");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        setCompleted(r.data?.completed || {});
        if (r.data?.issues) setData((d) => ({ ...d, ...r.data.issues }));
      })
      .catch((err) => logError("Failed to load prep:", err));
  }, []);

  const updateField = (cat, key, val) => {
    setData((d) => ({ ...d, [cat]: { ...d[cat], [key]: val } }));
  };

  const onNext = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/issues", data);
      toast.success("Concerns noted.");
      navigate("/prep/priority");
    } catch (err) {
      logError("Save issues failed:", err);
      toast.error("Could not save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <WizardLayout
        currentKey="issues"
        eyebrow="Step 2 of 5"
        title="Map your concerns — without escalating them."
        description="Tap each category to capture what's actually on your mind. Short, factual notes work best."
        completed={completed}
        saving={saving}
        onNext={onNext}
      >
        <div className="space-y-3">
          {CATEGORIES.map((cat) => (
            <div
              key={cat.key}
              className={`rounded-2xl border transition-colors ${
                open === cat.key
                  ? "bg-white border-[#849D8E]/40"
                  : "bg-[#F5F3E9] border-transparent"
              }`}
            >
              <button
                type="button"
                onClick={() => setOpen(open === cat.key ? null : cat.key)}
                className="w-full text-left px-5 py-4 flex items-center justify-between"
                data-testid={`issues-toggle-${cat.key}`}
              >
                <span className="font-serif text-xl text-[#2A3631]">{cat.label}</span>
                <span className="text-[#8A9A92] text-sm">
                  {open === cat.key ? "Close" : "Open"}
                </span>
              </button>
              {open === cat.key && (
                <div className="px-5 pb-5 space-y-3">
                  {cat.fields.map((f) => (
                    <div key={f.key}>
                      <label className="eyebrow block mb-2">{f.label}</label>
                      <textarea
                        rows={2}
                        value={data[cat.key]?.[f.key] || ""}
                        onChange={(e) => updateField(cat.key, f.key, e.target.value)}
                        className="input-soft resize-none"
                        data-testid={`issues-${cat.key}-${f.key}-textarea`}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}

          <div className="rounded-2xl border border-[#C28771]/30 bg-[#C28771]/5 p-5 mt-6">
            <div className="font-serif text-xl text-[#2A3631] mb-1">Safety concerns</div>
            <p className="text-sm text-[#5C6B64] mb-3">
              If safety is at risk, please also speak to a qualified attorney or therapist.
              This app is preparation — not a substitute for professional support.
            </p>
            <Link
              to="/safety"
              className="inline-flex items-center gap-2 text-sm text-[#C28771] hover:text-[#a87560] mb-3"
              data-testid="issues-safety-resources-link"
            >
              <ShieldAlert size={14} />
              View domestic violence support resources
            </Link>
            <textarea
              rows={3}
              className="input-soft resize-none"
              placeholder="What feels unsafe, for you or your child? (optional)"
              value={data.safety_concerns}
              onChange={(e) => setData({ ...data, safety_concerns: e.target.value })}
              data-testid="issues-safety-textarea"
            />
          </div>
        </div>
      </WizardLayout>
    </AppShell>
  );
}
