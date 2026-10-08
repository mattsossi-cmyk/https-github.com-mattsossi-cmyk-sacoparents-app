import React from "react";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../../components/ui/dialog";
import { EXAMPLES, TEMPLATES } from "./aiLibrary";

const copy = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success("Copied. Fill in the [brackets] before you send.");
  } catch {
    toast.error("Couldn't copy. Please select the text and copy it.");
  }
};

const CopyBtn = ({ text, testid }) => (
  <button
    type="button"
    data-testid={testid}
    onClick={() => copy(text)}
    className="shrink-0 px-2.5 py-1 rounded-full bg-white border border-purple-200 hover:bg-purple-50 text-[11px] font-semibold text-purple-900 transition-colors"
  >
    <i className="fa-regular fa-copy mr-1"></i>Copy
  </button>
);

function ExampleCard({ ex, grey }) {
  const after = grey ? ex.grey : ex.after;
  return (
    <div data-testid={`sa-ai-example-${ex.key}`} className="rounded-xl border border-purple-100 bg-white p-3 space-y-2">
      <div className="text-sm font-bold text-[#3B1C6B]">{ex.title}</div>
      <p className="text-xs text-rose-800 bg-rose-50 rounded-lg px-2.5 py-1.5 line-through decoration-rose-300">{ex.before}</p>
      <div className="flex items-start gap-2">
        <p className="flex-1 text-xs text-emerald-900 bg-emerald-50 rounded-lg px-2.5 py-1.5">{after}</p>
        <CopyBtn text={after} testid={`sa-ai-example-copy-${ex.key}`} />
      </div>
    </div>
  );
}

function TemplateCard({ t, grey }) {
  const body = grey ? t.grey : t.body;
  return (
    <div data-testid={`sa-ai-template-${t.key}`} className="rounded-xl border border-purple-100 bg-white p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-bold text-[#3B1C6B]">{t.title}</div>
        <CopyBtn text={body} testid={`sa-ai-template-copy-${t.key}`} />
      </div>
      <p className="text-xs text-slate-700 mt-1.5 leading-relaxed">{body}</p>
    </div>
  );
}

export function AiLibraryDialog({ tab, onClose, grey }) {
  const examples = tab === "examples";
  return (
    <Dialog open={!!tab} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="sa-ai-library" className="max-w-lg w-[calc(100%-1rem)] max-h-[85vh] overflow-y-auto rounded-2xl z-[60]">
        <DialogTitle className="text-lg font-extrabold text-[#3B1C6B]">
          {examples ? "AI Examples" : "Quick Templates"}
        </DialogTitle>
        <DialogDescription className="text-xs text-slate-500">
          {examples
            ? "See how a reactive message can be reworked into a calm, child-focused one."
            : "Ready-to-use starting points. Fill in the [brackets] before you send."}
          {grey && " Shown in grey-rock style: logistics only."}
        </DialogDescription>
        <div className="space-y-3">
          {examples
            ? EXAMPLES.map((ex) => <ExampleCard key={ex.key} ex={ex} grey={grey} />)
            : TEMPLATES.map((t) => <TemplateCard key={t.key} t={t} grey={grey} />)}
        </div>
      </DialogContent>
    </Dialog>
  );
}
