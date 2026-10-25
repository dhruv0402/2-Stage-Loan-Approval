import { useEffect, useState, type FormEvent } from 'react';
import { LayoutDashboard, FileText, BarChart3, HelpCircle, Menu, Sliders, ShieldCheck } from 'lucide-react';
import { ApplicationForm, initial, type Input } from './components/ApplicationForm';
import { Result, type Assessment } from './components/Result';
import { ModelCard, type ModelInfo } from './components/ModelCard';
import { Dashboard } from './components/Dashboard';
import { StressTesting } from './components/StressTesting';
import { ExplainabilityCenter } from './components/ExplainabilityCenter';

type View = 'assessment' | 'model' | 'dashboard' | 'stresstest' | 'audit';

export default function App() {
  const [view, setView] = useState<View>('assessment');
  const [input, setInput] = useState<Input>(initial);
  const [result, setResult] = useState<Assessment | null>(null);
  const [card, setCard] = useState<ModelInfo | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch('/api/model-card')
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(setCard)
      .catch(() => {});
  }, []);

  function navigate(next: View) {
    setView(next);
    setOpen(false);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input)
      });
      const body = await response.json();
      if (!response.ok)
        throw new Error(
          typeof body.detail === 'string'
            ? body.detail
            : Array.isArray(body.detail)
            ? body.detail.map((d: any) => d.msg).join(', ')
            : 'Assessment failed. Check input fields.'
        );
      setResult(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'API unavailable. Start the backend server.');
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setInput(initial);
    setResult(null);
    setError('');
  }

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', letterSpacing: '-0.02em' }}>
          <span>Credence</span><span style={{ color: '#4f46e5', fontWeight: 800 }}>AI</span><span className="brand-mark">◈</span>
        </div>
        <nav aria-label="Main navigation">
          <button className={view === 'dashboard' ? 'selected' : ''} onClick={() => navigate('dashboard')}>
            <LayoutDashboard size={18} />
            Overview & Metrics
          </button>
          <button className={view === 'assessment' ? 'selected' : ''} onClick={() => navigate('assessment')}>
            <FileText size={18} />
            Loan Decision Center
          </button>
          <button className={view === 'stresstest' ? 'selected' : ''} onClick={() => navigate('stresstest')}>
            <Sliders size={18} />
            Market Simulator
          </button>
          <button className={view === 'audit' ? 'selected' : ''} onClick={() => navigate('audit')}>
            <ShieldCheck size={18} />
            Fairness & Insights
          </button>
          <button className={view === 'model' ? 'selected' : ''} onClick={() => navigate('model')}>
            <BarChart3 size={18} />
            Model Accuracy & Proof
          </button>
        </nav>
        <div className="sidebar-bottom">
          <button onClick={() => navigate('model')}>
            <HelpCircle size={16} />
            System Performance
          </button>
          <small>Credence AI · Smart Credit Platform</small>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <button className="mobile-menu" aria-label="Toggle navigation" onClick={() => setOpen(!open)}>
            <Menu />
          </button>
          <span>Credence AI — Intelligent Credit Decision Platform</span>
          <div className="avatar">C</div>
        </header>

        <main>
          {view === 'assessment' ? (
            <>
              <div className="page-heading">
                <h1>Instant Loan Decision Center</h1>
                <p>
                  Check loan approval eligibility, view sanctioned amounts, and see transparent interest rates in real time.
                </p>
              </div>
              <div className="work-grid">
                <ApplicationForm value={input} onChange={setInput} onSubmit={submit} onClear={reset} busy={busy} />
                <Result data={result} error={error} />
              </div>
            </>
          ) : view === 'stresstest' ? (
            <StressTesting />
          ) : view === 'audit' ? (
            <ExplainabilityCenter />
          ) : view === 'model' ? (
            <ModelCard card={card} />
          ) : (
            <Dashboard card={card} onAssess={() => navigate('assessment')} />
          )}
        </main>
      </div>
    </div>
  );
}
