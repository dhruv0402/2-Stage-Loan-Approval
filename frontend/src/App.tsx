import { useEffect, useState, type FormEvent } from 'react';
import { LayoutDashboard, FileText, BarChart3, HelpCircle, Menu } from 'lucide-react';
import { ApplicationForm, initial, type Input } from './components/ApplicationForm';
import { Result, type Assessment } from './components/Result';
import { ModelCard, type ModelInfo } from './components/ModelCard';
import { Dashboard } from './components/Dashboard';

type View='assessment'|'model'|'dashboard';
export default function App(){
  const [view,setView]=useState<View>('assessment');
  const [input,setInput]=useState<Input>(initial);
  const [result,setResult]=useState<Assessment|null>(null);
  const [card,setCard]=useState<ModelInfo|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [open,setOpen]=useState(false);
  useEffect(()=>{fetch('/api/model-card').then(r=>r.ok?r.json():Promise.reject()).then(setCard).catch(()=>{});},[]);
  function navigate(next:View){setView(next);setOpen(false)}
  async function submit(e:FormEvent){
    e.preventDefault();setBusy(true);setError('');
    try{
      const response=await fetch('/api/assess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input)});
      const body=await response.json();
      if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:'Assessment failed. Check the input fields.');
      setResult(body);
    }catch(err){setError(err instanceof Error?err.message:'API unavailable. Start the backend and load the model.')}
    finally{setBusy(false)}
  }
  function reset(){setInput(initial);setResult(null);setError('')}
  return <div className="shell">
    <aside className={`sidebar ${open?'open':''}`}><div className="brand">Underwrite<span className="brand-mark">◈</span></div>
      <nav aria-label="Main navigation"><button className={view==='dashboard'?'selected':''} onClick={()=>navigate('dashboard')}><LayoutDashboard/>Dashboard</button><button className={view==='assessment'?'selected':''} onClick={()=>navigate('assessment')}><FileText/>New assessment</button><button className={view==='model'?'selected':''} onClick={()=>navigate('model')}><BarChart3/>Model card</button></nav>
      <div className="sidebar-bottom"><button onClick={()=>navigate('model')}><HelpCircle/>About this demo</button><small>Research prototype · v0.2</small></div>
    </aside>
    <div className="workspace"><header className="topbar"><button className="mobile-menu" aria-label="Toggle navigation" onClick={()=>setOpen(!open)}><Menu/></button><span>Decision intelligence / Research demo</span><div className="avatar">U</div></header>
      <main>{view==='assessment'?<><div className="page-heading"><h1>Loan decision workbench</h1><p>Explore a historical funded-loan outcome and a policy-capped amount. For simulation only.</p></div><div className="work-grid"><ApplicationForm value={input} onChange={setInput} onSubmit={submit} onClear={reset} busy={busy}/><Result data={result} error={error}/></div></>:view==='model'?<ModelCard card={card}/>:<Dashboard card={card} onAssess={()=>navigate('assessment')}/>}</main>
    </div>
  </div>
}
