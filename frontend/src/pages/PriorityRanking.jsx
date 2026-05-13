import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";
import { logError } from "../lib/logger";
import { GripVertical, Plus, X } from "lucide-react";

const BUCKETS = [
  { key: "urgent", label: "Most urgent", color: "#C28771" },
  { key: "difficult", label: "Most emotionally difficult", color: "#849D8E" },
  { key: "easy", label: "Easier agreements", color: "#9CB4C4" },
  { key: "compromise", label: "Willing to compromise", color: "#D6A374" },
];

// The fixed list of legal / custody topics every parent ranks for mediation.
// Order here = display order; first 10 are predefined topics, 11th is "Other".
const PRIORITY_TOPICS = [
  { id: "custody", label: "Custody" },
  { id: "possession_schedule", label: "Possession Schedule" },
  { id: "special_education", label: "Special Education" },
  { id: "mental_health", label: "Mental Health" },
  { id: "medication", label: "Medication" },
  { id: "geographic_restriction", label: "Geographic Restriction" },
  { id: "right_of_first_refusal", label: "Right of First Refusal" },
  { id: "morality_clause", label: "Morality Clause" },
  { id: "telephonic_access", label: "Telephonic Access" },
  { id: "airport_transportation", label: "Airport Transportation" },
  { id: "other", label: "Other" },
];

const PRIORITY_TOPIC_IDS = new Set(PRIORITY_TOPICS.map((t) => t.id));

const KIND_META = {
  topic: {
    label: "Topic",
    text: "text-[#5C7A6A]",
    chipBg: "bg-[#849D8E]/20",
  },
  custom: {
    label: "Added",
    text: "text-[#8A6A40]",
    chipBg: "bg-[#D6A374]/20",
  },
};

function isPredefined(item) {
  return PRIORITY_TOPIC_IDS.has(item.id);
}

export default function PriorityRanking() {
  const navigate = useNavigate();
  const [completed, setCompleted] = useState({});
  const [items, setItems] = useState([]); // { id, label, bucket }
  const [newLabel, setNewLabel] = useState("");
  const [saving, setSaving] = useState(false);
  const [dragId, setDragId] = useState(null);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        setCompleted(r.data?.completed || {});

        const existing = r.data?.priority?.items || [];
        const existingById = new Map(existing.map((x) => [x.id, x]));

        // 1) Seed the 11 predefined topics — keeping any previously-saved bucket.
        const seeded = PRIORITY_TOPICS.map((t) => ({
          id: t.id,
          label: t.label,
          bucket: existingById.get(t.id)?.bucket || "easy",
        }));

        // 2) Append any custom items the user added in earlier sessions.
        const customCarriedOver = existing.filter((e) => !PRIORITY_TOPIC_IDS.has(e.id));

        setItems([...seeded, ...customCarriedOver]);
      })
      .catch((err) => logError("Failed to load prep:", err));
  }, []);

  const addItem = () => {
    if (!newLabel.trim()) return;
    setItems((i) => [
      ...i,
      { id: `c_${Date.now()}`, label: newLabel.trim(), bucket: "easy" },
    ]);
    setNewLabel("");
  };

  const removeItem = (id) => setItems((i) => i.filter((x) => x.id !== id));
  const moveTo = (id, bucket) =>
    setItems((i) => i.map((x) => (x.id === id ? { ...x, bucket } : x)));

  const onDragStart = (id) => setDragId(id);
  const onDropTo = (bucket) => {
    if (dragId) moveTo(dragId, bucket);
    setDragId(null);
  };

  const onNext = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/priority", { items });
      toast.success("Priorities saved.");
      navigate("/prep/communication");
    } catch (err) {
      logError("Save priority failed:", err);
      toast.error("Could not save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <WizardLayout
        currentKey="priority"
        eyebrow="Step 3 of 5"
        title="Rank what matters most."
        description="Sort each of the legal and custody topics below into a bucket. This becomes the agenda for your mediation session."
        completed={completed}
        saving={saving}
        onNext={onNext}
      >
        <div className="space-y-6">
          <div className="flex gap-2">
            <input
              className="input-soft"
              placeholder="Add a topic not listed…"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addItem())}
              data-testid="priority-add-input"
            />
            <button type="button" onClick={addItem} className="btn-soft" data-testid="priority-add-button">
              <Plus size={16} className="inline mr-1" /> Add
            </button>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            {BUCKETS.map((b) => {
              const bucketItems = items.filter((i) => i.bucket === b.key);
              return (
                <div
                  key={b.key}
                  className="rounded-2xl bg-[#F5F3E9] p-4 min-h-[180px]"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => onDropTo(b.key)}
                  data-testid={`priority-bucket-${b.key}`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ background: b.color }}
                    />
                    <div className="font-serif text-lg text-[#2A3631]">{b.label}</div>
                    <span className="text-xs text-[#8A9A92] ml-auto">
                      {bucketItems.length}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {bucketItems.length === 0 && (
                      <div className="text-xs italic text-[#8A9A92]">
                        Drag topics into this bucket.
                      </div>
                    )}
                    {bucketItems.map((it) => {
                      const meta = isPredefined(it) ? KIND_META.topic : KIND_META.custom;
                      return (
                        <div
                          key={it.id}
                          draggable
                          onDragStart={() => onDragStart(it.id)}
                          className="bg-white rounded-xl px-3 py-2 flex items-center gap-2 shadow-sm border border-[#E8ECE9] cursor-grab active:cursor-grabbing"
                          data-testid={`priority-item-${it.id}`}
                        >
                          <GripVertical size={14} className="text-[#8A9A92] shrink-0" />
                          <span
                            className={`text-[10px] uppercase tracking-[0.15em] px-1.5 py-0.5 rounded ${meta.chipBg} ${meta.text} shrink-0`}
                            data-testid={`priority-item-${it.id}-chip`}
                          >
                            {meta.label}
                          </span>
                          <span className="text-sm text-[#2A3631] flex-1">{it.label}</span>
                          {!isPredefined(it) && (
                            <button
                              type="button"
                              onClick={() => removeItem(it.id)}
                              className="text-[#8A9A92] hover:text-[#C28771]"
                              aria-label="Remove"
                              data-testid={`priority-item-${it.id}-remove`}
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-xs text-[#8A9A92] italic">
            Tip: drag-and-drop to reorganize. The 11 predefined topics always stay
            on this list — only added items can be removed.
          </div>
        </div>
      </WizardLayout>
    </AppShell>
  );
}
