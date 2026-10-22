export default function Panel({ kicker, title, chip, className = "", children }) {
  return (
    <section className={`panel ${className}`}>
      {(kicker || title) && (
        <div className="panel-heading">
          <div>
            {kicker && <div className="section-kicker">{kicker}</div>}
            {title && <h2>{title}</h2>}
          </div>
          {chip && <span className="step-chip">{chip}</span>}
        </div>
      )}
      {children}
    </section>
  );
}
