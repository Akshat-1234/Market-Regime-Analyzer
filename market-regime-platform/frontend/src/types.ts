export type Row = Record<string, any>;
export interface Run extends Row {
  run_id: string;
  status: string;
  has_research_artifacts: boolean;
  data_end?: string;
  control_history_sessions?: number | null;
}
export interface OverviewData {
  status: Run;
  metadata: Row;
  data_manifest: Row;
  holdout: Row;
  backtest: Row;
  performance: Row[];
  regime_summary: Row[];
  bootstrap: Row[];
  strategies: string[];
  models: string[];
}
export interface SeriesData {
  start: string; end: string; observations: number; sampled_points: number;
  equity: Row[]; drawdown: Row[]; stats: Row[]; basis: string;
}
export interface Workspace {
  runId: string;
  info: OverviewData;
  runs: Run[];
  start: string;
  end: string;
  setStart: (v: string) => void;
  setEnd: (v: string) => void;
  setRunId: (v: string) => void;
  refreshRuns: () => Promise<void>;
}
