import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { getCommShare, setCommShare } from "../../lib/commShare";
import { Switch } from "../ui/switch";

// Account: change the Communication Style sharing choice made after that step.
export function CommShareSwitch() {
  const [choice, setChoice] = useState(undefined);
  useEffect(() => {
    getCommShare().then(setChoice, () => setChoice(null));
  }, []);

  const toggle = async (on) => {
    const before = choice;
    setChoice(on ? "yes" : "no");
    try {
      await setCommShare(on);
      toast.success(on ? "Your 4 Communication Style answers will be shared with SACOparentsAlign." : "Your Communication Style answers are no longer shared.");
    } catch {
      setChoice(before);
      toast.error("Couldn't save that right now. Please try again.");
    }
  };

  return (
    <div data-testid="comm-share-row" className="mt-3 flex items-start gap-3 sm:pl-12">
      <Switch id="comm-share-switch" data-testid="comm-share-switch" checked={choice === "yes"}
              disabled={choice === undefined} onCheckedChange={toggle} className="mt-0.5 shrink-0" />
      <label htmlFor="comm-share-switch" className="text-xs text-[#4B4567] leading-relaxed">
        Share my 4 Communication Style answers with SACOparentsAlign. They&apos;re seen only by my assigned professionals
        and, when needed, SA CoParents administrators. They never go to my co-parent, the court, or any report.
        {choice === null && <span data-testid="comm-share-undecided"> Not chosen yet, so nothing is shared.</span>}
      </label>
    </div>
  );
}
