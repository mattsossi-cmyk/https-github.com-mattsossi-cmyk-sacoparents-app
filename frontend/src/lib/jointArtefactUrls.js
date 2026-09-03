/**
 * Joint Alignment Report / Agreement URL builders.
 *
 * Every dashboard entry point (share pills, promo card, history rows)
 * routes into the report pages with the same `?share=<id>&mint=1` shape.
 * Centralizing keeps the pages, param names, and default flags in one
 * place — if we ever rename the route or the param, one change here.
 */

export function jointReportUrl(shareId, { mint = true } = {}) {
  if (!shareId) return "/joint-professional-report";
  const params = new URLSearchParams({ share: shareId });
  if (mint) params.set("mint", "1");
  return `/joint-professional-report?${params.toString()}`;
}

export function jointAgreementUrl(shareId, { mint = true } = {}) {
  if (!shareId) return "/joint-agreement";
  const params = new URLSearchParams({ share: shareId });
  if (mint) params.set("mint", "1");
  return `/joint-agreement?${params.toString()}`;
}
