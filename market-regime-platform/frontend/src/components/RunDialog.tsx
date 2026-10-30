import { useEffect, useState } from 'react';
import { AlertTriangle, FlaskConical, X } from 'lucide-react';
import { fetchJson } from '../api';
import { ErrorBlock, Notice } from './Common';
import type { Row } from '../types';

export function RunDialog({ onClose, onStarted, job }: {onClose:()=>void; onStarted:()=>void; job:Row|null}) {
  const [form,setForm]=useState({start:'2012-01-01', execution_delay:1, simulations:200, bootstrap_samples:1000, seed:1701, block_length:20, control_history:63});
  const [error,setError]=useState<string|null>(null);
  const [busy,setBusy]=useState(false);
  const [submitted,setSubmitted]=useState(false);
  useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[onClose]);
  const change=(key:string,value:string)=>setForm({...form,[key]:key==='start'?value:Number(value)});
  async function launch(e:React.FormEvent) {
    e.preventDefault();setBusy(true);setError(null);
    try { await fetchJson('/api/job',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(form)});setSubmitted(true);onStarted(); }
    catch(e){setError(e instanceof Error?e.message:'Failed to start run');} finally {setBusy(false);}
  }
  return <div className="modal-backdrop" onMouseDown={onClose}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="new-run-title" onMouseDown={e=>e.stopPropagation()}>
    <div className="modal-head"><div><div className="eyebrow cyan">RESEARCH CONTROLS</div><h2 id="new-run-title">Create a new run</h2><p>Run the real walk-forward pipeline on the supplied dataset.</p></div><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={19}/></button></div>
    {submitted ? <><Notice tone="success"><strong>Research run started.</strong> This may take several minutes. Its status will appear in the run selector; existing artifacts are not changed.</Notice><div className="modal-actions"><button className="button button-primary" onClick={onClose}>Done</button></div></> : <form onSubmit={launch}>
      <div className="form-grid"><label>First signal date<input type="date" value={form.start} onChange={e=>change('start',e.target.value)} required/></label>
      <label>Execution timing<select value={form.execution_delay} onChange={e=>change('execution_delay',e.target.value)}><option value={1}>Delayed close (+1 session)</option><option value={0}>Same-close (optimistic)</option></select></label>
      <label>Simulations per control<input type="number" min="2" max="1000" value={form.simulations} onChange={e=>change('simulations',e.target.value)} required/></label>
      <label>Bootstrap samples<input type="number" min="2" max="5000" value={form.bootstrap_samples} onChange={e=>change('bootstrap_samples',e.target.value)} required/></label>
      <label>Random seed<input type="number" min="0" max="4294967295" value={form.seed} onChange={e=>change('seed',e.target.value)} required/></label>
      <label>Block length (sessions)<input type="number" min="1" max="252" value={form.block_length} onChange={e=>change('block_length',e.target.value)} required/></label>
      <label>Control history (sessions)<input type="number" min="0" max="5000" value={form.control_history} onChange={e=>change('control_history',e.target.value)} required/><small>0 = all prior history; otherwise at least 2.</small></label></div>
      <div className="modal-note"><AlertTriangle size={16}/><span>All settings are exploratory. Uses the project’s configured cash rate and costs (defaults: 6.5% and 10 bps). A new run takes real compute; no results are fabricated.</span></div>
      {form.execution_delay===0 && <Notice tone="warning">Same-close execution is an optimistic sensitivity case, not next-open execution.</Notice>}
      {job?.status==='running' && <Notice tone="warning">A run is already in progress. Wait for it to finish.</Notice>}{error && <ErrorBlock message={error}/>}
      <div className="modal-actions"><button className="button button-ghost" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={busy||job?.status==='running'}><FlaskConical size={16}/>{busy?'Starting…':'Start research run'}</button></div>
    </form>}
  </div></div>;
}
