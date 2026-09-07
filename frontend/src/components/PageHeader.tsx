interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, description, action }: PageHeaderProps) {
  const titleId = `page-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <header className="page-header" aria-labelledby={titleId}>
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1 id={titleId}>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}
