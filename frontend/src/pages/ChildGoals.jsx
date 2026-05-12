import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";

const GOAL_OPTIONS = [
  { id: "emotional_safety", label: "Emotional safety" },
  { id: "stability", label: "Stability" },
  { id: "school_success", label: "School success" },
  { id: "both_parents", label: "Healthy relationship with both parents" },
  { id: "less_conflict", label: "Reduced conflict exposure" },
  { id: "routines", label: "Healthy routines" },
  { id: "consistency", label: "Communication consistency" },
];

export default function ChildGoals() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState([]);
  const [consistencyText, setConsistencyText] = useState("");
  const [feelText, setFeelText] = useState("");
  const [strengthText, setStrengthText] = useState("");
  const [completed, setCompleted] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        const cg = r.data?.child_goals;
        setCompleted(r.data?.completed || {});
        if (cg) {
          setSelected(cg.selected_goals || []);
          setConsistencyText(cg.consistency_text || "");
          setFeelText(cg.feel_text || "");
          setStrengthText(cg.strength_text || "");
        }
      })
      .catch((err) => console.error("Failed to load prep:", err));
  }, []);

  const toggle = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const onNext = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/child-goals", {
        selected_goals: selected,
        consistency_text: consistencyText,
        feel_text: feelText,
        strength_text: strengthText,
        priority_order: selected,
      });
      toast.success("Your goals are saved.");
      navigate("/prep/issues");
    } catch (err) {
      console.error("Save child-goals failed:", err);
      toast.error("Could not save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <WizardLayout
        currentKey="child-goals"
        eyebrow="Step 1 of 5"
        title="What do you want your child to experience?"
        description="Choose what matters most. These become the emotional anchor of your mediation conversation."
        completed={completed}
        saving={saving}
        onNext={onNext}
      >
        <div className="space-y-8">
          <div>
            <div className="eyebrow mb-3">Select what feels true</div>
            <div className="grid sm:grid-cols-2 gap-3">
              {GOAL_OPTIONS.map((g) => {
                const isOn = selected.includes(g.id);
                return (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => toggle(g.id)}
                    data-testid={`goal-option-${g.id}`}
                    className={`text-left rounded-2xl px-5 py-4 border transition-all ${
                      isOn
                        ? "bg-[#849D8E] text-white border-[#849D8E] shadow-sm"
                        : "bg-[#F5F3E9] text-[#2A3631] border-transparent hover:bg-[#E8ECE9]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span>{g.label}</span>
                      <span
                        className={`w-5 h-5 rounded-full grid place-items-center text-xs ${
                          isOn ? "bg-white text-[#849D8E]" : "border border-[#8A9A92]"
                        }`}
                      >
                        {isOn ? "✓" : ""}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="eyebrow block mb-2">
              My child needs more consistency in…
            </label>
            <textarea
              rows={3}
              className="input-soft resize-none"
              placeholder="e.g. bedtime routines, school pickups, screen-time rules…"
              value={consistencyText}
              onChange={(e) => setConsistencyText(e.target.value)}
              data-testid="goals-consistency-textarea"
            />
          </div>
          <div>
            <label className="eyebrow block mb-2">I want my child to feel…</label>
            <textarea
              rows={3}
              className="input-soft resize-none"
              placeholder="e.g. safe to love both parents, settled, not torn between us…"
              value={feelText}
              onChange={(e) => setFeelText(e.target.value)}
              data-testid="goals-feel-textarea"
            />
          </div>
          <div>
            <label className="eyebrow block mb-2">
              One strength of the other parent is…
            </label>
            <textarea
              rows={3}
              className="input-soft resize-none"
              placeholder="A small, honest acknowledgement softens the room."
              value={strengthText}
              onChange={(e) => setStrengthText(e.target.value)}
              data-testid="goals-strength-textarea"
            />
          </div>
        </div>
      </WizardLayout>
    </AppShell>
  );
}
