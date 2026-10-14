import React from "react";
import { CalendarClock } from "lucide-react";

import AccountSwitch from "./AccountSwitch";

// Only shown to people who have created a court code or joint case.
export default function ProfessionalDigestSwitch() {
  return (
    <AccountSwitch
      url="/professional/digest"
      Icon={CalendarClock}
      title="Monday case digest"
      body="A short Monday email with how many parents finished, are in progress or haven't started. Counts only: no names, no case references. Skipped when nothing changed."
      onMsg="Monday digest is on."
      offMsg="Monday digest is off."
      testid="pro-digest"
    />
  );
}
