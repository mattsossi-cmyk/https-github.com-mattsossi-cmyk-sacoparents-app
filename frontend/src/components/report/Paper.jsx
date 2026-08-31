import { PieChart, Pie, Cell } from "recharts";

export function Paper({ children, pageNum, pageTitle }) {
  return (
    <div
      className="report-paper report-page-enter rounded-lg max-w-4xl mx-auto p-8 sm:p-12 md:p-14"
      data-testid={`report-page-${pageNum}`}
    >
      <div className="flex items-baseline justify-between border-b border-border pb-4 mb-8">
        <span className="font-display text-lg font-semibold text-primary">SA CoParents</span>
        <span className="text-xs uppercase tracking-widest text-muted-foreground" data-testid={`page-label-${pageNum}`}>
          Page {pageNum} of 10 — {pageTitle}
        </span>
      </div>
      {children}
    </div>
  );
}

export function SectionHeading({ children, testId }) {
  return (
    <h2 className="text-3xl sm:text-4xl font-semibold text-foreground mb-6" data-testid={testId}>
      {children}
    </h2>
  );
}

export function PullQuote({ children, testId }) {
  return (
    <div className="bg-secondary/50 border-l-4 border-accent rounded-r-lg p-5 my-6" data-testid={testId}>
      <p className="font-display text-xl italic leading-relaxed text-foreground">{children}</p>
    </div>
  );
}

export function StatusDot({ color }) {
  const map = {
    green: "bg-align-green",
    yellow: "bg-align-yellow",
    blue: "bg-align-blue",
    purple: "bg-align-purple",
  };
  return <span className={`inline-block h-3 w-3 rounded-full ${map[color]} shrink-0 mt-1.5`} />;
}

export function Snapshot({ snapshot, note }) {
  const data = [
    { name: "Aligned", value: snapshot.aligned, color: "#668B69" },
    { name: "Different perspectives", value: snapshot.different, color: "#D4B46A" },
    { name: "Need more information", value: snapshot.info, color: "#6096BA" },
  ];
  return (
    <div className="border border-border rounded-lg p-6 bg-muted/40" data-testid="alignment-snapshot">
      <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-4">
        Your Joint Alignment Snapshot — {snapshot.total} Topics Reviewed
      </p>
      <div className="flex flex-col sm:flex-row items-center gap-8">
        <PieChart width={180} height={180}>
          <Pie data={data} innerRadius={52} outerRadius={80} dataKey="value" stroke="none">
            {data.map((d) => (
              <Cell key={d.name} fill={d.color} />
            ))}
          </Pie>
        </PieChart>
        <div className="space-y-3 flex-1 w-full">
          {data.map((d) => (
            <div key={d.name} className="flex items-center gap-3" data-testid={`snapshot-${d.name.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
              <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
              <span className="font-display text-2xl font-semibold w-8" data-testid={`snapshot-count-${d.name.toLowerCase().replace(/[^a-z]+/g, "-")}`}>{d.value}</span>
              <span className="text-sm">{d.name}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="mt-4 text-sm italic text-muted-foreground" data-testid="snapshot-note">{note}</p>
    </div>
  );
}
