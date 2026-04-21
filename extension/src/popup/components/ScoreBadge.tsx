import type { BrowserCheckScore } from "../../shared/types";

interface Props {
  score: BrowserCheckScore;
  resolved: number;
  total: number;
}

const SCORE_CONFIG = {
  good: {
    label: "GOOD",
    description: "Your privacy settings look great.",
    textColor: "text-success",
    strokeColor: "#22c55e",
  },
  fair: {
    label: "FAIR",
    description: "A few settings could be hardened.",
    textColor: "text-warning",
    strokeColor: "#f59e0b",
  },
  vulnerable: {
    label: "VULNERABLE",
    description: "High-priority settings need attention.",
    textColor: "text-danger",
    strokeColor: "#ef4444",
  },
} as const;

export function ScoreBadge({ score, resolved, total }: Props) {
  const cfg = SCORE_CONFIG[score];
  const r = 32;
  const circ = 2 * Math.PI * r;
  const pct = total > 0 ? resolved / total : 0;
  const dash = pct * circ;

  return (
    <div className="flex flex-col items-center pt-5 pb-4">
      <div className="relative w-24 h-24">
        <svg
          className="w-full h-full"
          style={{ transform: "rotate(-90deg)" }}
          viewBox="0 0 80 80"
        >
          <circle
            cx="40"
            cy="40"
            r={r}
            fill="none"
            stroke="#1e2d45"
            strokeWidth="7"
          />
          <circle
            cx="40"
            cy="40"
            r={r}
            fill="none"
            stroke={cfg.strokeColor}
            strokeWidth="7"
            strokeLinecap="round"
            style={{ strokeDasharray: `${dash.toFixed(1)} ${circ.toFixed(1)}` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-xl font-black leading-none ${cfg.textColor}`}>
            {Math.round(pct * 100)}
            <span className="text-xs font-semibold">%</span>
          </span>
        </div>
      </div>
      <p className={`text-base font-bold mt-2 tracking-wide ${cfg.textColor}`}>
        {cfg.label}
      </p>
      <p className="text-xs text-muted mt-0.5">{cfg.description}</p>
      <p className="text-xs text-muted mt-1">
        {resolved}
        <span className="text-muted">/{total}</span>
        {" "}settings hardened
      </p>
    </div>
  );
}
