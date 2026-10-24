import React, { useEffect, useState } from "react";

import { scanText } from "../../lib/aiNoticeChecks";
import { useAiNotice } from "./AiNoticeProvider";

/**
 * One guard per AI input. `inputProps` locks the box (read-only) until the notice is acknowledged and opens the
 * pop-up on focus or tap; `confirmSend(text)` re-checks right before anything goes to the AI provider.
 */
export function useAiGuard(feature, value = "") {
  const ctx = useAiNotice();
  const [found, setFound] = useState([]);
  useEffect(() => {
    const t = setTimeout(() => setFound(scanText(value)), 300);
    return () => clearTimeout(t);
  }, [value]);
  const locked = !ctx.acked;
  const open = (e) => locked && !ctx.shouldSkipFocus() && ctx.openNotice(e.currentTarget, feature);
  return {
    feature,
    found,
    locked,
    openNotice: ctx.openNotice,
    confirmSend: (text = value) => ctx.confirmSend(feature, text),
    inputProps: {
      readOnly: locked || undefined,
      "aria-readonly": locked || undefined,
      "data-ai-locked": locked ? "true" : undefined,
      "data-ai-flagged": found.length ? "true" : undefined,
      onFocus: open,
      onClick: open,
    },
  };
}

export function AiPrivacyBanner({ tp, feature = null }) {
  const { openNotice } = useAiNotice();
  return (
    <div className="sa-ai-banner" role="note" data-testid={`${tp}-ai-banner`}>
      <span className="sa-ai-banner__icon" aria-hidden="true">🔒</span>
      <span>
        <strong>Privacy reminder:</strong> Don&apos;t include names, birth dates, ID numbers, contact details, or medical or psychological details. Use
        &quot;my child&quot; instead, and add specifics after the draft is written.{" "}
        <button type="button" className="sa-ai-link" data-testid={`${tp}-ai-learn-more`} onClick={(e) => openNotice(e.currentTarget, feature)}>
          Learn more
        </button>
      </span>
    </div>
  );
}

export function AiPrivacyAlert({ tp, labels }) {
  return (
    <div className="sa-ai-alert" role="alert" aria-live="polite" hidden={!labels.length} data-testid={`${tp}-ai-alert`}>
      <strong>Possible personal information found:</strong>
      <ul data-testid={`${tp}-ai-alert-list`}>
        {labels.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <span>Please remove or replace it with general wording before using the AI.</span>
    </div>
  );
}

// Shown where AI would run by itself (tips, coaching, recaps): nothing goes to the AI until the notice is accepted.
export function AiNoticeNeeded({ tp, children = "AI suggestions appear here after you read and accept the AI privacy notice.", className = "" }) {
  const { openNotice } = useAiNotice();
  return (
    <div className={`sa-ai-banner ${className}`} role="note" data-testid={`${tp}-ai-needed`}>
      <span className="sa-ai-banner__icon" aria-hidden="true">🔒</span>
      <span>
        {children}{" "}
        <button type="button" className="sa-ai-link" data-testid={`${tp}-ai-needed-open`} onClick={(e) => openNotice(e.currentTarget)}>
          Read the AI notice
        </button>
      </span>
    </div>
  );
}

// Banner above the AI text box, live alert below it (as placed by the file).
export function AiGuardFrame({ tp, guard, children, className = "" }) {
  return (
    <div className={className} data-testid={`${tp}-ai-frame`}>
      <AiPrivacyBanner tp={tp} feature={guard.feature} />
      {children}
      <AiPrivacyAlert tp={tp} labels={guard.found} />
    </div>
  );
}
