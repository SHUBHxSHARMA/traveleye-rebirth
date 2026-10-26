export function Wordmark({
  inverted = false,
  className = "",
}: {
  inverted?: boolean;
  className?: string;
}) {
  const ink = inverted ? "#f6f1e7" : "#143028";

  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
        <circle cx="11" cy="11" r="8.25" fill="none" stroke={ink} strokeWidth="1.25" />
        <circle cx="11" cy="11" r="2.7" fill="#c4b083" />
      </svg>
      <span className="font-display text-[1.35rem] leading-none tracking-tight" style={{ color: ink }}>
        Travel Eye
      </span>
    </span>
  );
}
