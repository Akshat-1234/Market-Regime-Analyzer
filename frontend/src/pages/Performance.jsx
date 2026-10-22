import { Link } from "react-router-dom";
import PageHeading from "../components/common/PageHeading.jsx";
import MetricsGrid from "../components/backtest/MetricsGrid.jsx";
import EquityPanel from "../components/backtest/EquityPanel.jsx";
import { useBacktest } from "../context/BacktestContext.jsx";

export default function Performance() {
  const { result, ranWith, strategyLabel } = useBacktest();

  return (
    <>
      <PageHeading
        
        title="Performance"
        description=""
        pill={result ? strategyLabel.toUpperCase() : undefined}
      />

      {!result ? (
        <div className="empty-state">
          <h2>No backtest yet</h2>
          <p>Run a strategy in the Strategy Lab and its results will show up here.</p>
          <Link className="ghost-button" to="/">
            Go to Strategy Lab <span>↗</span>
          </Link>
        </div>
      ) : (
        <>
         
          <MetricsGrid />
          <EquityPanel />
        </>
      )}
    </>
  );
}
