import Panel from "../common/Panel.jsx";
import { useBacktest } from "../../context/BacktestContext.jsx";

export default function BacktestForm() {
  const { strategies, form, updateField, runBacktest, loading, error, apiStatus } =
    useBacktest();

  const onSubmit = (event) => {
    event.preventDefault();
    runBacktest();
  };

  const bind = (name) => ({
    value: form[name],
    onChange: (e) => updateField(name, e.target.value),
  });

  return (
    <Panel  title="Backtest setup"  className="setup-panel">
      <form onSubmit={onSubmit}>
        <label className="field-label" htmlFor="strategy">
          Trading strategy
        </label>
        <select id="strategy" {...bind("strategy")}>
          {strategies.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>

        <div className="field-grid">
          <div>
            <label className="field-label" htmlFor="capital">
              Initial capital (₹)
            </label>
            <input id="capital" type="number" min="1" step="1" required {...bind("capital")} />
          </div>
          <div>
            <label className="field-label" htmlFor="lookback">
              Lookback period
            </label>
            <input id="lookback" type="number" min="1" max="1000" required {...bind("lookback")} />
          </div>
          <div>
            <label className="field-label" htmlFor="costs">
              Transaction costs
            </label>
            <input id="costs" type="number" min="0" max="0.99" step="0.0001" required {...bind("costs")} />
           
          </div>
          <div>
            <label className="field-label" htmlFor="risk-free">
              Risk-free rate
            </label>
            <input id="risk-free" type="number" min="0" max="1" step="0.005" required {...bind("riskFreeRate")} />
            <small className="field-hint"></small>
          </div>
        </div>

        <br />
  
        <button className="run-button" type="submit" disabled={loading || apiStatus !== "connected"}>
          {loading ? (
            <>
              <span className="spinner" /> Running backtest…
            </>
          ) : (
            <>
              <span>▶</span> Run backtest <span className="button-arrow">↗</span>
            </>
          )}
        </button>

        {apiStatus === "offline" && (
          <p className="inline-error">Start your FastAPI server on port 8000, then refresh this page.</p>
        )}
        {error && <p className="inline-error">{error}</p>}
      </form>
    </Panel>
  );
}
