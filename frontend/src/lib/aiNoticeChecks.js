// Browser-only checks from the AI privacy warning file. Labels must match backend ai_notice.AI_NOTICE_LABELS.
// Street address: capitalised street words only, and not "Family/District/County… Court". ID: only next to an ID word (not a year).
export const CHECKS = [
  { label: "Social Security number", re: /\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b/ },
  { label: "Date of birth or specific date", re: /\b(0?[1-9]|1[0-2])[/\-.](0?[1-9]|[12]\d|3[01])[/\-.](\d{2}|\d{4})\b|\b(born|birthday|DOB|date of birth)\b/i },
  { label: "Phone number", re: /(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b/ },
  { label: "Email address", re: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i },
  {
    label: "Street address",
    re: /\b\d{1,6}\s+(?:[A-Z][a-z]+\s){1,3}(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Blvd|Boulevard|(?<!\b(?:Family|District|County|Juvenile|Probate|Circuit|Supreme|Municipal|Appeals)\s)(?:Ct|Court)|Way|Pkwy|Cir|Circle|Trl|Trail)\b/,
  },
  {
    label: "ID, Medicaid, insurance or case number",
    re: /\b(student\s?id|ID\s?#|medicaid|insurance|policy|member\s?id|case\s?(number|no\.?|#)|MRN)\b[^.\n]{0,20}?(?!(?:19|20)\d{2}\b)\d{4,}/i,
  },
  {
    label: "Medical or psychological details",
    re: /\b(diagnos(ed|is)|ADHD|autis(m|tic)|ASD|anxiety|depression|bipolar|PTSD|OCD|dyslexi[ac]|epilep(sy|tic)|seizures?|diabet(es|ic)|asthma|medication|prescri(bed|ption)|mg\b|Adderall|Ritalin|Concerta|Vyvanse|Zoloft|Prozac|Risperdal|therap(y|ist)|counsel(ing|or)|psychiatr(ist|ic)|psycholog(ist|ical)|suicid(e|al)|self[-\s]?harm|hospitali[sz]ed|IQ\s?\d+)\b/i,
  },
];

export function scanText(text) {
  const found = [];
  CHECKS.forEach((c) => {
    if (c.re.test(text || "")) found.push(c.label);
  });
  return found;
}
