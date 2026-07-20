/**
 * True polar technology radar (RMPlan/plan.md 2.1).
 *
 * Concentric rings = adoption status (preferred innermost → prohibited
 * outermost); angular sectors = category. Each standard is a clickable blip
 * placed in its (category sector, status ring) cell, coloured by status. This
 * is the classic Thoughtworks-style radar, distinct from the tabular heatmap.
 *
 * Pure inline SVG — no charting dependency. Theme-aware via MUI CSS vars.
 */

interface RadarBlip {
  id: string;
  name: string;
  open_exceptions?: number;
}

interface Props {
  /** matrix[category][status] -> standards in that cell. */
  matrix: Record<string, Record<string, RadarBlip[]>>;
  categories: readonly string[];
  /** Status order from innermost ring to outermost. */
  statuses: readonly string[];
  statusColor: Record<string, string>;
  catLabel: (cat: string) => string;
  statusLabel: (status: string) => string;
  onBlipClick: (blip: RadarBlip) => void;
}

const SIZE = 540;
const CX = SIZE / 2;
const CY = SIZE / 2;
const HOLE = 48;
const MAX_R = 250;

const polar = (angleDeg: number, r: number): [number, number] => {
  const rad = (angleDeg * Math.PI) / 180;
  return [CX + r * Math.cos(rad), CY + r * Math.sin(rad)];
};

export default function TechRadarPolar({
  matrix,
  categories,
  statuses,
  statusColor,
  catLabel,
  statusLabel,
  onBlipClick,
}: Props) {
  const sectorAngle = 360 / categories.length;
  const band = (MAX_R - HOLE) / statuses.length;

  const ringCircles = statuses.map((_s, i) => HOLE + (i + 1) * band);
  const sectorLines = categories.map((_c, i) => {
    const a = i * sectorAngle;
    const [x1, y1] = polar(a, HOLE);
    const [x2, y2] = polar(a, MAX_R);
    return { x1, y1, x2, y2 };
  });

  const blips: {
    key: string;
    cx: number;
    cy: number;
    color: string;
    blip: RadarBlip;
    flagged: boolean;
  }[] = [];
  categories.forEach((cat, ci) => {
    const start = ci * sectorAngle;
    statuses.forEach((status, si) => {
      const cell = matrix[cat]?.[status] ?? [];
      const midR = HOLE + si * band + band / 2;
      cell.forEach((blip, k) => {
        // Spread blips across the sector's angular span at the ring mid-radius,
        // alternating a small radial jitter so dense cells stay legible.
        const a = start + (sectorAngle * (k + 0.5)) / cell.length;
        const jitter = (k % 3) - 1; // -1, 0, 1
        const [x, y] = polar(a, midR + jitter * band * 0.22);
        blips.push({
          key: blip.id,
          cx: x,
          cy: y,
          color: statusColor[status] ?? "#888",
          blip,
          flagged: (blip.open_exceptions ?? 0) > 0,
        });
      });
    });
  });

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      style={{ width: "100%", maxWidth: 640, height: "auto", display: "block", margin: "0 auto" }}
      role="img"
    >
      {/* Ring fills (subtle) + boundaries */}
      {ringCircles.map((r, i) => (
        <circle
          key={`ring-${i}`}
          cx={CX}
          cy={CY}
          r={r}
          fill="none"
          stroke="var(--mui-palette-divider)"
          strokeWidth={1}
        />
      ))}
      <circle cx={CX} cy={CY} r={HOLE} fill="none" stroke="var(--mui-palette-divider)" />

      {/* Sector dividers */}
      {sectorLines.map((l, i) => (
        <line
          key={`sec-${i}`}
          x1={l.x1}
          y1={l.y1}
          x2={l.x2}
          y2={l.y2}
          stroke="var(--mui-palette-divider)"
          strokeWidth={1}
        />
      ))}

      {/* Ring labels (status), stacked up the top spoke */}
      {statuses.map((status, si) => {
        const r = HOLE + si * band + band / 2;
        return (
          <text
            key={`rl-${status}`}
            x={CX + 4}
            y={CY - r}
            fontSize={9}
            fill="var(--mui-palette-text-secondary)"
            dominantBaseline="middle"
          >
            {statusLabel(status)}
          </text>
        );
      })}

      {/* Category labels at each sector's outer mid-angle */}
      {categories.map((cat, ci) => {
        const mid = ci * sectorAngle + sectorAngle / 2;
        const [x, y] = polar(mid, MAX_R + 16);
        const anchor = Math.cos((mid * Math.PI) / 180) > 0.2
          ? "start"
          : Math.cos((mid * Math.PI) / 180) < -0.2
            ? "end"
            : "middle";
        return (
          <text
            key={`cl-${cat}`}
            x={x}
            y={y}
            fontSize={12}
            fontWeight={600}
            textAnchor={anchor as "start" | "end" | "middle"}
            fill="var(--mui-palette-text-primary)"
            dominantBaseline="middle"
          >
            {catLabel(cat)}
          </text>
        );
      })}

      {/* Blips */}
      {blips.map((b) => (
        <g
          key={b.key}
          onClick={() => onBlipClick(b.blip)}
          style={{ cursor: "pointer" }}
        >
          <title>
            {b.blip.name}
            {b.flagged ? ` — ${b.blip.open_exceptions} open exception(s)` : ""}
          </title>
          <circle cx={b.cx} cy={b.cy} r={6.5} fill={b.color} stroke="#fff" strokeWidth={1.5} />
          {b.flagged && (
            <circle
              cx={b.cx}
              cy={b.cy}
              r={9.5}
              fill="none"
              stroke="var(--mui-palette-warning-main)"
              strokeWidth={1.5}
            />
          )}
        </g>
      ))}
    </svg>
  );
}
