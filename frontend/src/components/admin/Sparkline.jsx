// Tiny weekly trend line for the admin question tile (oldest week on the left).
const W = 88;
const H = 24;

export default function Sparkline({ values, testid }) {
  const max = Math.max(1, ...values);
  const step = values.length > 1 ? W / (values.length - 1) : W;
  const pts = values.map((v, i) => [i * step, H - 2 - (v / max) * (H - 4)]);
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const [lx, ly] = pts[pts.length - 1];
  return (
    <svg
      width={W}
      height={H}
      viewBox={`-2 0 ${W + 4} ${H}`}
      role="img"
      aria-label={`Taps per week, last ${values.length} weeks, oldest first: ${values.join(', ')}`}
      data-testid={testid}
      data-values={values.join(',')}
    >
      <line x1="0" y1={H - 2} x2={W} y2={H - 2} stroke="#EDE7F7" strokeWidth="1" />
      <polyline points={line} fill="none" stroke="#3D1A78" strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="2.25" fill="#3D1A78" />
    </svg>
  );
}
