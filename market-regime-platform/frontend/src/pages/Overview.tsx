import { ArrowRight, BarChart3, Clock3, Gauge, Layers3, ShieldCheck, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useApi, query } from '../api';
import { useWorkspace } from '../context';
import { Badge, CsvLink, DateRange, ErrorBlock, Loading, Notice, PageHeading, Panel, PanelTitle, ReportLink, StatCard } from '../components/Common';
import { EquityChart, Legend } from '../components/Charts';
import type { SeriesData } from '../types';
import { evidence, integer, num, pct, shortDate, signed, signedPct, stateName, strategyColor } from '../utils';

const names=['HMM + Trend','Trend 50','Buy & Hold'];
export default function Overview(){
  const {runId,info,start,end}=useWorkspace();
  const {data,error,loading}=useApi<SeriesData>(query(`/api/runs/${runId}/series`,{start,end,strategies:names.join(',')}));
  const stat=(name:string)=>data?.stats.find(x=>x.strategy===name);
  const real=stat('HMM + Trend'), trend=stat('Trend 50');
  const boot=info.bootstrap.find(x=>x.control==='Trend');
  const fullReal=info.performance.find(x=>x.strategy==='HMM + Trend');
  const fullTrend=info.performance.find(x=>x.strategy==='Trend 50');
  const evidenceLabel=evidence(info.bootstrap);
  const delay=info.backtest.execution_delay_sessions;
  const ciMin=boot?Math.min(0,boot.lower)-(Math.abs(boot.upper-boot.lower)||.1)*.12:-.3;
  const ciMax=boot?Math.max(0,boot.upper)+(Math.abs(boot.upper-boot.lower)||.1)*.12:.3;
  const position=(value:number)=>Math.max(0,Math.min(100,(value-ciMin)/(ciMax-ciMin)*100));
  return <div className="page overview-page">
    <PageHeading eyebrow="MARKET INTELLIGENCE  /  01" title="Research overview" description="A clearer view of what regime information really adds.">
      <div className="header-tag"><span className="status-dot"/>NIFTY 50 · HISTORICAL</div>
    </PageHeading>
    <div className="hero-grid"><section className="hero-panel"><div className="hero-decoration" aria-hidden="true"><span/><span/><span/><span/><span/></div>
      <div className="hero-kicker"><span className="hero-number">01</span> THE RESEARCH QUESTION</div>
      <h2>Does knowing the regime<br/><em>make a difference?</em></h2>
      <p>Testing an HMM + trend blend against trend alone and causal random controls—without assuming an edge.</p>
      <div className="hero-bottom"><Badge tone={evidenceLabel==='INTERVAL INCLUDES ZERO'?'amber':'neutral'}>{evidenceLabel}</Badge><span>PAIRED BLOCK BOOTSTRAP · FULL SAMPLE</span></div>
    </section>
    <section className="hero-result"><div className="hero-result-top"><div><div className="eyebrow">HMM + TREND VS TREND</div><h3>Incremental Sharpe</h3></div><div className="result-icon"><Gauge size={19}/></div></div>
      <div className="hero-number-row"><strong>{signed(boot?.observed_sharpe_difference)}</strong><span>observed difference</span></div>
      <div className="ci-scale"><div className="ci-track"/><span className="ci-zero" style={{left:`${position(0)}%`}}/><span className="ci-range" style={boot?{left:`${position(boot.lower)}%`,right:`${100-position(boot.upper)}%`}:undefined}/></div>
      <div className="ci-labels"><span>LOWER {signed(boot?.lower)}</span><span>ZERO</span><span>UPPER {signed(boot?.upper)}</span></div>
      <div className="hero-result-foot"><span>95% paired bootstrap interval</span><span className="muted">not a p-value</span></div>
    </section></div>
    <div className="section-toolbar"><div><div className="eyebrow">PERFORMANCE SNAPSHOT</div><h2>Out-of-sample results <span className="section-sub">/ selected return dates</span></h2></div><DateRange compact/></div>
    {error && <ErrorBlock message={error}/>}
    {loading && <Loading label="Recalculating selected-period metrics"/>}
    {data && <><div className="stats-grid">
      <StatCard label="ANNUALIZED RETURN" value={pct(real?.cagr)} meta={<>Trend {pct(trend?.cagr)} <span className="meta-separator">·</span> net of costs</>} icon={<TrendingUp size={16}/>}/>
      <StatCard label="SHARPE RATIO" value={num(real?.sharpe,3)} meta={<>Trend {num(trend?.sharpe,3)} <span className="meta-separator">·</span> {pct(info.backtest.annual_risk_free_rate)} cash</>} icon={<Gauge size={16}/>}/>
      <StatCard label="MAX DRAWDOWN" value={pct(real?.max_drawdown)} meta={<>Trend {pct(trend?.max_drawdown)} <span className="meta-separator">·</span> window-rebased</>} icon={<ShieldCheck size={16}/>}/>
      <StatCard label="MEAN EXPOSURE" value={pct(real?.mean_exposure)} meta={<>Trend {pct(trend?.mean_exposure)} <span className="meta-separator">·</span> long-only</>} icon={<Layers3 size={16}/>}/>
    </div>
    <Panel className="equity-panel"><PanelTitle eyebrow="PERFORMANCE  /  REBASED TO 100" title="Growth of capital" description={`Continuous portfolio returns · ${integer(data.observations)} sessions · ${shortDate(data.start)} to ${shortDate(data.end)}`} aside={<CsvLink name="daily_returns">Full daily CSV</CsvLink>}/>
      <div className="chart-header"><Legend names={names}/><span>BASE = 100</span></div><EquityChart data={data.equity} names={names} height={282}/>
      <div className="panel-foot"><span>Returns are net of recorded costs. The chart is sampled; metrics use all daily returns.</span><Link to="/strategies">Compare strategies <ArrowRight size={14}/></Link></div>
    </Panel>
    <div className="overview-lower"><Panel><PanelTitle eyebrow="CROSS-STRATEGY  /  SELECTED WINDOW" title="Strategy snapshot" aside={<Link className="text-link" to="/strategies">Full comparison <ArrowRight size={14}/></Link>}/>
      <div className="snapshot-head"><span>STRATEGY</span><span>RETURN</span><span>SHARPE</span><span>MAX DD</span></div>
      {names.map(n=>{const r=stat(n);return <div className="snapshot-row" key={n}><span className="strategy-label"><i style={{background:strategyColor[n]}}/>{n}</span><span>{pct(r?.cagr)}</span><span>{num(r?.sharpe,2)}</span><span>{pct(r?.max_drawdown)}</span></div>;})}
      <div className="small-note">Return is annualized; max drawdown is shown as a positive loss magnitude.</div>
    </Panel><Panel><PanelTitle eyebrow="PRIMARY MODEL  /  FULL RUN" title="Regime distribution" aside={<Link className="text-link" to="/regimes">Explore <ArrowRight size={14}/></Link>}/>
      <p className="panel-description">Filtered states ranked by training volatility; labels can change after refits.</p>
      <div className="occupancy-list">{info.regime_summary.map(row=><div className="occupancy-row" key={row.state_by_train_vol}><div><span><i className={`state-dot state-${row.state_by_train_vol}`}/>STATE {row.state_by_train_vol} <small>{stateName(row.state_by_train_vol)}</small></span><strong>{pct(row.occupancy)}</strong></div><div className="progress-track"><span className={`state-fill state-${row.state_by_train_vol}`} style={{width:`${row.occupancy*100}%`}}/></div></div>)}</div>
      <div className="small-note">{integer(info.regime_summary.reduce((a,r)=>a+r.days,0))} decision-linked observations · {info.metadata.primary_model}</div>
    </Panel></div></>}
    <div className="insight-strip"><div className="insight-icon"><BarChart3 size={18}/></div><div><span className="eyebrow">RESEARCH TAKEAWAY · FULL SAMPLE</span><p>{boot && boot.lower<=0 && boot.upper>=0 ? 'The interval includes zero: the historical results do not establish a Sharpe improvement over trend alone.' : 'Interpret the historical Sharpe difference alongside the bootstrap interval, costs and prior model selection.'} {fullReal && fullTrend && <>The blend’s realized drawdown was {pct(fullReal.max_drawdown)} versus {pct(fullTrend.max_drawdown)} for trend.</>}</p></div><ReportLink name="overall">Read research report</ReportLink></div>
    <Notice tone="warning"><strong>Historical only.</strong> Data end {shortDate(info.metadata.data_end)}. {delay===0?'Same-close execution is an optimistic sensitivity case.':'A signal at close t is executed at the next session’s close and earns the following close-to-close return—not the next open.'} Transaction costs are {num(info.backtest.transaction_cost_bps,0)} bps one-way; dividends, taxes and impact are excluded.</Notice>
  </div>;
}
