import PageHeading from "../components/common/PageHeading.jsx";
import DataStrip from "../components/backtest/DataStrip.jsx";
import BacktestForm from "../components/backtest/BacktestForm.jsx";
import MetricsGrid from "../components/backtest/MetricsGrid.jsx";
import EquityPanel from "../components/backtest/EquityPanel.jsx";
import { useBacktest } from "../context/BacktestContext.jsx";

export default function StrategyLab() {
  const { result } = useBacktest();

  return (
    <>
      <PageHeading
      
        title="Strategy Lab"
        
      />
      <DataStrip />

      <div className="workspace-grid">
        <BacktestForm />
        <section className="results-column">
          <div className="results-heading">
            <div>
              <h2>Performance summary</h2>
            </div>
            
          </div>
          <MetricsGrid />
          <EquityPanel />
        </section>
      </div>
    </>
  );
}
