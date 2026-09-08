interface FactOCheckLogoProps {
  compact?: boolean;
  className?: string;
}

export function FactOCheckLogo({ compact = false, className = "" }: FactOCheckLogoProps) {
  return <span className={`logo-lockup${compact ? " logo-lockup--compact" : ""}${className ? ` ${className}` : ""}`}>
    <svg className="logo-mark" viewBox="0 0 32 32" role={compact ? "img" : undefined}
      aria-label={compact ? "Fact-O-Check" : undefined} aria-hidden={compact ? undefined : true}>
      <path className="logo-mark__frame" d="M12 5H7.5A2.5 2.5 0 0 0 5 7.5v17A2.5 2.5 0 0 0 7.5 27H12M20 5h4.5A2.5 2.5 0 0 1 27 7.5v17a2.5 2.5 0 0 1-2.5 2.5H20" />
      <path className="logo-mark__link" d="M10 13h5m7-3-8 12-4-4" />
      <circle cx="10" cy="13" r="1.5" />
      <circle cx="22" cy="10" r="1.5" />
    </svg>
    {!compact && <span className="logo-wordmark">Fact-O-Check</span>}
  </span>;
}
