import {useEffect,useState} from 'react'; import {api,loadHistory,loadOverview,Instrument} from '../services/api'; import Metric from '../components/Metric'; import PriceChart from '../components/PriceChart'; import {ArrowUpRight,RefreshCw,Send,Plus,Trash2,Play,AlertTriangle,ChevronDown} from 'lucide-react';
const defaultInstrument='RELIANCE'; const fmt=(v:any,d=2)=>v==null?'—':Number(v).toLocaleString('en-IN',{minimumFractionDigits:d,maximumFractionDigits:d}); const pct=(v:any)=>v==null?'—':`${(Number(v)*100).toFixed(2)}%`;
function useMarket(period='1y'){const [symbol,setSymbol]=useState(()=>new URLSearchParams(window.location.search).get('symbol')||defaultInstrument),[overview,setOverview]=useState<any>(null),[hist,setHist]=useState<any[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);const refresh=async()=>{setBusy(true);setError('');try{const [o,h]=await Promise.all([loadOverview(symbol,period),loadHistory(symbol,period)]);setOverview(o);setHist(h.data)}catch(e:any){setError(e?.response?.data?.detail||'Market data unavailable. Check the API connection.')}finally{setBusy(false)}};useEffect(()=>{void refresh()},[symbol,period]);return {symbol,setSymbol,overview,hist,error,busy,refresh}}
function Head({title,sub,actions}:{title:string;sub:string;actions?:React.ReactNode}){return <div className="page-head"><div><div className="section-kicker">MIRAI / FOUR-COMPANY FOCUS</div><h1>{title}</h1><p>{sub}</p></div>{actions&&<div className="head-actions">{actions}</div>}</div>}
function Selector({value,onChange}:{value:string;onChange:(s:string)=>void}){const [opts,setOpts]=useState<Instrument[]>([]);useEffect(()=>{api.get('/market/instruments').then(r=>setOpts(r.data)).catch(()=>{})},[]);return <label className="select-wrap"><select value={value} onChange={e=>onChange(e.target.value)}>{(opts.length?opts:[{symbol:'RELIANCE',name:'Reliance Industries Ltd.',exchange:'NSE',kind:'equity'}]).map(x=><option key={x.symbol} value={x.symbol}>{x.name}</option>)}</select><ChevronDown size={14}/></label>}
function Source({o}:{o:any}){return <div className="source-line"><span className={o?.simulated?'dot amber-dot':'dot green-dot'}/>{o?.source||'Connecting to market data'}{o?.timestamp&&<span>· Updated {new Date(o.timestamp).toLocaleString()}</span>}</div>}
function ChartPanel({data,title='Price & trend'}:{data:any[];title?:string}){return <section className="panel chart-panel"><div className="panel-head"><div><h3>{title}</h3><span className="muted">Daily observations · local exchange time</span></div><div className="legend"><i/> Close <i className="sand"/> SMA 20</div></div>{data.length?<PriceChart data={data}/>:<div className="empty-chart">Price history appears when the API is available.</div>}</section>}
export function Dashboard(){const m=useMarket();const [portfolio,setPortfolio]=useState<any>(null);useEffect(()=>{api.get('/portfolio').then(r=>setPortfolio(r.data)).catch(()=>{})},[]);return <div className="page"><Head title="Market dashboard" sub="A measured view of price, trend and portfolio risk." actions={<><Selector value={m.symbol} onChange={m.setSymbol}/><button className="icon-button" onClick={m.refresh} title="Refresh"><RefreshCw size={16} className={m.busy?'spin':''}/></button></>}/>{m.error&&<div className="notice error"><AlertTriangle size={16}/>{m.error}</div>}<Source o={m.overview}/><div className="panel" style={{background:'#122c20',borderColor:'#1f6b4a',display:'flex',justifyContent:'space-between',alignItems:'center',padding:'12px 18px',margin:'12px 0 16px'}}><div><span className="eyebrow" style={{color:'#8bd4a6'}}>FOUR-COMPANY AI PREDICTION ENGINE ACTIVE</span><p style={{margin:'2px 0 0',fontSize:'12px',color:'#d2ded4'}}>Direct deterministic forecasts & Ollama insights for MRF, TCS, Jio Platforms & Reliance.</p></div><a href="/predictions" className="primary-button" style={{textDecoration:'none'}}>Open 4-Company Predictions <ArrowUpRight size={14}/></a></div><div className="metric-grid"><Metric label={m.overview?.instrument||'RELIANCE'} value={fmt(m.overview?.price)} change={m.overview?.change!=null?pct(m.overview.change)+' today':''} tone={m.overview?.change>=0?'positive':'negative'}/><Metric label="MARKET REGIME" value={m.overview?.regime?.regime||'—'} change={m.overview?.regime?.confidence?`${Math.round(m.overview.regime.confidence*100)}% confidence`:''}/><Metric label="ANNUAL VOLATILITY" value={pct(m.overview?.volatility)}/><Metric label="RSI · 14" value={fmt(m.overview?.rsi,1)}/><Metric label="ADX · 14" value={fmt(m.overview?.adx,1)}/><Metric label="ACTIVE SIGNAL · MA CROSS" value={m.overview?.active_signal?.signal||'—'} change={m.overview?.active_signal?.position||'Calculating'}/><Metric label="PORTFOLIO RETURN" value={portfolio?.return_pct==null?"—":pct(portfolio.return_pct)} change={portfolio?.total_value!=null?`₹${fmt(portfolio.total_value)}`:"Add holdings to calculate"} tone={portfolio?.return_pct>=0?"positive":"negative"}/><Metric label="SHARPE RATIO" value={fmt(m.overview?.risk?.sharpe)}/></div><div className="dashboard-grid"><div className="main-column"><ChartPanel data={m.hist}/><div className="panel regime-panel"><div className="panel-head"><div><h3>Regime assessment</h3><span className="muted">Rule-based classification</span></div><span className="badge">{m.overview?.regime?.regime||'Awaiting data'}</span></div><p>{m.overview?.regime?.explanation||'Classification requires sufficient market history.'}</p><div className="regime-stats">{Object.entries(m.overview?.regime?.supporting_indicators||{}).map(([k,v])=><div key={k}><span>{k.replaceAll('_',' ')}</span><b>{typeof v==='number'?fmt(v):'—'}</b></div>)}</div></div></div><div className="side-column"><div className="panel"><div className="panel-head"><div><h3>Risk summary</h3><span className="muted">Historical estimates</span></div><AlertTriangle size={16} className="icon-muted"/></div><div className="risk-row"><span>Max drawdown</span><b className="negative">{pct(m.overview?.risk?.max_drawdown)}</b></div><div className="risk-row"><span>Daily VaR · 95%</span><b>{pct(m.overview?.risk?.var_95)}</b></div><div className="risk-row"><span>CVaR · 95%</span><b className="negative">{pct(m.overview?.risk?.cvar_95)}</b></div><div className="risk-row"><span>CAGR</span><b>{pct(m.overview?.risk?.cagr)}</b></div></div><div className="panel"><div className="panel-head"><div><h3>Research note</h3><span className="muted">Data integrity</span></div></div><p className="note-text">{m.overview?.simulated?'Sample data is shown because the market data provider is unavailable. It is deterministic and is not live market information.':'Prices are historical and may be delayed. MIRAI is a research tool; signals are not trade instructions.'}</p><a className="text-link" href="/markets">Open market intelligence <ArrowUpRight size={14}/></a></div></div></div><footer>Research and decision support only · No brokerage connection · Past performance does not indicate future results</footer></div>}
export function Markets(){const [period,setPeriod]=useState('1y');const m=useMarket(period);return <div className="page"><Head title="Market intelligence" sub="Historical price action with calculated technical indicators." actions={<><Selector value={m.symbol} onChange={m.setSymbol}/><select className="period-select" value={period} onChange={e=>setPeriod(e.target.value)}><option value="1y">1 year</option><option value="2y">2 years</option><option value="5y">5 years</option></select><button className="icon-button" onClick={m.refresh}><RefreshCw size={16}/></button></>}/>{m.error&&<div className="notice error">{m.error}</div>}<Source o={m.overview}/><div className="metric-grid four"><Metric label="LAST PRICE" value={fmt(m.overview?.price)}/><Metric label="PERIOD CHANGE" value={pct(m.overview?.change)} tone={m.overview?.change>=0?'positive':'negative'}/><Metric label="REALIZED VOLATILITY" value={pct(m.overview?.volatility)}/><Metric label="TREND STATE" value={m.overview?.regime?.regime}/></div><ChartPanel data={m.hist}/><div className="panel"><div className="panel-head"><div><h3>Indicator monitor</h3><span className="muted">Values calculated from adjusted historical close and OHLC data</span></div></div><IndicatorTable data={m.hist}/></div><footer>Market data source and freshness are shown above. Sample series are explicitly marked simulated.</footer></div>}
function IndicatorTable({data}:{data:any[]}){const d=data.filter(x=>x.rsi!=null).at(-1);return <div className="table-wrap"><table><thead><tr><th>Indicator</th><th>Current</th><th>Interpretation</th><th>Method</th></tr></thead><tbody>{[["RSI (14)",fmt(d?.rsi,1),d?.rsi>70?'Overbought zone':d?.rsi<30?'Oversold zone':'Neutral','Wilder smoothing'],["MACD",fmt(d?.macd,2),d?.macd>d?.macd_signal?'Above signal':'Below signal','12 / 26 / 9 EMA'],["SMA (20)",fmt(d?.sma_20),d?.close>d?.sma_20?'Price above average':'Price below average','20 sessions'],["EMA (20)",fmt(d?.ema_20),'Trend reference','20 sessions'],["ADX (14)",fmt(d?.adx,1),d?.adx>25?'Strong directional trend':'Weak trend','Wilder smoothing'],["Annualized volatility",pct(d?.volatility),'20-session realized','252-session annualization']].map(row=><tr key={row[0]}><td>{row[0]}</td><td className="table-value">{row[1]}</td><td>{row[2]}</td><td className="muted">{row[3]}</td></tr>)}</tbody></table></div>}
export function Regimes(){const m=useMarket();return <div className="page"><Head title="Market regimes" sub="Explainable classifications from trend strength, slope and realized volatility." actions={<Selector value={m.symbol} onChange={m.setSymbol}/>}/><Source o={m.overview}/><div className="panel regime-feature"><div className="section-kicker">CURRENT CLASSIFICATION</div><div className="regime-title">{m.overview?.regime?.regime||'Insufficient data'}<span className="badge">{Math.round((m.overview?.regime?.confidence||0)*100)}% confidence</span></div><p>{m.overview?.regime?.explanation||'Connect to market data to calculate the regime.'}</p><div className="regime-stats">{Object.entries(m.overview?.regime?.supporting_indicators||{}).map(([k,v])=><div key={k}><span>{k.replaceAll('_',' ')}</span><b>{typeof v==='number'?fmt(v):'—'}</b></div>)}</div></div><ChartPanel data={m.hist} title="Price context"/><div className="panel"><h3>Classification rules</h3><div className="rule-grid"><div><b>Bullish / bearish trend</b><p>ADX ≥ 22 and 20-session SMA slope exceeds ±1.5%.</p></div><div><b>High / low volatility</b><p>Annualized 20-session realized volatility above 32% or below 10%.</p></div><div><b>Sideways</b><p>Default when trend strength and slope do not meet the trending thresholds.</p></div></div></div></div>}
export function Strategies(){const m=useMarket();const [rows,setRows]=useState<any[]>([]);const [sort,setSort]=useState('sharpe');const [err,setErr]=useState('');useEffect(()=>{api.get('/strategies',{params:{symbol:m.symbol}}).then(r=>setRows(r.data.data)).catch(()=>setErr('Strategies unavailable; API connection required.'))},[m.symbol]);const sorted=[...rows].sort((a,b)=>(b.metrics?.[sort]??-999)-(a.metrics?.[sort]??-999));return <div className="page"><Head title="Strategy discovery" sub="Compare historical rule-based strategy results across the selected instrument." actions={<Selector value={m.symbol} onChange={m.setSymbol}/>}/><Source o={{source:rows.length?'Historical simulation':undefined,simulated:m.overview?.simulated}}/>{err&&<div className="notice error">{err}</div>}<div className="panel"><div className="panel-head"><div><h3>Strategy screen</h3><span className="muted">Metrics are calculated from chronological historical closes and include transaction costs.</span></div><select className="period-select" value={sort} onChange={e=>setSort(e.target.value)}><option value="sharpe">Sort by Sharpe</option><option value="cagr">Sort by CAGR</option><option value="max_drawdown">Sort by drawdown</option></select></div><div className="table-wrap"><table><thead><tr><th>Strategy</th><th>Risk</th><th>CAGR</th><th>Sharpe</th><th>Sortino</th><th>Max DD</th><th>Win rate</th><th>Trades</th></tr></thead><tbody>{sorted.map(x=><tr key={x.id}><td><b>{x.name}</b><div className="muted strategy-desc">{x.description}</div></td><td><span className="badge">{x.risk}</span></td><td>{pct(x.metrics.cagr)}</td><td>{fmt(x.metrics.sharpe)}</td><td>{fmt(x.metrics.sortino)}</td><td className="negative">{pct(x.metrics.max_drawdown)}</td><td>{pct(x.metrics.win_rate)}</td><td>{x.metrics.total_trades}</td></tr>)}</tbody></table></div></div><footer>Historical backtests are sensitive to sample period, costs and assumptions. No future returns are implied.</footer></div>}
export function Backtest(){const m=useMarket();const [strategy,setStrategy]=useState('ma_crossover'),[capital,setCapital]=useState(100000),[cost,setCost]=useState(5),[result,setResult]=useState<any>(null),[busy,setBusy]=useState(false),[err,setErr]=useState('');async function run(){setBusy(true);setErr('');try{const r=await api.post('/backtests/run',{symbol:m.symbol,strategy,initial_capital:Number(capital),transaction_cost_bps:Number(cost),period:'5y'});setResult(r.data)}catch{setErr('Backtest could not run. Check API and selected strategy.')}finally{setBusy(false)}}return <div className="page"><Head title="Backtesting lab" sub="Chronological simulation with next-session execution and configurable transaction costs." actions={<Selector value={m.symbol} onChange={m.setSymbol}/>}/><div className="panel form-panel"><div><label>Strategy<select value={strategy} onChange={e=>setStrategy(e.target.value)}>{['ma_crossover','dual_ma','rsi_mean_reversion','momentum_breakout','bollinger_mean_reversion','macd_trend'].map(x=><option value={x} key={x}>{x.replaceAll('_',' ')}</option>)}</select></label><label>Initial capital<input type="number" value={capital} onChange={e=>setCapital(+e.target.value)}/></label><label>Transaction cost (bps)<input type="number" value={cost} onChange={e=>setCost(+e.target.value)}/></label><button className="primary-button" disabled={busy} onClick={run}><Play size={15}/>{busy?'Running':'Run backtest'}</button></div></div>{err&&<div className="notice error">{err}</div>}{result&&<><Source o={result}/><div className="metric-grid four"><Metric label="TOTAL RETURN" value={pct(result.results.total_return)} tone={result.results.total_return>=0?'positive':'negative'}/><Metric label="CAGR" value={pct(result.results.cagr)}/><Metric label="SHARPE" value={fmt(result.results.sharpe)}/><Metric label="MAX DRAWDOWN" value={pct(result.results.max_drawdown)} tone="negative"/><Metric label="SORTINO" value={fmt(result.results.sortino)}/><Metric label="WIN RATE" value={pct(result.results.win_rate)}/><Metric label="PROFIT FACTOR" value={fmt(result.results.profit_factor)}/><Metric label="CLOSED TRADES" value={result.results.total_trades}/></div><section className="panel chart-panel"><div className="panel-head"><div><h3>Equity curve</h3><span className="muted">Backtest #{result.id}</span></div></div><PriceChart data={result.results.dates.map((date:string,i:number)=>({date,close:result.results.equity[i]}))}/></section><div className="panel"><div className="panel-head"><h3>Closed trades</h3><span className="muted">{result.results.trades.length} completed positions</span></div><TradeTable trades={result.results.trades}/></div><div className="notice">{result.disclaimer}</div></>}</div>}
function TradeTable({trades}:{trades:any[]}){return <div className="table-wrap"><table><thead><tr><th>Entry</th><th>Exit</th><th>Entry price</th><th>Exit price</th><th>Return</th></tr></thead><tbody>{trades.slice(-20).reverse().map((t,i)=><tr key={i}><td>{String(t.entry_date).slice(0,10)}</td><td>{String(t.exit_date).slice(0,10)}</td><td>{fmt(t.entry_price)}</td><td>{fmt(t.exit_price)}</td><td className={t.return>=0?'positive':'negative'}>{pct(t.return)}</td></tr>)}</tbody></table></div>}
export function Portfolio(){const [rows,setRows]=useState([{symbol:'RELIANCE',quantity:10,average_price:1330}]),[result,setResult]=useState<any>(null),[error,setError]=useState('');useEffect(()=>{api.get('/portfolio').then(r=>{if(r.data.holdings?.length)setRows(r.data.holdings)}).catch(()=>{})},[]);const update=(i:number,key:string,v:any)=>setRows(rows.map((r,j)=>j===i?{...r,[key]:v}:r));async function save(){try{await api.post('/portfolio',{holdings:rows.map(x=>({...x,quantity:Number(x.quantity),average_price:Number(x.average_price)}))});setResult((await api.get('/portfolio/risk')).data);setError('')}catch(e:any){setError(e?.response?.data?.detail||'Could not save holdings.')}}return <div className="page"><Head title="Portfolio & risk" sub="Enter holdings to calculate allocation and historical risk estimates." actions={<button className="primary-button" onClick={save}>Calculate risk</button>}/>{error&&<div className="notice error">{error}</div>}<div className="panel"><div className="panel-head"><div><h3>Holdings</h3><span className="muted">Quantities and average purchase prices</span></div><button className="quiet-button" onClick={()=>setRows([...rows,{symbol:'TCS',quantity:1,average_price:2400}])}><Plus size={15}/> Add holding</button></div><div className="holding-list">{rows.map((r,i)=><div className="holding-row" key={i}><select value={r.symbol} onChange={e=>update(i,'symbol',e.target.value)}>{['RELIANCE','TCS','MRF','JIO'].map(s=><option key={s}>{s}</option>)}</select><input aria-label="Quantity" type="number" value={r.quantity} onChange={e=>update(i,'quantity',e.target.value)}/><input aria-label="Average price" type="number" value={r.average_price} onChange={e=>update(i,'average_price',e.target.value)}/><button className="icon-button" onClick={()=>setRows(rows.filter((_,j)=>j!==i))}><Trash2 size={15}/></button></div>)}</div><div className="holding-labels"><span>Instrument</span><span>Quantity</span><span>Average price (₹)</span></div></div>{result?.available&&<><div className="metric-grid four"><Metric label="PORTFOLIO VALUE" value={'₹'+fmt(result.portfolio_value)}/><Metric label="INVESTED" value={'₹'+fmt(result.invested_value)}/><Metric label="RETURN" value={pct(result.return)} tone={result.return>=0?'positive':'negative'}/><Metric label="BETA" value={fmt(result.beta)}/><Metric label="VOLATILITY" value={pct(result.risk.annualized_volatility)}/><Metric label="SHARPE" value={fmt(result.risk.sharpe)}/><Metric label="95% VaR · DAILY" value={pct(result.risk.var_95)}/><Metric label="MAX DRAWDOWN" value={pct(result.risk.max_drawdown)} tone="negative"/></div><div className="panel"><h3>Asset allocation</h3>{result.allocation.map((a:any)=><div className="alloc-row" key={a.symbol}><span>{a.symbol}</span><div className="alloc-track"><i style={{width:`${a.weight*100}%`}}/></div><b>{pct(a.weight)}</b></div>)}</div></>}{result&&!result.available&&<div className="notice">{result.reason}</div>}</div>}
type Message={role:'user'|'assistant';content:string;provider?:string;verdict?:string};
const prompts = [
  'Should I buy this stock?',
  'Will I make a profit or loss?',
  'What is the expected price after five sessions?',
  'Is it better to buy, hold or wait?',
  'Explain this company\'s risk.',
];

function FormattedAssistantMessage({ text }: { text: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let currentBullets: string[] = [];
  let keyIdx = 0;

  const flushBullets = () => {
    if (currentBullets.length > 0) {
      elements.push(
        <ul key={`ul-${keyIdx++}`} style={{ margin: '8px 0 14px 20px', padding: 0 }}>
          {currentBullets.map((b, i) => {
            const boldMatch = b.match(/^\*\*(.*?)\*\*(.*)$/);
            return (
              <li key={i} style={{ margin: '4px 0', fontSize: '12px', lineHeight: 1.6, color: '#d1d8d0' }}>
                {boldMatch ? (
                  <>
                    <strong style={{ color: '#f2f5f2', fontWeight: 600 }}>{boldMatch[1]}</strong>
                    {boldMatch[2]}
                  </>
                ) : (
                  b
                )}
              </li>
            );
          })}
        </ul>
      );
      currentBullets = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    if (line.startsWith('### ')) {
      flushBullets();
      const title = line.replace('### ', '').trim();
      elements.push(
        <div
          key={`h-${keyIdx++}`}
          style={{
            fontFamily: "'DM Mono', monospace",
            fontSize: '11px',
            letterSpacing: '1px',
            color: '#8bd4a6',
            textTransform: 'uppercase',
            marginTop: '16px',
            marginBottom: '6px',
            borderBottom: '1px solid #1e3629',
            paddingBottom: '3px',
            fontWeight: 600,
          }}
        >
          {title}
        </div>
      );
    } else if (
      line.startsWith('YES —') ||
      line.startsWith('NO —') ||
      line.startsWith('WAIT —') ||
      line.startsWith('WAIT') ||
      line === 'INSUFFICIENT DATA'
    ) {
      flushBullets();
      const isYes = line.startsWith('YES');
      const isNo = line.startsWith('NO');
      const isWait = line.startsWith('WAIT');
      const bg = isYes ? '#12372a' : isNo ? '#38161c' : isWait ? '#332717' : '#1e2923';
      const color = isYes ? '#8bd4a6' : isNo ? '#e58b98' : isWait ? '#e6be75' : '#a3b899';
      const border = isYes ? '#1f6b4a' : isNo ? '#852232' : isWait ? '#85642a' : '#384e40';

      elements.push(
        <div
          key={`verdict-${keyIdx++}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: bg,
            color: color,
            border: `1.5px solid ${border}`,
            borderRadius: '4px',
            padding: '8px 16px',
            fontSize: '15px',
            fontWeight: 700,
            letterSpacing: '0.5px',
            margin: '4px 0 12px 0',
            boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
          }}
        >
          <span
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: color,
            }}
          />
          {line}
        </div>
      );
    } else if (line.startsWith('- ')) {
      currentBullets.push(line.replace(/^- /, ''));
    } else {
      flushBullets();
      const parts = line.split(/(\*\*.*?\*\*)/g);
      elements.push(
        <p key={`p-${keyIdx++}`} style={{ margin: '6px 0 10px 0', fontSize: '12px', lineHeight: 1.65, color: '#d1d8d0' }}>
          {parts.map((p, idx) => {
            if (p.startsWith('**') && p.endsWith('**')) {
              return <strong key={idx} style={{ color: '#f2f5f2', fontWeight: 600 }}>{p.slice(2, -2)}</strong>;
            }
            return p;
          })}
        </p>
      );
    }
  }
  flushBullets();

  return <div className="formatted-analyst-message">{elements}</div>;
}

export function Assistant(){const m=useMarket();const [messages,setMessages]=useState<Message[]>([]),[input,setInput]=useState(''),[busy,setBusy]=useState(false),[err,setErr]=useState('');async function send(text=input){if(!text.trim()||busy)return;const q=text.trim();setMessages(prev=>[...prev,{role:'user',content:q}]);setInput('');setBusy(true);setErr('');try{const r=await api.post('/ai/chat',{question:q,symbol:m.symbol},{timeout:120000});setMessages(x=>[...x,{role:'assistant',content:r.data.answer,provider:r.data.provider,verdict:r.data.verdict}])}catch{setErr('Assistant is unavailable while the API is offline.')}finally{setBusy(false)}}return <div className="page assistant-page"><Head title="MIRAI Intelligence" sub="Your quantitative stock research analyst with clear YES/NO verdicts." actions={<Selector value={m.symbol} onChange={m.setSymbol}/>}/><div className="chat-panel">{messages.length===0?<div className="chat-welcome"><div className="assistant-mark">M</div><h2>Institutional Research, Simplified.</h2><p>Ask whether to buy, hold, or sell. MIRAI provides direct verdicts and plain-English explanations grounded in verified quantitative data.</p><div className="prompt-grid" style={{gridTemplateColumns:'repeat(auto-fit, minmax(230px, 1fr))'}}>{prompts.map(p=><button key={p} onClick={()=>send(p)}><span>{p}</span><ArrowUpRight size={14}/></button>)}</div></div>:<div className="messages">{messages.map((x,i)=><div className={'message '+x.role} key={i}><div className="message-label">{x.role==='assistant'?'MIRAI FINANCIAL RESEARCH ANALYST':'YOU'} {x.provider==='ollama'&&<span className="badge" style={{color:'#8bd4a6',borderColor:'#1f6b4a',background:'#12372a'}}>OLLAMA ACTIVE</span>}{x.provider==='mirai_analyst'&&<span className="badge" style={{color:'#8bd4a6',borderColor:'#1f6b4a',background:'#12372a'}}>DETERMINISTIC ANALYST</span>}</div><div className="message-text">{x.role==='assistant'?<FormattedAssistantMessage text={x.content}/>:x.content}</div></div>)}{busy&&<div className="message assistant"><div className="message-label">MIRAI ANALYST</div><div className="typing"><i/><i/><i/></div></div>}</div>}{messages.length>0&&<div className="chat-suggestions-bar">{prompts.map(p=><button key={p} className="chat-suggestion-chip" onClick={()=>send(p)}>{p}</button>)}</div>}<div className="chat-input"><input value={input} placeholder={`Ask about ${m.symbol} or any of the 4 companies…`} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()}/><button className="primary-button" onClick={()=>send()} disabled={busy}><Send size={15}/></button></div>{err&&<div className="chat-error">{err}</div>}</div><footer>Assistant responses provide research analysis and decision support grounded in historical datasets and calibrated quantitative models. Not automated trade execution.</footer></div>}
export function Library(){return <Strategies/>}export function Settings(){return <div className="page"><Head title="Settings" sub="Environment and data provider configuration."/><div className="panel settings-panel"><h3>Market data</h3><p>Provider: Yahoo Finance historical data via yfinance. Provider outages trigger a clearly labeled deterministic sample series for local exploration.</p><h3>AI research assistant</h3><p>Set <code>OPENAI_API_KEY</code> in the backend environment to enable model responses. With no key, MIRAI returns a transparent context-based fallback.</p><h3>Research controls</h3><p>Historical data may be delayed. Backtests include transaction costs and next-session position execution. MIRAI does not execute trades.</p></div></div>}
