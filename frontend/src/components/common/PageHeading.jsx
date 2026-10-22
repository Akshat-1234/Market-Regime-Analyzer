export default function PageHeading({ eyebrow, title, description, pill }) {
  return (
    <section className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {pill && (
        <div className="market-pill">
          <span className="market-dot" /> {pill}
        </div>
      )}
    </section>
  );
}
