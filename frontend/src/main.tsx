import React from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const q = async (path:string)=>{ const r=await fetch(API+path); if(!r.ok) throw new Error(await r.text()); return r.json(); };

function App(){
  const [run,setRun]=React.useState(''); const [service,setService]=React.useState(''); const [search,setSearch]=React.useState('');
  const summary=useQuery({queryKey:['summary',run],queryFn:()=>q('/api/v1/resources/summary'+(run?'?inventory_run_id='+encodeURIComponent(run):''))});
  const resources=useQuery({queryKey:['resources',run,service,search],queryFn:()=>q('/api/v1/resources?limit=100'+(run?'&inventory_run_id='+encodeURIComponent(run):'')+(service?'&service='+encodeURIComponent(service):'')+(search?'&search='+encodeURIComponent(search):''))});
  const runs=useQuery({queryKey:['runs'],queryFn:()=>q('/api/v1/inventory-runs?limit=25')});
  const [accounts,setAccounts]=React.useState('');
  async function start(){ const ids=accounts.split(',').map(x=>x.trim()).filter(Boolean); if(!ids.length)return; await fetch(API+'/api/v1/inventory-runs',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({account_ids:ids})}); runs.refetch(); }
  return <div className="app"><header><div><h1>AWS Cloud Inventory</h1><p>Read-only multi-account inventory</p></div><div className="actions"><input placeholder="account IDs, comma separated" value={accounts} onChange={e=>setAccounts(e.target.value)}/><button onClick={start}>Run inventory</button></div></header>
  <main><section className="cards"><Card t="Resources" v={summary.data?.resource_count ?? '—'}/><Card t="Accounts" v={summary.data?.accounts?.length ?? '—'}/><Card t="Services" v={summary.data?.services?.length ?? '—'}/><Card t="No Owner" v={summary.data?.missing_owner ?? '—'}/></section>
  <section className="panel"><div className="toolbar"><select value={run} onChange={e=>setRun(e.target.value)}><option value="">All runs</option>{runs.data?.items?.map((r:any)=><option key={r.run_id} value={r.run_id}>{r.run_id.slice(0,8)} · {r.status}</option>)}</select><select value={service} onChange={e=>setService(e.target.value)}><option value="">All services</option>{summary.data?.services?.map((s:string)=><option key={s}>{s}</option>)}</select><input placeholder="Search name, ID or ARN" value={search} onChange={e=>setSearch(e.target.value)}/><a href={API+'/api/v1/resources/export.csv'+(run?'?inventory_run_id='+encodeURIComponent(run):'')} target="_blank">CSV</a><a href={API+'/api/v1/resources/export.json'+(run?'?inventory_run_id='+encodeURIComponent(run):'')} target="_blank">JSON</a></div>
  <table><thead><tr><th>Name</th><th>Type</th><th>Service</th><th>Account</th><th>Region</th><th>State</th><th>Owner</th><th>Environment</th></tr></thead><tbody>{resources.data?.items?.map((r:any)=><tr key={r.resource_type+r.resource_id}><td>{r.resource_name||r.resource_id}</td><td>{r.resource_type}</td><td>{r.service}</td><td>{r.account_id}</td><td>{r.region||'global'}</td><td>{r.state||'—'}</td><td>{r.owner||<span className="warn">missing</span>}</td><td>{r.environment||'—'}</td></tr>)}</tbody></table></section>
  <section className="panel"><h2>Inventory runs</h2><table><thead><tr><th>Run</th><th>Status</th><th>Started</th><th>Resources</th><th>Errors</th></tr></thead><tbody>{runs.data?.items?.map((r:any)=><tr key={r.run_id}><td>{r.run_id}</td><td>{r.status}</td><td>{new Date(r.started_at).toLocaleString()}</td><td>{r.resource_count}</td><td>{r.error_count}</td></tr>)}</tbody></table></section></main></div>
}
function Card({t,v}:{t:string,v:any}){return <div className="card"><span>{t}</span><strong>{v}</strong></div>}
createRoot(document.getElementById('root')!).render(<QueryClientProvider client={new QueryClient()}><App/></QueryClientProvider>);
