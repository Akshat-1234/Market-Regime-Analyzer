import { useCallback, useEffect, useState } from 'react';
import { NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { Activity, ArrowUpRight, BarChart3, CheckCircle2, ChevronRight, CircleDot, Database, FlaskConical, Layers3, LayoutDashboard, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { fetchJson, useApi } from './api';
import { WorkspaceContext } from './context';
import { ErrorBlock, Loading } from './components/Common';
import { RunDialog } from './components/RunDialog';
import type { OverviewData, Row, Run } from './types';
import { shortDate } from './utils';
import Overview from './pages/Overview';
import RegimeExplorer from './pages/RegimeExplorer';
import StrategyCompare from './pages/StrategyCompare';
import Validation from './pages/Validation';
import DataQuality from './pages/DataQuality';

const nav=[
  {to:'/',label:'Overview',icon:LayoutDashboard},
  {to:'/regimes',label:'Regime Explorer',icon:Layers3},
  {to:'/strategies',label:'Strategy Compare',icon:BarChart3},
  {to:'/validation',label:'Validation',icon:ShieldCheck},
  {to:'/data-quality',label:'Data Quality',icon:Database},
];
function runLabel(r:Run) {
  const history = r.control_history_sessions === undefined || r.control_history_sessions === null ? 'full history' : `${r.control_history_sessions}-session`;
  return `${r.run_id.slice(4,19).replace('_',' · ')}  /  ${history}`;
}
export default function App() {
  const [runs,setRuns]=useState<Run[]>([]);
  const [runId,setRunId]=useState('');
  const [start,setStart]=useState('');const [end,setEnd]=useState('');
  const [loadError,setLoadError]=useState<string|null>(null);
  const [runsLoaded,setRunsLoaded]=useState(false);
  const [dialog,setDialog]=useState(false);
  const [job,setJob]=useState<Row|null>(null);
  const location=useLocation();
  const current=nav.find(n=>n.to===location.pathname)?.label??'Overview';
  const refreshRuns=useCallback(async()=>{
    try {const response=await fetchJson<{runs:Run[]}>('/api/runs');setRuns(response.runs);setLoadError(null);setRunsLoaded(true);
      setRunId(old=> old && response.runs.some(r=>r.run_id===old && r.status==='completed') ? old : response.runs.find(r=>r.status==='completed' && r.has_research_artifacts)?.run_id??'');
    } catch(e){setLoadError(e instanceof Error?e.message:'API unavailable');}
  },[]);
  useEffect(()=>{refreshRuns();},[refreshRuns]);
  useEffect(()=>{let disposed=false;
    const check=async()=>{try{const j=await fetchJson<Row>('/api/job');if(!disposed){setJob(prev=>{if(prev?.status==='running' && j.status!=='running')refreshRuns();return j;});}}catch{/* API error is displayed by runs */}};
    check();const t=window.setInterval(check,4000);return()=>{disposed=true;clearInterval(t);};
  },[refreshRuns]);
  const overview=useApi<OverviewData>(runId?`/api/runs/${runId}/overview`:null);
  useEffect(()=>{if(overview.data){setStart(String(overview.data.metadata.first_return_date).slice(0,10));setEnd(String(overview.data.metadata.last_return_date).slice(0,10));}},[overview.data]);
  const ready=overview.data && start && end;
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><Activity size={21} strokeWidth={2.2}/></div><div><div className="brand-name">PROFNITT</div><div className="brand-sub">QUANT CLUB</div></div></div>
      <div className="side-label">RESEARCH WORKSPACE</div><nav aria-label="Primary navigation" className="side-nav">{nav.map(({to,label,icon:Icon})=><NavLink key={to} to={to} end={to==='/'} className={({isActive})=>`nav-item ${isActive?'active':''}`}><Icon size={18}/><span>{label}</span>{label==='Overview' && <span className="nav-dot"/>}</NavLink>)}</nav>
      <div className="sidebar-spacer"/><div className="side-card"><div className="side-card-top"><span className="status-dot"/> HISTORICAL DATA</div><strong>NIFTY 50 Index</strong><span>Research, not live trading.</span><div className="side-card-divider"/><span>Latest observation</span><b>{overview.data?shortDate(overview.data.metadata.data_end):'—'}</b></div>
      <div className="side-footer"><span>RESEARCH TERMINAL</span><span>v1.0</span></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><span>WORKSPACE</span><ChevronRight size={14}/><strong>{current}</strong></div>
      <div className="top-actions"><div className="historical-pill"><span className="status-dot"/>HISTORICAL ONLY</div>{job?.status==='running' && <span className="job-indicator"><span className="status-dot pulse"/>RUNNING</span>}{job?.status==='completed' && <span className="job-indicator"><span className="status-dot"/>RUN COMPLETE · SELECT RUN</span>}{job?.status==='failed' && <span className="job-indicator">RUN FAILED · CHECK LOGS</span>}
      <label className="run-select"><SlidersHorizontal size={14}/><span className="sr-only">Research run</span><select aria-label="Research run" value={runId} onChange={e=>setRunId(e.target.value)} disabled={!runs.length}>{runs.filter(r=>r.status==='completed'&&r.has_research_artifacts).map(r=><option key={r.run_id} value={r.run_id}>{runLabel(r)}</option>)}</select></label>
      <button className="button button-primary top-run" onClick={()=>setDialog(true)}><FlaskConical size={15}/>New run</button></div>
    </header>
    {loadError && <div className="content"><ErrorBlock message={`Cannot connect to the research API: ${loadError}`}/><p>Start the backend on port 8000 and reload.</p></div>}
    {!loadError && !runsLoaded && <div className="content"><Loading label="Discovering research runs"/></div>}
    {!loadError && runsLoaded && !runId && <div className="content"><ErrorBlock message="No completed research run found. Generate one using the research command or New run."/></div>}
    {overview.error && <div className="content"><ErrorBlock message={overview.error}/></div>}
    {!loadError && runId && overview.loading && <div className="content"><Loading/></div>}
    {ready && <WorkspaceContext.Provider value={{runId,info:overview.data!,runs,start,end,setStart,setEnd,setRunId,refreshRuns}}>
      <main className="content"><Routes><Route path="/" element={<Overview/>}/><Route path="/regimes" element={<RegimeExplorer/>}/><Route path="/strategies" element={<StrategyCompare/>}/><Route path="/validation" element={<Validation/>}/><Route path="/data-quality" element={<DataQuality/>}/><Route path="*" element={<Overview/>}/></Routes>
        <footer className="main-footer"><span><CircleDot size={12}/> RESEARCH USE ONLY · NO LIVE FEED</span><span>PROFNITT QUANT CLUB <ArrowUpRight size={12}/></span></footer></main>
    </WorkspaceContext.Provider>}
    </div>{dialog && <RunDialog onClose={()=>setDialog(false)} job={job} onStarted={()=>{refreshRuns();fetchJson<Row>('/api/job').then(setJob).catch(()=>{});}}/>}
  </div>;
}
