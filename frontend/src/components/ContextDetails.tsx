function label(value: string) { return value.replaceAll("_", " "); }

export function ContextDetails({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") return <>Not supplied</>;
  if (typeof value === "boolean") return <>{value ? "Yes" : "No"}</>;
  if (Array.isArray(value)) return value.length ? <ul className="context-details-list">
    {value.map((item, index) => <li key={index}><ContextDetails value={item} /></li>)}
  </ul> : <>None recorded</>;
  if (typeof value === "object") return <dl className="context-details">
    {Object.entries(value).map(([key, item]) => <div key={key}>
      <dt>{label(key)}</dt><dd><ContextDetails value={item} /></dd>
    </div>)}
  </dl>;
  return <>{label(String(value))}</>;
}
