import React from "react";
import { Link } from "react-router-dom";

import { PROS_PAGE_PATH } from "../../lib/proVisibility";

// "What professionals can see" link. Opens in a new tab so a parent mid-flow keeps their place.
export function ProSeeLink({ testid, area, className = "", newTab = true, label = "What professionals can see" }) {
  return (
    <Link
      to={`${PROS_PAGE_PATH}${area ? `#${area}` : ""}`}
      data-testid={testid}
      {...(newTab ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      className={`inline-flex items-center gap-1.5 font-semibold text-[#3D1A78] underline underline-offset-2 hover:text-[#2A0F5F] ${className}`}
    >
      <i className="fa-solid fa-user-shield text-[0.9em]" aria-hidden="true"></i>
      {label}
    </Link>
  );
}
