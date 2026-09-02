export function ConfidentialityNotice() {
  return (
    <div className="bg-secondary/50 border border-border rounded-lg p-4 text-xs text-muted-foreground leading-relaxed" data-testid="confidentiality-notice">
      <p className="font-semibold text-foreground mb-1">Your information is private by default.</p>
      <p>
        SA CoParents does not share your assessment or reports with your co-parent or a professional
        unless you choose to share them, except where disclosure is required by law. Completing an
        SA CoParents assessment does not automatically provide your answers to your co-parent. Unless
        a particular feature clearly tells you otherwise before you submit information: your individual
        responses remain associated with your account and are not automatically disclosed to the other
        parent; when SA CoParents generates a report, Foundation Statement, Mediation Statement, or
        similar output, the resulting document may contain selected information derived from your
        responses. You should review any report before sharing it.
      </p>
    </div>
  );
}
