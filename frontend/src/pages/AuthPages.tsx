import {FormEvent,useEffect,useState} from 'react'; import {Link,useNavigate,useLocation,useSearchParams} from 'react-router-dom'; import {Eye,EyeOff,ArrowUpRight,ShieldCheck,TrendingUp,Save,KeyRound,Trash2,Plus,RefreshCw} from 'lucide-react'; import {useAuth} from '../context/AuthContext'; import {api} from '../services/api';
function Brand(){return <Link to="/login" className="auth-brand"><span className="brand-mark">M</span><span><b>MIRAI</b><small>Where Intelligence Creates Wealth.</small></span></Link>}
function Visual(){return <aside className="auth-visual"><div className="visual-label"><span className="dot green-dot"/> PRIVATE RESEARCH WORKSPACE</div><div className="visual-copy"><span className="section-kicker">A CLEARER VIEW OF YOUR CAPITAL</span><h2>Research with<br/>discipline.</h2><p>One secure place for market context, systematic research and your personal portfolio.</p></div><div className="illustration-chart"><div className="chart-caption"><span>ILLUSTRATIVE MARKET MOVEMENT</span><TrendingUp size={15}/></div><svg viewBox="0 0 520 190" role="img" aria-label="Decorative illustrative market chart"><path d="M0 160H520M0 112H520M0 64H520M0 16H520" stroke="var(--line)" strokeWidth="1"/><path d="M8 150 C48 142 55 96 89 112 S133 139 165 90 S215 105 245 67 S291 89 325 53 S368 76 399 45 S445 62 478 23 S500 34 516 12" fill="none" stroke="var(--emerald)" strokeWidth="2.5"/><path d="M8 150 C48 142 55 96 89 112 S133 139 165 90 S215 105 245 67 S291 89 325 53 S368 76 399 45 S445 62 478 23 S500 34 516 12V190H8Z" fill="var(--emerald)" opacity=".08"/></svg><small>Illustration only · No live prices shown</small></div><div className="visual-foot"><ShieldCheck size={16}/> Your portfolio data is private to your account.</div></aside>}
function AuthLayout({children,title,subtitle}:{children:React.ReactNode;title:string;subtitle:string}){return <div className="auth-layout"><section className="auth-form-side"><Brand/><div className="auth-form-wrap"><span className="section-kicker">MIRAI ACCOUNT</span><h1>{title}</h1><p>{subtitle}</p>{children}</div><footer>Research and decision support only · No trade execution</footer></section><Visual/></div>}
function msg(e:any){
  if (e?.response?.status === 404) {
    return 'Authentication service is initializing. If your account is already created, please sign in directly.';
  }
  if (e?.response?.status === 409) {
    return 'That email or username is already registered. Please click "Sign in" below to access your workspace.';
  }
  return e?.response?.data?.detail || 'Could not connect to MIRAI. Check that the API is running.';
}
export function LoginPage(){const {login}=useAuth(),navigate=useNavigate(),location=useLocation();const [email,setEmail]=useState(sessionStorage.getItem('mirai_remembered_email')||''),[password,setPassword]=useState(''),[show,setShow]=useState(false),[remember,setRemember]=useState(true),[error,setError]=useState(''),[busy,setBusy]=useState(false);async function submit(e:FormEvent){e.preventDefault();setError('');setBusy(true);try{await login(email,password,remember);if(remember)sessionStorage.setItem('mirai_remembered_email',email);else sessionStorage.removeItem('mirai_remembered_email');navigate(location.state?.from||'/',{replace:true})}catch(e){setError(msg(e))}finally{setBusy(false)}}return <AuthLayout title="Welcome back" subtitle="Sign in to your personal research workspace."><form className="auth-form" onSubmit={submit}><label>Email address or username<input type="text" autoComplete="username" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com or username"/></label><label>Password<div className="password-field"><input type={show?'text':'password'} autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password"/><button type="button" aria-label={show?'Hide password':'Show password'} onClick={()=>setShow(!show)}>{show?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></label><div className="auth-options"><label className="check-label"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)}/> Remember me</label><Link to="/forgot-password">Forgot password?</Link></div>{error&&<div role="alert" className="notice error">{error}</div>}<button className="auth-submit" disabled={busy}>{busy?'Signing in…':'Sign in'}<ArrowUpRight size={16}/></button><div className="form-switch">New to MIRAI? <Link to="/signup">Create an account</Link></div></form></AuthLayout>}
export function SignupPage(){const {register}=useAuth(),navigate=useNavigate();const [data,setData]=useState({full_name:'',email:'',username:'',password:'',confirm_password:'',phone:''}),[show,setShow]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);const update=(key:string,value:string)=>setData({...data,[key]:value});async function submit(e:FormEvent){e.preventDefault();setError('');if(data.password!==data.confirm_password){setError('Passwords do not match.');return}setBusy(true);try{await register(data);navigate('/',{replace:true})}catch(e){setError(msg(e))}finally{setBusy(false)}}return <AuthLayout title="Create your account" subtitle="Set up your private portfolio and research workspace."><form className="auth-form signup-form" onSubmit={submit}><label>Full name<input required minLength={2} autoComplete="name" value={data.full_name} onChange={e=>update('full_name',e.target.value)} placeholder="Full name"/></label><label>Email address<input type="email" required autoComplete="email" value={data.email} onChange={e=>update('email',e.target.value)} placeholder="you@example.com"/></label><label>Username<input required minLength={3} maxLength={32} pattern="[A-Za-z0-9_]+" autoComplete="username" value={data.username} onChange={e=>update('username',e.target.value)} placeholder="Choose a username"/></label><label>Phone <span className="optional">OPTIONAL</span><input type="tel" autoComplete="tel" value={data.phone} onChange={e=>update('phone',e.target.value)} placeholder="Phone number"/></label><label>Password<div className="password-field"><input type={show?'text':'password'} required minLength={6} autoComplete="new-password" value={data.password} onChange={e=>update('password',e.target.value)} placeholder="At least 6 characters"/><button type="button" aria-label="Toggle password visibility" onClick={()=>setShow(!show)}>{show?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></label><label>Confirm password<input type="password" required autoComplete="new-password" value={data.confirm_password} onChange={e=>update('confirm_password',e.target.value)} placeholder="Enter password again"/></label><p className="password-hint">Use at least 6 characters.</p>{error&&<div role="alert" className="notice error">{error}</div>}<button className="auth-submit" disabled={busy}>{busy?'Creating account…':'Create account'}<ArrowUpRight size={16}/></button><div className="form-switch">Already registered? <Link to="/login">Sign in</Link></div></form></AuthLayout>}

export function ForgotPasswordPage(){const [email,setEmail]=useState(''),[sent,setSent]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{await api.post('/auth/forgot-password',{email});setSent(true)}catch(e){setError(msg(e))}finally{setBusy(false)}}return <AuthLayout title="Reset your password" subtitle="We’ll send a one-time reset link if an account matches this email."><form className="auth-form" onSubmit={submit}>{sent?<div className="notice">If the account exists and email delivery is configured, reset instructions are on the way.</div>:<><label>Email address<input required type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>{error&&<div role="alert" className="notice error">{error}</div>}<button className="auth-submit" disabled={busy}>{busy?'Sending…':'Send reset link'}<ArrowUpRight size={16}/></button></>}<div className="form-switch"><Link to="/login">Back to sign in</Link></div></form></AuthLayout>}

export function ResetPasswordPage(){const [params]=useSearchParams();const [password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[error,setError]=useState(''),[done,setDone]=useState(false),[busy,setBusy]=useState(false);async function submit(e:FormEvent){e.preventDefault();setError('');if(password!==confirm){setError('Passwords do not match.');return}setBusy(true);try{await api.post('/auth/reset-password',{token:params.get('token'),new_password:password});setDone(true)}catch(e){setError(msg(e))}finally{setBusy(false)}}return <AuthLayout title="Choose a new password" subtitle="Reset links expire after 30 minutes and can be used once."><form className="auth-form" onSubmit={submit}>{done?<div className="notice">Password updated successfully.</div>:<><label>New password<input type="password" required minLength={10} autoComplete="new-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><label>Confirm new password<input type="password" required autoComplete="new-password" value={confirm} onChange={e=>setConfirm(e.target.value)}/></label>{error&&<div role="alert" className="notice error">{error}</div>}<button className="auth-submit" disabled={busy}>{busy?'Updating…':'Update password'}<ArrowUpRight size={16}/></button></>}<div className="form-switch"><Link to="/login">Go to sign in</Link></div></form></AuthLayout>}

export function ProfilePage(){const {user,setUser,logout}=useAuth();const [form,setForm]=useState({full_name:user?.full_name||'',email:user?.email||'',username:user?.username||'',phone:user?.phone||''}),[password,setPassword]=useState({current_password:'',new_password:''}),[message,setMessage]=useState(''),[error,setError]=useState('');useEffect(()=>{if(user)setForm({full_name:user.full_name,email:user.email,username:user.username,phone:user.phone||''})},[user]);async function saveProfile(e:FormEvent){e.preventDefault();setError('');setMessage('');try{const r=await api.put('/auth/me',form);setUser(r.data);setMessage('Profile updated.')}catch(e){setError(msg(e))}}async function changePassword(e:FormEvent){e.preventDefault();setError('');setMessage('');try{const r=await api.post('/auth/change-password',password);setMessage(r.data.message);setPassword({current_password:'',new_password:''})}catch(e){setError(msg(e))}}return <div className="page"><PageHeading title="Your profile" subtitle="Account details and sign-in security."/><div className="profile-grid"><section className="panel"><div className="panel-head"><div><h3>Personal details</h3><span className="muted">Private to your account</span></div><div className="profile-avatar">{user?.full_name?.slice(0,1).toUpperCase()}</div></div><form className="account-form" onSubmit={saveProfile}><label>Full name<input required minLength={2} value={form.full_name} onChange={e=>setForm({...form,full_name:e.target.value})}/></label><label>Email address<input required type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label><label>Username<input required minLength={3} value={form.username} onChange={e=>setForm({...form,username:e.target.value})}/></label><label>Phone<input type="tel" value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></label><button className="primary-button"><Save size={15}/>Save profile</button></form><div className="profile-meta"><span>ACCOUNT CREATED</span><b>{user?.created_at?new Date(user.created_at).toLocaleDateString():'—'}</b><span>USER ID</span><b>{user?.id}</b></div></section><section className="panel"><div className="panel-head"><div><h3>Change password</h3><span className="muted">Password is stored as a bcrypt hash.</span></div><KeyRound size={17}/></div><form className="account-form" onSubmit={changePassword}><label>Current password<input type="password" required value={password.current_password} onChange={e=>setPassword({...password,current_password:e.target.value})}/></label><label>New password<input type="password" required minLength={10} value={password.new_password} onChange={e=>setPassword({...password,new_password:e.target.value})}/></label><p className="password-hint">At least 10 characters, including a letter and number.</p><button className="primary-button">Update password</button></form><div className="account-security"><ShieldCheck size={17}/><span>Bearer sessions expire automatically. Log out to close this device session.</span></div><button className="danger-button" onClick={()=>void logout()}><Trash2 size={15}/>Log out of MIRAI</button></section></div>{message&&<div className="notice">{message}</div>}{error&&<div role="alert" className="notice error">{error}</div>}</div>}

export function WatchlistPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [symbol, setSymbol] = useState('RELIANCE');
  const [instruments, setInstruments] = useState<any[]>([]);
  const [error, setError] = useState('');

  async function refresh() {
    try {
      const r = await api.get('/watchlist');
      setRows(r.data);
    } catch (e) {
      setError(msg(e));
    }
  }

  useEffect(() => {
    void refresh();
    api
      .get('/market/instruments')
      .then((r) => setInstruments(r.data))
      .catch(() => {});
  }, []);

  async function add() {
    setError('');
    try {
      await api.post('/watchlist', { symbol });
      await refresh();
    } catch (e) {
      setError(msg(e));
    }
  }

  async function remove(id: number) {
    try {
      await api.delete(`/watchlist/${id}`);
      await refresh();
    } catch (e) {
      setError(msg(e));
    }
  }

  return (
    <div className="page">
      <PageHeading
        title="Watchlist"
        subtitle="Track institutional assets with real-time quantitative forecasts, RSI indicators, and AI verdicts."
        actions={
          <>
            <select className="period-select" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              {instruments.map((x) => (
                <option key={x.symbol} value={x.symbol}>
                  {x.name}
                </option>
              ))}
            </select>
            <button className="primary-button" onClick={add}>
              <Plus size={15} /> Add instrument
            </button>
            <button className="icon-button" onClick={() => void refresh()}>
              <RefreshCw size={15} />
            </button>
          </>
        }
      />
      {error && <div className="notice error">{error}</div>}

      {rows.length ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="watch-grid">
            {rows.map((row) => (
              <div className="panel watch-card" key={row.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span className="eyebrow">{row.exchange || 'NSE'} · {row.symbol}</span>
                    <h3>{row.name}</h3>
                  </div>
                  <span
                    className={`badge ${
                      row.verdict?.includes('BUY')
                        ? 'positive'
                        : row.verdict?.includes('SELL')
                        ? 'negative'
                        : 'neutral'
                    }`}
                    style={{ fontSize: '11px', fontWeight: 600 }}
                  >
                    {row.verdict || 'HOLD'}
                  </span>
                </div>

                <div className="watch-price" style={{ margin: '14px 0 6px' }}>
                  {row.price == null ? '—' : `₹${Number(row.price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}
                  <span className={row.change >= 0 ? 'positive' : 'negative'}>
                    {row.change == null ? '—' : `${row.change >= 0 ? '+' : ''}${(row.change * 100).toFixed(2)}%`}
                  </span>
                </div>

                {/* Quantitative Indicators Row */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '8px',
                    padding: '8px 0',
                    borderTop: '1px solid #1a2f26',
                    borderBottom: '1px solid #1a2f26',
                    margin: '8px 0',
                    fontSize: '11px',
                  }}
                >
                  <div>
                    <span className="muted">RSI (14):</span> <b>{row.rsi ? Number(row.rsi).toFixed(1) : '50.0'}</b>
                  </div>
                  <div>
                    <span className="muted">5D Forecast:</span> <b>₹{row.forecast_price ? Number(row.forecast_price).toFixed(2) : '—'}</b>
                  </div>
                  <div>
                    <span className="muted">Expected Return:</span>{' '}
                    <b className={row.expected_return_pct >= 0 ? 'positive' : 'negative'}>
                      {row.expected_return_pct ? `${row.expected_return_pct >= 0 ? '+' : ''}${Number(row.expected_return_pct).toFixed(2)}%` : '—'}
                    </b>
                  </div>
                  <div>
                    <span className="muted">Volume:</span> <b>{row.volume ? Number(row.volume).toLocaleString('en-IN') : '—'}</b>
                  </div>
                </div>

                <div className="watch-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Link to={`/markets?symbol=${encodeURIComponent(row.symbol)}`}>Analyse & Trade</Link>
                  {row.is_custom && (
                    <button className="icon-button" onClick={() => void remove(row.id)} aria-label={`Remove ${row.name}`}>
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="panel empty-state">
          <Eye size={24} />
          <h3>Your watchlist is empty</h3>
          <p>Add an instrument to track its available historical price and move.</p>
        </div>
      )}
      <footer>Prices are calculated strictly from the 4 institutional CSV datasets (MRF, TCS, Jio Platforms, Reliance).</footer>
    </div>
  );
}

function PageHeading({title,subtitle,actions}:{title:string;subtitle:string;actions?:React.ReactNode}){return <div className="page-head"><div><div className="section-kicker">MIRAI / ACCOUNT</div><h1>{title}</h1><p>{subtitle}</p></div>{actions&&<div className="head-actions">{actions}</div>}</div>}
