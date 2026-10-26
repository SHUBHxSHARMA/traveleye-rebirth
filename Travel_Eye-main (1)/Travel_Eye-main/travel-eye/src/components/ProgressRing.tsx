"use client";

interface ProgressRingProps {
  discovered: number;
  total: number;
  size?: number;
  tone?: "light" | "dark";
}

export function ProgressRing({
  discovered,
  total,
  size = 92,
  tone = "light",
}: ProgressRingProps) {
  const pct = total === 0 ? 0 : (discovered / total) * 100;
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const track = tone === "dark" ? "#2a3a34" : "#e3dacb";
  const progress = tone === "dark" ? "#c4b083" : "#143028";
  const number = tone === "dark" ? "#f6f1e7" : "#143028";
  const caption = tone === "dark" ? "#d9d3c7" : "#514c45";

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${discovered} of ${total} places found`}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={track} strokeWidth="6" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={progress}
          strokeWidth="6"
          strokeLinecap="square"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute text-center">
        <p className="font-display text-2xl leading-none" style={{ color: number }}>
          {discovered}
        </p>
        <p className="mt-1 text-[10px] uppercase tracking-[0.14em]" style={{ color: caption }}>
          of {total}
        </p>
      </div>
    </div>
  );
}
