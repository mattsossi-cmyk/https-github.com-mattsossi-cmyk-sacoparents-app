import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";
import { logError } from "../lib/logger";
import { ShieldAlert } from "lucide-react";

// The fixed list of concerns shown to every parent. Add new items here and the
// Issues page + Priority page auto-pick them up.
export const ISSUE_TYPES = [
  {
    id: "communication_conflict",
    label: "Poor communication or constant conflict",
    placeholder: "What does the communication or conflict look like in your day-to-day?",
  },
  {
    id: "badmouthing",
    label: "Badmouthing the other parent to the child",
    placeholder: "What has your child heard or witnessed?",
  },
  {
    id: "plan_breaches",
    label: "Not following the parenting plan",
    placeholder: "Which parts of the plan are not being followed?",
  },
  {
    id: "child_as_messenger",
    label: "Using the child as a messenger or weapon",
    placeholder: "How is your child being placed in the middle?",
  },
  {
    id: "inconsistent_parenting",
    label: "Inconsistent parenting and discipline",
    placeholder: "Where are the inconsistencies between households?",
  },
  {
    id: "refusing_cooperation",
    label: "Refusing to cooperate on major decisions",
    placeholder: "Which decisions (school, medical, religion, activities) are stuck?",
  },
  {
    id: "adult_conflict_exposure",
    label: "Exposing the child to adult conflict",
    placeholder: "When and how is your child exposed to adult arguments?",
  },
  {
    id: "unreliability",
    label: "Unreliability with schedules, pickups, or visitation",
    placeholder: "What patterns of unreliability have you noticed?",
  },
  {
    id: "emotional_manipulation",
    label: "Emotional manipulation or alienating behaviors",
    placeholder: "What manipulative or alienating behaviors are you seeing?",
  },
  {
    id: "safety_concerns",
    label: "Concerns about the child's emotional or physical safety",
    placeholder: "What is happening that feels unsafe for your child?",
    safetyFlag: true,
  },
];

function IssueRow({ id, label, placeholder, safetyFlag, value, onChange }) {
  return (
    <div
      className={`rounded-2xl border p-5 transition-colors ${
        safetyFlag
          ? "border-[#C28771]/30 bg-[#C28771]/5"
          : "border-transparent bg-[#F5F3E9]"
      }`}
      data-testid={`issue-${id}`}
    >
      <div className="flex items-start gap-3 mb-2">
        {safetyFlag && (
          <div className="w-7 h-7 rounded-full bg-[#C28771]/15 text-[#C28771] grid place-items-center mt-0.5 shrink-0">
            <ShieldAlert size={14} />
          </div>
        )}
        <div className="font-serif text-lg text-[#2A3631] leading-snug">{label}</div>
      </div>
      {safetyFlag && (
        <p className="text-xs text-[#5C6B64] mb-3">
          If your child is in immediate danger, please call 911 or visit our{" "}
          <Link to="/safety" className="underline text-[#C28771]" data-testid={`issue-${id}-safety-link`}>
            safety resources
          </Link>
          .
        </p>
      )}
      <textarea
        rows={3}
        className="input-soft resize-none"
        placeholder={placeholder}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        data-testid={`issue-${id}-textarea`}
      />
    </div>
  );
}

export default function IssuesConcerns() {
  const navigate = useNavigate();
  const [completed, setCompleted] = useState({});
  const [items, setItems] = useState({}); // { issue_id: note }
  const [other, setOther] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        setCompleted(r.data?.completed || {});
        const existing = r.data?.issues;
        if (existing?.items) setItems(existing.items);
        if (existing?.other) setOther(existing.other);
      })
      .catch((err) => logError("Failed to load prep:", err));
  }, []);

  const updateItem = (id, val) => setItems((prev) => ({ ...prev, [id]: val }));

  const onNext = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/issues", { items, other });
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
        title="Name the concerns — without escalating them."
        description="For each item that applies to you, briefly note what you've experienced. Leave any item blank if it doesn't apply. Short, factual notes work best."
        completed={completed}
        saving={saving}
        onNext={onNext}
      >
        <div className="space-y-3">
          {ISSUE_TYPES.map((it) => (
            <IssueRow
              key={it.id}
              {...it}
              value={items[it.id]}
              onChange={(v) => updateItem(it.id, v)}
            />
          ))}

          <div className="rounded-2xl bg-[#F5F3E9] p-5">
            <div className="font-serif text-lg text-[#2A3631] mb-2">
              Anything else on your mind
            </div>
            <p className="text-xs text-[#5C6B64] mb-3">
              Use this space for anything not covered above.
            </p>
            <textarea
              rows={4}
              className="input-soft resize-none"
              placeholder="Add your own concerns, observations, or context here."
              value={other}
              onChange={(e) => setOther(e.target.value)}
              data-testid="issue-other-textarea"
            />
          </div>
        </div>
      </WizardLayout>
    </AppShell>
  );
}
