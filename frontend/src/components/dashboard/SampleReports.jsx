import { CasesTable } from "@/components/CasesTable";

export const SampleReports = ({ cases, onLoadSample, loading, canLoad }) => {
  const samples = (cases || []).filter((j) => j.is_demo && j.is_creator && !j.archived);
  if (samples.length === 0 && !canLoad) return null;
  return (
    <section data-testid="sample-reports-section">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
        <h2 className="text-2xl font-semibold">Sample Reports</h2>
        <p className="text-xs text-muted-foreground">Fictional two-parent example — kept separate from your client cases.</p>
      </div>
      {samples.length > 0 ? (
        <CasesTable cases={samples} />
      ) : (
        <button type="button" onClick={onLoadSample} disabled={loading} className="inline-flex items-center gap-2 rounded-full border border-dashed border-brand-purple/40 px-4 py-2 text-sm font-medium text-brand-purple hover:bg-brand-purple/5 disabled:opacity-60" data-testid="load-sample-case-btn">
          {loading ? "Loading sample…" : "Load a sample case to explore a complete Joint Alignment Report"}
        </button>
      )}
    </section>
  );
};
