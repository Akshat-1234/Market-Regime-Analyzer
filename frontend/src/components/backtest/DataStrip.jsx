import { useBacktest } from "../../context/BacktestContext.jsx";

export default function DataStrip() {
  const { dataInfo } = useBacktest();

  return (
    <section className="data-strip">
      <div className="data-strip-icon">▥</div>
      <div className="data-strip-copy">
        <strong>Historical market dataset</strong>
        <span>
          {dataInfo
            ? `${Number(dataInfo.rows ?? 0).toLocaleString("en-IN")} observations · ${
                dataInfo.first_date ?? "—"
              } to ${dataInfo.last_date ?? "—"}`
            : "Checking dataset availability…"}
        </span>
      </div>
      
    </section>
  );
}
