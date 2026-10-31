import { useMemo } from "react";
import PageHeading from "../components/common/PageHeading.jsx";
import Panel from "../components/common/Panel.jsx";
import { useBacktest } from "../context/BacktestContext.jsx";

const STATES = [0, 1, 2];

const REGIME_COLORS = {
  0: "#38bdf8",
  1: "#f59e0b",
  2: "#a78bfa",
};

const STRATEGY_LABELS = {
  buy_hold: "Buy & Hold",
  momentum: "Momentum",
  mean_reversion: "Mean Reversion",
  ma_crossover: "MA Crossover",
  rsi_mean_reversion: "RSI Mean Reversion",
  donchian_breakout: "Donchian Breakout",
  adx_trend: "ADX Trend",
  atr_targeting: "ATR Targeting",
};

function strategyName(value) {
  return STRATEGY_LABELS[value] ??
    String(value ?? "Unknown").replace(/_/g, " ");
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
}

function formatPercent(value) {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  return `${(Number(value) * 100).toFixed(2)}%`;
}

function average(rows, key) {
  const values = rows
    .map((row) => row[key])
    .filter((value) => value != null && Number.isFinite(Number(value)))
    .map(Number);

  if (!values.length) return null;

  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function normaliseObservations(raw = []) {
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item) => ({
      date: item.Date ?? item.date,
      regime: Number(item.regime),
      confidence: item.regime_confidence,
      dailyReturn: item.daily_return,
      return20: item.return_20,
      volatility20: item.volatility_20,
      selectedStrategy: item.selected_strategy,
      sample: item.sample,
    }))
    .filter(
      (item) =>
        item.date &&
        Number.isInteger(item.regime) &&
        item.regime >= 0 &&
        item.regime <= 2
    )
    .sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

function buildStrategyRuns(rows) {
  if (!rows.length) return [];

  const runs = [];
  let startIndex = 0;
  let currentStrategy = rows[0].selectedStrategy;

  for (let i = 1; i < rows.length; i += 1) {
    if (rows[i].selectedStrategy !== currentStrategy) {
      const previous = rows[i - 1];
      const next = rows[i];

      runs.push({
        strategy: currentStrategy,
        startDate: rows[startIndex].date,
        endDate: previous.date,
        days: i - startIndex,
        previousStrategy: rows[startIndex - 1]?.selectedStrategy ?? null,
        changedOn: rows[startIndex].date,
        fromRegime: rows[startIndex - 1]?.regime ?? null,
        regime: rows[startIndex].regime,
        isLatest: false,
      });

      startIndex = i;
      currentStrategy = next.selectedStrategy;
    }
  }

  runs.push({
    strategy: currentStrategy,
    startDate: rows[startIndex].date,
    endDate: rows.at(-1).date,
    days: rows.length - startIndex,
    previousStrategy: rows[startIndex - 1]?.selectedStrategy ?? null,
    changedOn: rows[startIndex].date,
    fromRegime: rows[startIndex - 1]?.regime ?? null,
    regime: rows[startIndex].regime,
    isLatest: true,
  });

  return runs;
}

function getSwitchReason(run, trainingScores) {
  const score = trainingScores.find(
    (item) =>
      Number(item.regime) === run.regime &&
      item.strategy === run.strategy
  );

  if (Number(score?.observations) > 0 &&
      Number(score.observations) < 30) {
    return `State ${run.regime} had fewer than 30 training observations. The model therefore used the Buy & Hold fallback for this regime.`;
  }

  if (run.previousStrategy && run.fromRegime !== run.regime) {
    const scoreText =
      score?.mean_daily_net_return != null
        ? ` Its training mean daily net return for this state was ${formatPercent(score.mean_daily_net_return)}.`
        : "";

    return `The HMM changed from State ${run.fromRegime} to State ${run.regime}. The training-period mapping assigns ${strategyName(run.strategy)} to State ${run.regime}.${scoreText}`;
  }

  if (!run.previousStrategy) {
    return `This was the strategy mapped to the first regime observed in the out-of-sample test period.${score?.mean_daily_net_return != null ? ` Its training mean daily net return for this state was ${formatPercent(score.mean_daily_net_return)}.` : ""}`;
  }

  return `The strategy selected by the HMM regime mapping became ${strategyName(run.strategy)}.`;
}

function RegimeTimeline({ rows }) {
  if (!rows.length) {
    return <div className="chart-empty">Run an HMM Adaptive backtest to display regime history.</div>;
  }

  const width = 1100;
  const height = 230;
  const left = 100;
  const right = 25;
  const top = 35;
  const bottom = 42;
  const plotWidth = width - left - right;

  const x = (index) =>
    left + (index / Math.max(rows.length - 1, 1)) * plotWidth;

  const y = (regime) => top + Number(regime) * 58;

  const segments = [];

  let start = 0;

  for (let i = 1; i <= rows.length; i += 1) {
    if (i === rows.length || rows[i].regime !== rows[start].regime) {
      segments.push({
        regime: rows[start].regime,
        startIndex: start,
        endIndex: i - 1,
        startDate: rows[start].date,
        endDate: rows[i - 1].date,
      });

      start = i;
    }
  }

  const splitIndex = rows.findIndex((row) => row.sample === "test");

  const dateTicks = [
    0,
    Math.floor((rows.length - 1) / 2),
    rows.length - 1,
  ].filter((value, index, array) => array.indexOf(value) === index);

  return (
    <Panel kicker="" title="Market regime timeline">
      <p style={{ color: "var(--text-muted, #94a3b8)", fontSize: 13 }}>
       
      </p>

      <div style={{ width: "100%", overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: "100%", minWidth: 650, display: "block" }}
          role="img"
          aria-label="Historical HMM market regime timeline"
        >
          {STATES.map((state) => (
            <g key={state}>
              <line
                x1={left}
                y1={y(state)}
                x2={width - right}
                y2={y(state)}
                stroke="currentColor"
                opacity="0.14"
                strokeDasharray="4 5"
              />
              <text
                x={left - 14}
                y={y(state) + 5}
                textAnchor="end"
                fill={REGIME_COLORS[state]}
                fontSize="13"
                fontWeight="600"
              >
                State {state}
              </text>
            </g>
          ))}

          {segments.map((segment, index) => {
            const x1 = x(segment.startIndex);
            const x2 = Math.max(x1 + 1.5, x(segment.endIndex));

            return (
              <g key={`${segment.regime}-${segment.startIndex}`}>
                <line
                  x1={x1}
                  y1={y(segment.regime)}
                  x2={x2}
                  y2={y(segment.regime)}
                  stroke={REGIME_COLORS[segment.regime]}
                  strokeWidth="9"
                  strokeLinecap="butt"
                />
                <title>
                  State {segment.regime}: {formatDate(segment.startDate)} to{" "}
                  {formatDate(segment.endDate)}
                </title>

                {index < segments.length - 1 && (
                  <line
                    x1={x2}
                    y1={y(segment.regime)}
                    x2={x2}
                    y2={y(segments[index + 1].regime)}
                    stroke={REGIME_COLORS[segments[index + 1].regime]}
                    strokeWidth="2"
                  />
                )}
              </g>
            );
          })}

          {splitIndex > 0 && (
            <g>
              <line
                x1={x(splitIndex)}
                y1={top - 18}
                x2={x(splitIndex)}
                y2={y(2) + 22}
                stroke="#e2e8f0"
                strokeDasharray="5 5"
                opacity="0.75"
              />
              <text
                x={x(splitIndex) + 6}
                y={top - 20}
                fill="currentColor"
                fontSize="10"
              >
                TEST START
              </text>
            </g>
          )}

          {dateTicks.map((index) => (
            <text
              key={index}
              x={x(index)}
              y={height - bottom + 22}
              textAnchor={
                index === 0
                  ? "start"
                  : index === rows.length - 1
                    ? "end"
                    : "middle"
              }
              fill="currentColor"
              opacity="0.7"
              fontSize="12"
            >
              {formatDate(rows[index].date)}
            </text>
          ))}
        </svg>
      </div>

      <div style={{ display: "flex", gap: 18, flexWrap: "wrap", fontSize: 12 }}>
        {STATES.map((state) => (
          <span
            key={state}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <span
              style={{
                width: 9,
                height: 9,
                borderRadius: "50%",
                background: REGIME_COLORS[state],
              }}
            />
            State {state}
          </span>
        ))}
      </div>
    </Panel>
  );
}

export default function RegimeExplorer() {
  const { result } = useBacktest();

  const isAdaptive = result?.strategy === "hmm_adaptive";

  const observations = useMemo(
    () =>
      normaliseObservations(
        result?.regime_history ?? result?.test_observations
      ),
    [result]
  );

  const testObservations = useMemo(
    () => normaliseObservations(result?.test_observations),
    [result]
  );

  const mapping = result?.regime_strategy_mapping ?? {};
  const trainingScores = result?.training_scores ?? [];

  const profiles = useMemo(() => {
    const base = STATES.map((regime) => {
      const rows = observations.filter((item) => item.regime === regime);

      return {
        regime,
        rows,
        count: rows.length,
        meanDailyReturn: average(rows, "dailyReturn"),
        meanVolatility: average(rows, "volatility20"),
        meanTrend: average(rows, "return20"),
        meanConfidence: average(rows, "confidence"),
      };
    });

    const ranked = base
      .filter((item) => item.count && item.meanVolatility != null)
      .sort((a, b) => a.meanVolatility - b.meanVolatility);

    return base.map((profile) => {
      const rank = ranked.findIndex(
        (item) => item.regime === profile.regime
      );

      const volatilityLabel =
        rank < 0
          ? "No observations"
          : ranked.length === 1
            ? "Volatility profile"
            : rank === 0
              ? "Lower relative volatility"
              : rank === ranked.length - 1
                ? "Higher relative volatility"
                : "Mid-range volatility";

      const trendLabel =
        profile.meanTrend == null
          ? "Trend unavailable"
          : profile.meanTrend > 0
            ? "Positive 20-day return"
            : profile.meanTrend < 0
              ? "Negative 20-day return"
              : "Flat 20-day return";

      return {
        ...profile,
        volatilityLabel,
        trendLabel,
      };
    });
  }, [observations]);

  const strategyRuns = useMemo(
    () => buildStrategyRuns(testObservations),
    [testObservations]
  );

  const latest = testObservations.at(-1);
  const activeRun = strategyRuns.at(-1);

  if (!isAdaptive) {
    return (
      <>
        <PageHeading
          eyebrow=""
          title="Regime Explorer"
          description=""
        />

        <Panel kicker="NO ADAPTIVE RESULT" title="Run an HMM Adaptive backtest">
          <p>
            Open Strategy Lab, select HMM Adaptive, and run the backtest.
            The regime timeline and strategy-switch history will appear here
            using the resulting model predictions.
          </p>
        </Panel>
      </>
    );
  }

  return (
    <>
      <PageHeading
        eyebrow=""
        title="Regime Explorer"
        description=""
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginBottom: 20,
        }}
      >
        {profiles.map((profile) => (
          <Panel
            key={profile.regime}
            kicker={`HMM STATE ${profile.regime}`}
            title={profile.volatilityLabel}
          >
            <div
              style={{
                borderLeft: `3px solid ${REGIME_COLORS[profile.regime]}`,
                paddingLeft: 12,
              }}
            >
              <strong>{profile.trendLabel}</strong>
              <dl className="kv-list" style={{ marginTop: 12 }}>
                <div>
                  <dt>Observations</dt>
                  <dd>{profile.count.toLocaleString("en-IN")}</dd>
                </div>
                <div>
                  <dt>Average daily return</dt>
                  <dd>{formatPercent(profile.meanDailyReturn)}</dd>
                </div>
                <div>
                  <dt>20-day volatility</dt>
                  <dd>{formatPercent(profile.meanVolatility)}</dd>
                </div>
                <div>
                  <dt>Average 20-day return</dt>
                  <dd>{formatPercent(profile.meanTrend)}</dd>
                </div>
                <div>
                  <dt>Average HMM confidence</dt>
                  <dd>{formatPercent(profile.meanConfidence)}</dd>
                </div>
                <div>
                  <dt>Mapped strategy</dt>
                  <dd>{strategyName(mapping[String(profile.regime)])}</dd>
                </div>
              </dl>
            </div>
          </Panel>
        ))}
      </div>

      <div style={{ marginBottom: 20 }}>
        <RegimeTimeline rows={observations} />
      </div>

      

      <div style={{ marginTop: 20 }}>
        <Panel kicker="" title="Strategy usage and switching history">
          <p style={{ fontSize: 13, opacity: 0.75 }}>
            
          </p>

          {strategyRuns.length === 0 ? (
            <p className="chart-empty">
              No strategy-switch history is available. Run an HMM Adaptive
              backtest first.
            </p>
          ) : (
            <div style={{ display: "grid", gap: 16, marginTop: 18 }}>
              {[...strategyRuns].reverse().map((run, index) => (
                <div
                  key={`${run.strategy}-${run.startDate}-${index}`}
                  style={{
                    padding: "14px 0",
                    borderBottom: "1px solid var(--border, #334155)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                      gap: 10,
                    }}
                  >
                    <div>
                      <strong>{strategyName(run.strategy)}</strong>
                      {run.isLatest && (
                        <span
                          style={{
                            marginLeft: 10,
                            fontSize: 11,
                            color: "#34d399",
                          }}
                        >
                          ACTIVE AT TEST END
                        </span>
                      )}
                    </div>
                    <strong>{run.days} trading days</strong>
                  </div>

                  <p style={{ fontSize: 12, opacity: 0.7, marginTop: 6 }}>
                    {formatDate(run.startDate)} — {formatDate(run.endDate)}
                  </p>

                  {run.previousStrategy && (
                    <p style={{ fontSize: 13, marginTop: 8 }}>
                      Changed on {formatDate(run.changedOn)}:{" "}
                      {strategyName(run.previousStrategy)} →{" "}
                      {strategyName(run.strategy)}
                    </p>
                  )}

                  <p style={{ fontSize: 13, marginTop: 8 }}>
                    <strong>Why this strategy?</strong>{" "}
                    {getSwitchReason(run, trainingScores)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      
    </>
  );
}