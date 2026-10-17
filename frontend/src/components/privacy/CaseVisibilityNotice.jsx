import React from "react";

import { ProSeeLink } from "./ProSeeLink";

// What a professional sees once a parent accepts their case invitation or enters their court code.
export function CaseVisibilityNotice({ testid, className = "" }) {
  return (
    <div data-testid={testid} role="note" className={`rounded-xl border border-purple-200 bg-[#F5F1FB] px-3.5 py-3 text-[12.5px] leading-relaxed text-[#2A0F5F] ${className}`}>
      <p className="font-bold mb-0.5">
        <i className="fa-solid fa-user-shield mr-1.5" aria-hidden="true"></i>What this professional will see
      </p>
      <p>
        Once you accept, they can see whether each step they asked for is done, in progress or not started, with the dates. They don&rsquo;t see your
        answers. Shared co-parenting results reach them only after both parents finish. Your Self-Assessment answers are never shared.
      </p>
      <ProSeeLink testid={`${testid}-link`} area="case" className="mt-1 text-[0.75rem]" />
    </div>
  );
}
