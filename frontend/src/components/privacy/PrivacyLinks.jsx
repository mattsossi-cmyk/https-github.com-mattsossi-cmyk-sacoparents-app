import React from "react";
import { Link } from "react-router-dom";

import { PROS_PAGE_PATH } from "../../lib/proVisibility";

const LINKS = [
  { key: "policy", to: "/privacy", label: "Privacy Policy" },
  { key: "rights", to: "/privacy#your-rights", label: "Your data rights" },
  { key: "pros", to: PROS_PAGE_PATH, label: "What professionals can see" },
  { key: "assessments", to: `${PROS_PAGE_PATH}#by-assessment`, label: "How each assessment is shared" },
];

// Privacy link list used by the first-visit notice and the sign-in page.
export function PrivacyLinks({ tp, only }) {
  const items = only ? LINKS.filter((l) => only.includes(l.key)) : LINKS;
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[13px]">
      {items.map((l) => (
        <li key={l.key}>
          <Link to={l.to} data-testid={`${tp}-link-${l.key}`} className="text-[#3D1A78] font-semibold underline underline-offset-2 hover:text-[#2A0F5F]">
            {l.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}
