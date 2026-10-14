import React from "react";
import { MailCheck } from "lucide-react";

import AccountSwitch from "./AccountSwitch";

// Only shown to people who have created a court code or joint case.
export default function CompletionAlertsSwitch() {
  return (
    <AccountSwitch
      url="/professional/completion-alerts"
      Icon={MailCheck}
      title="Email me when a parent finishes what I asked for"
      body="One short email per parent per case. It names only the case reference and your private label: no names, no answers."
      onMsg="Completion emails are on."
      offMsg="Completion emails are off."
      testid="completion-alerts"
    />
  );
}
