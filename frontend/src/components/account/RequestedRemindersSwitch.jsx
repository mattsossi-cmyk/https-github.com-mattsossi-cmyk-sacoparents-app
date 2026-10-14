import React from "react";
import { BellRing } from "lucide-react";

import AccountSwitch from "./AccountSwitch";

// Weekly Monday reminder about requested-but-unfinished assessments: on/off both ways (also undoes email unsubscribe).
export default function RequestedRemindersSwitch() {
  return (
    <AccountSwitch
      url="/court-path/reminders"
      Icon={BellRing}
      title="Weekly reminders for requested assessments"
      body="A short Monday email if something your professional asked for is still waiting. It never names the assessment."
      onMsg="Weekly reminders are on."
      offMsg="Weekly reminders are off."
      testid="requested-reminders"
    />
  );
}
