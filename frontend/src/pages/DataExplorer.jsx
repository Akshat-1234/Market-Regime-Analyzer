import PageHeading from "../components/common/PageHeading.jsx";
import Panel from "../components/common/Panel.jsx";
import { useBacktest } from "../context/BacktestContext.jsx";

export default function DataExplorer() {
  const { dataInfo, apiStatus, strategies } = useBacktest();

  const rows = [
    ["Observations", dataInfo ? Number(dataInfo.rows ?? 0).toLocaleString("en-IN") : "—"],
    ["First date", dataInfo?.first_date ?? "—"],
    ["Last date", dataInfo?.last_date ?? "—"],
    ["API status", apiStatus],
  ];

  return (
    <>
      <PageHeading
        eyebrow=""
        title="Data Explorer"
        description=""
      />

      <div className="two-col">
        <Panel kicker="" title="Dataset summary">
          <dl className="kv-list">
            {rows.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>

        <Panel kicker="" title="Available strategies">
          <ul className="pill-list">
            {strategies.map((s) => (
              <li key={s.value}>
                <strong>{s.label}</strong>
                <code>{s.value}</code>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}
