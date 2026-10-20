const CODE_RE = /^SA-[A-Z0-9]{4,32}$/;

// Puts a valid shared case code (SA-XXXXXX) into a {case_id} address; anything else -> null (never an empty ?case=).
export function fillCaseCode(template, code) {
  return (template || "").includes("{case_id}") && CODE_RE.test(code || "") ? template.replace("{case_id}", encodeURIComponent(code)) : null;
}

// "Who has looked at my information": only for parents linked to Align. Case code -> case page, else the plain page.
export function accessLogHref({ linked, code, template, general }) {
  if (!linked) return null;
  return fillCaseCode(template, code) || general || null;
}
