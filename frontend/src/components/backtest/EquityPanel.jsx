import Panel from "../common/Panel.jsx";
import EquityChart from "./EquityChart.jsx";
import { useBacktest } from "../../context/BacktestContext.jsx";

export default function EquityPanel() {
  const { result, curve, strategyLabel } = useBacktest();

  return (
    <Panel className="chart-panel">
      <div className="chart-heading">
        <div>
          <h2>Equity curve</h2>
          <p>
            {result
              ? `${strategyLabel} · Historical backtest`
              : ""}
          </p>
        </div>
        
      </div>
      <EquityChart points={curve} />
      {result && curve.length === 0 && (
        <p className="chart-notice">
          The API returned metrics, but no recognised equity-curve array. Check the response's chart data field to enable this chart.
        </p>
      )}
    </Panel>
  );
}
