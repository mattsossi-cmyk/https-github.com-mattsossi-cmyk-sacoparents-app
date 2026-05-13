import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";
import { logError } from "../lib/logger";
import { GripVertical, Plus, X } from "lucide-react";
import { ISSUE_TYPES } from "./IssuesConcerns";

const BUCKETS = [
  { key: "urgent", label: "Most urgent", color: "#C28771", tint: "#C28771/12" },
  { key: "difficult", label: "Most emotionally difficult", color: "#849D8E", tint: "#849D8E/12" },
  { key: "easy", label: "Easier agreements", color: "#9CB4C4", tint: "#9CB4C4/12" },
  { key: "compromise", label: "Willing to compromise", color: "#D6A374", tint: "#D6A374/12" },
];

const ISSUE_LABEL_BY_ID = Object.fromEntries(
  ISSUE_TYPES.map((it) => [it.id, it.label])
);

function deriveSuggestionsFromIssues(issues) {
  const suggestions = [];
  if (!issues) return suggestions;
  // New shape: { items: { issue_id: note }, other: string }
  if (issues.items && typeof issues.items === "object") {
    Object.entries(issues.items).forEach(([id, note]) => {
      if (note && String(note).trim().length > 0) {
        suggestions.push({
          id: `s_${id}`,
          label: ISSUE_LABEL_BY_ID[id] || id,
        });
      }
    });
  }
  if (issues.other && String(issues.other).trim().length > 0) {
    suggestions.push({ id: "s_other", label: "Other (your own notes)" });
  }
  return suggestions;
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
        const existing = r.data?.priority?.items;
        if (existing && existing.length) {
          setItems(existing);
        } else {
          const seeds = deriveSuggestionsFromIssues(r.data?.issues).map((s) => ({
            ...s,
            bucket: "easy",
          }));
          setItems(seeds);
        }
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
        description="Sort each concern into a bucket. This becomes the agenda for your mediation session."
        completed={completed}
        saving={saving}
        onNext={onNext}
      >
        <div className="space-y-6">
          <div className="flex gap-2">
            <input
              className="input-soft"
              placeholder="Add a concern not listed…"
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
                        Drag items here, or use the buttons below.
                      </div>
                    )}
                    {bucketItems.map((it) => (
                      <div
                        key={it.id}
                        draggable
                        onDragStart={() => onDragStart(it.id)}
                        className="bg-white rounded-xl px-3 py-2 flex items-center gap-2 shadow-sm border border-[#E8ECE9] cursor-grab active:cursor-grabbing"
                        data-testid={`priority-item-${it.id}`}
                      >
                        <GripVertical size={14} className="text-[#8A9A92] shrink-0" />
                        <span className="text-sm text-[#2A3631] flex-1">{it.label}</span>
                        <button
                          type="button"
                          onClick={() => removeItem(it.id)}
                          className="text-[#8A9A92] hover:text-[#C28771]"
                          aria-label="Remove"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {items.length > 0 && (
            <div className="text-xs text-[#8A9A92] italic">
              Tip: drag-and-drop to reorganize, or use the X to remove an item.
            </div>
          )}
        </div>
      </WizardLayout>
    </AppShell>
  );
}
