import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { RefreshCw, Shield, AlertTriangle, TrendingUp, TrendingDown, Minus, Cpu } from 'lucide-react';

export interface CompanyPrediction {
  company: string;
  symbol: string;
  sector: string;
  exchange: string;
  prediction_horizon_sessions: number;
  current_price: number;
  forecast_price: number;
  expected_return_pct: number;
  estimated_transaction_cost_pct: number;
  expected_net_return_pct: number;
  verdict: 'BUY' | 'SELL' | 'HOLD';
  recommendation_type: string;
  risk_level: 'Low' | 'Moderate' | 'High';
  confidence: number;
  strategy_rationale: string;
  indicators: {
    close: number;
    ema20: number;
    ema50: number | null;
    rsi: number;
    roc_10d: number;
    atr_14d: number;
    rel_vol: number;
    obv: number;
    momentum_10d: number;
    observations: number;
  };
  validation_metrics?: {
    train_sessions: number;
    test_sessions: number;
    mae: number;
    baseline_mae: number;
    rmse: number;
    directional_accuracy_pct: number;
    baseline_comparison: string;
  };
  dataset_info: {
    start_date: string;
    end_date: string;
    total_sessions: number;
  };
  ollama_explanation?: string;
}

export interface PredictionPayload {
  title: string;
  benchmark_index: string;
  prediction_horizon_sessions: number;
  estimated_round_trip_cost_pct: number;
  summary: {
    total_companies: number;
    buy_count: number;
    sell_count: number;
    hold_count: number;
    top_opportunity: {
      company: string;
      verdict: string;
      expected_net_return_pct: number;
    } | null;
  };
  companies: CompanyPrediction[];
  generated_at: string;
}

const fmt = (v: any, d = 2) => (v == null ? '—' : Number(v).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (v: any) => (v == null ? '—' : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`);

export function PredictionsPage() {
  const [data, setData] = useState<PredictionPayload | null>(null);
  const [horizon, setHorizon] = useState<number>(5);
  const [busy, setBusy] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  const loadData = async (h = horizon) => {
    setBusy(true);
    setError('');
    try {
      const res = await api.get('/predictions/companies', { params: { horizon: h, include_ollama: true } });
      setData(res.data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load four-company predictions from the backend API.');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void loadData(horizon);
  }, [horizon]);

  return (
    <div className="page predictions-page">
      <div className="page-head">
        <div>
          <div className="section-kicker">MIRAI / FOUR-COMPANY QUANT ENGINE</div>
          <h1>AI Prediction & P&L Decision Engine</h1>
          <p>
            Deterministic quantitative forecasts, cost-adjusted net return calculations, and Ollama intelligence for MRF, TCS, Jio Platforms, and Reliance Industries.
          </p>
        </div>
        <div className="head-actions">
          <label className="select-wrap">
            <select
              value={horizon}
              onChange={(e) => {
                const val = Number(e.target.value);
                setHorizon(val);
              }}
            >
              <option value={3}>3 Sessions Horizon</option>
              <option value={5}>5 Sessions Horizon (Standard)</option>
              <option value={10}>10 Sessions Horizon</option>
            </select>
          </label>
          <button className="icon-button" onClick={() => void loadData(horizon)} title="Refresh Predictions" disabled={busy}>
            <RefreshCw size={16} className={busy ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {error && (
        <div className="notice error">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* OVERALL EXECUTIVE SUMMARY BANNER */}
      {data && (
        <div className="panel summary-banner" style={{ background: '#12251e', borderColor: '#1f6b4a' }}>
          <div className="panel-head" style={{ marginBottom: '8px' }}>
            <div>
              <span className="eyebrow" style={{ color: '#8bd4a6' }}>EXECUTIVE QUANTITATIVE PORTFOLIO SUMMARY</span>
              <h3 style={{ fontSize: '16px', marginTop: '4px' }}>Four-Company Strategic Allocation Overview</h3>
            </div>
            <span className="badge" style={{ background: '#1f6b4a', color: '#e8f5e9' }}>
              NIFTY 50 ELIMINATED · INDEPENDENT ANALYSIS
            </span>
          </div>

          <div className="metric-grid four" style={{ margin: '10px 0 0', background: '#0b1f18', borderColor: '#293b30' }}>
            <div className="metric">
              <span className="eyebrow">COMPANIES ANALYZED</span>
              <div className="metric-value">{data.summary.total_companies}</div>
              <span className="metric-note">MRF, TCS, JIO, RELIANCE</span>
            </div>
            <div className="metric">
              <span className="eyebrow">VERDICT CONFLUENCE</span>
              <div className="metric-value">
                <span className="positive">{data.summary.buy_count} BUY</span>
                <small style={{ color: '#c7a46f', marginLeft: '6px' }}>{data.summary.hold_count} HOLD</small>
                {data.summary.sell_count > 0 && <small className="negative" style={{ marginLeft: '6px' }}>{data.summary.sell_count} SELL</small>}
              </div>
              <span className="metric-note">Independent Rule Classification</span>
            </div>
            <div className="metric">
              <span className="eyebrow">TOP NET OPPORTUNITY</span>
              <div className="metric-value positive">
                {data.summary.top_opportunity ? pct(data.summary.top_opportunity.expected_net_return_pct) : '—'}
              </div>
              <span className="metric-note">{data.summary.top_opportunity?.company || 'None'}</span>
            </div>
            <div className="metric">
              <span className="eyebrow">ROUND-TRIP TRANSACTION COST</span>
              <div className="metric-value">{data.estimated_round_trip_cost_pct.toFixed(2)}%</div>
              <span className="metric-note">STT + Brokerage + Turnover + GST</span>
            </div>
          </div>
        </div>
      )}

      {/* FOUR INDIVIDUAL COMPANY PREDICTION CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '20px', marginTop: '16px' }}>
        {data?.companies.map((c) => {
          const isBuy = c.verdict === 'BUY';
          const isSell = c.verdict === 'SELL';
          const badgeBg = isBuy ? '#12372a' : isSell ? '#38161c' : '#332717';
          const badgeBorder = isBuy ? '#1f6b4a' : isSell ? '#852232' : '#85642a';
          const badgeColor = isBuy ? '#8bd4a6' : isSell ? '#e58b98' : '#e6be75';

          return (
            <div
              key={c.symbol}
              className="panel company-pred-card"
              style={{
                background: '#141e19',
                borderColor: isBuy ? '#234a36' : isSell ? '#4d2028' : '#383b28',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #293b30', paddingBottom: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span className="badge" style={{ background: '#1b2d24', borderColor: '#3a5948', color: '#c2dec9' }}>
                        {c.exchange}: {c.symbol}
                      </span>
                      <span className="muted" style={{ fontSize: '10px' }}>{c.sector}</span>
                    </div>
                    <h2 style={{ margin: '8px 0 2px', fontSize: '20px', fontWeight: 600 }}>{c.company}</h2>
                    <span style={{ fontSize: '10px', color: '#829286' }}>
                      Historical Sample: {c.dataset_info.start_date} to {c.dataset_info.end_date} ({c.dataset_info.total_sessions} sessions)
                    </span>
                  </div>
                  <div
                    style={{
                      background: badgeBg,
                      border: `1.5px solid ${badgeBorder}`,
                      color: badgeColor,
                      padding: '8px 16px',
                      borderRadius: '4px',
                      fontFamily: "'DM Mono', monospace",
                      fontSize: '16px',
                      fontWeight: 700,
                      letterSpacing: '1.5px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    {isBuy ? <TrendingUp size={18} /> : isSell ? <TrendingDown size={18} /> : <Minus size={18} />}
                    {c.verdict}
                  </div>
                </div>

                {/* Primary Price & P&L Block */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', background: '#0d1813', padding: '14px', margin: '14px 0', border: '1px solid #223429' }}>
                  <div>
                    <span className="eyebrow" style={{ fontSize: '8px' }}>CURRENT PRICE</span>
                    <div style={{ fontFamily: "'DM Mono', monospace", fontSize: '18px', fontWeight: 600, marginTop: '4px' }}>
                      ₹{fmt(c.current_price)}
                    </div>
                  </div>
                  <div>
                    <span className="eyebrow" style={{ fontSize: '8px' }}>{c.prediction_horizon_sessions}-DAY FORECAST</span>
                    <div style={{ fontFamily: "'DM Mono', monospace", fontSize: '18px', fontWeight: 600, marginTop: '4px', color: '#dbe8de' }}>
                      ₹{fmt(c.forecast_price)}
                    </div>
                  </div>
                  <div>
                    <span className="eyebrow" style={{ fontSize: '8px' }}>GROSS RETURN</span>
                    <div style={{ fontFamily: "'DM Mono', monospace", fontSize: '16px', marginTop: '4px' }} className={c.expected_return_pct >= 0 ? 'positive' : 'negative'}>
                      {pct(c.expected_return_pct)}
                    </div>
                    <span style={{ fontSize: '8px', color: '#7e8e82' }}>Costs: -{c.estimated_transaction_cost_pct.toFixed(2)}%</span>
                  </div>
                  <div style={{ background: isBuy ? '#122c20' : '#1f1b14', padding: '6px 10px', borderRadius: '2px', borderLeft: `3px solid ${badgeColor}` }}>
                    <span className="eyebrow" style={{ fontSize: '8px', color: badgeColor }}>NET EXPECTED P&L</span>
                    <div style={{ fontFamily: "'DM Mono', monospace", fontSize: '19px', fontWeight: 700, marginTop: '2px' }} className={c.expected_net_return_pct >= 0 ? 'positive' : 'negative'}>
                      {pct(c.expected_net_return_pct)}
                    </div>
                    <span style={{ fontSize: '8px', color: '#97a89b' }}>Post-Commission</span>
                  </div>
                </div>

                {/* Risk & Confidence Bar */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#111b16', padding: '10px 14px', border: '1px solid #203126', marginBottom: '14px', fontSize: '11px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                    <Shield size={14} style={{ color: '#8bd4a6' }} />
                    <span style={{ color: '#a6b3aa' }}>Risk Level:</span>
                    <b style={{ color: c.risk_level === 'Low' ? '#8bd4a6' : c.risk_level === 'Moderate' ? '#e6be75' : '#e58b98' }}>{c.risk_level}</b>
                    <span style={{ color: '#536458' }}>|</span>
                    <span style={{ color: '#a6b3aa' }}>Setup:</span>
                    <span className="badge" style={{ fontSize: '8px', padding: '2px 6px' }}>{c.recommendation_type}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#a6b3aa' }}>Confidence:</span>
                    <div style={{ width: '80px', height: '6px', background: '#25352b', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ width: `${c.confidence * 100}%`, height: '100%', background: '#2c8e5f' }} />
                    </div>
                    <b style={{ fontFamily: "'DM Mono', monospace" }}>{Math.round(c.confidence * 100)}%</b>
                  </div>
                </div>

                {/* Key Technical Indicators Table */}
                <div style={{ marginBottom: '14px' }}>
                  <span className="eyebrow" style={{ display: 'block', marginBottom: '6px' }}>REAL CALCULATED TECHNICAL INDICATORS</span>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>RSI (14)</span>
                      <b style={{ fontFamily: "'DM Mono', monospace", color: c.indicators.rsi > 70 ? '#e58b98' : c.indicators.rsi < 35 ? '#8bd4a6' : '#d2ded4' }}>
                        {c.indicators.rsi}
                      </b>
                    </div>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>EMA (20)</span>
                      <b style={{ fontFamily: "'DM Mono', monospace" }}>₹{fmt(c.indicators.ema20)}</b>
                    </div>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>EMA (50)</span>
                      <b style={{ fontFamily: "'DM Mono', monospace" }}>{c.indicators.ema50 ? `₹${fmt(c.indicators.ema50)}` : 'N/A'}</b>
                    </div>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>ROC (10-Day)</span>
                      <b style={{ fontFamily: "'DM Mono', monospace" }} className={c.indicators.roc_10d >= 0 ? 'positive' : 'negative'}>
                        {pct(c.indicators.roc_10d)}
                      </b>
                    </div>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>ATR (14-Day)</span>
                      <b style={{ fontFamily: "'DM Mono', monospace" }}>₹{fmt(c.indicators.atr_14d)}</b>
                    </div>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>REL VOLUME</span>
                      <b style={{ fontFamily: "'DM Mono', monospace" }}>{c.indicators.rel_vol.toFixed(2)}x</b>
                    </div>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>OBV</span>
                      <b style={{ fontFamily: "'DM Mono', monospace", fontSize: '10px' }}>{fmt(c.indicators.obv, 0)}</b>
                    </div>
                    <div style={{ background: '#0d1813', padding: '8px', border: '1px solid #203126', textAlign: 'center' }}>
                      <span className="muted" style={{ fontSize: '9px', display: 'block' }}>MOMENTUM</span>
                      <b style={{ fontFamily: "'DM Mono', monospace" }} className={c.indicators.momentum_10d >= 0 ? 'positive' : 'negative'}>
                        {fmt(c.indicators.momentum_10d)}
                      </b>
                    </div>
                  </div>
                </div>

                {/* Walk-Forward Validation Strip */}
                {c.validation_metrics && c.validation_metrics.test_sessions > 0 && (
                  <div style={{ background: '#091510', border: '1px solid #1a3324', padding: '10px 14px', borderRadius: '4px', margin: '10px 0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span className="eyebrow" style={{ color: '#8bd4a6' }}>CHRONOLOGICAL WALK-FORWARD VALIDATION (OUT-OF-SAMPLE)</span>
                      <span className="badge" style={{ fontSize: '9px' }}>
                        Train: {c.validation_metrics.train_sessions}d | Test: {c.validation_metrics.test_sessions}d
                      </span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', fontSize: '11px', textAlign: 'center' }}>
                      <div>
                        <span className="muted" style={{ fontSize: '9px', display: 'block' }}>MODEL MAE</span>
                        <b>₹{fmt(c.validation_metrics.mae)}</b>
                      </div>
                      <div>
                        <span className="muted" style={{ fontSize: '9px', display: 'block' }}>BASELINE MAE</span>
                        <b>₹{fmt(c.validation_metrics.baseline_mae)}</b>
                      </div>
                      <div>
                        <span className="muted" style={{ fontSize: '9px', display: 'block' }}>RMSE</span>
                        <b>₹{fmt(c.validation_metrics.rmse)}</b>
                      </div>
                      <div>
                        <span className="muted" style={{ fontSize: '9px', display: 'block' }}>DIRECTIONAL ACCURACY</span>
                        <b style={{ color: c.validation_metrics.directional_accuracy_pct >= 50 ? '#8bd4a6' : '#e6be75' }}>
                          {c.validation_metrics.directional_accuracy_pct}%
                        </b>
                      </div>
                    </div>
                  </div>
                )}

                {/* Ollama AI Institutional Explanation */}
                <div style={{ background: '#0d1612', border: '1px solid #1e3629', padding: '14px', borderRadius: '3px', marginTop: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <Cpu size={15} style={{ color: '#8bd4a6' }} />
                    <span style={{ fontSize: '11px', fontWeight: 600, color: '#c4ddc8' }}>Ollama Quantitative Intelligence</span>
                    <span className="badge" style={{ fontSize: '8px', padding: '1px 5px', background: '#12372a', borderColor: '#1f6b4a' }}>
                      qwen2.5-coder:7b
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', lineHeight: '1.7', color: '#b9c7bc', whiteSpace: 'pre-line' }}>
                    {c.ollama_explanation || 'Generating explanation from quantitative indicators…'}
                  </div>
                </div>
              </div>

              {/* Strategy Note Footer */}
              <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid #223429', fontSize: '10px', color: '#7e8e82' }}>
                <b style={{ color: '#a6b3aa' }}>Execution Discipline: </b>
                {c.strategy_rationale}
              </div>
            </div>
          );
        })}
      </div>

      {/* COMPARATIVE FOUR-COMPANY AUDIT TABLE */}
      {data && (
        <div className="panel" style={{ marginTop: '24px' }}>
          <div className="panel-head">
            <div>
              <h3>Four-Company Comparative Decision Matrix</h3>
              <span className="muted">Direct cross-asset evaluation without index distortion</span>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Exchange Symbol</th>
                  <th>Current Price</th>
                  <th>Forecast (5D)</th>
                  <th>Gross Return</th>
                  <th>Net Expected Return</th>
                  <th>Verdict</th>
                  <th>Confidence</th>
                  <th>Risk Profile</th>
                  <th>RSI (14)</th>
                  <th>EMA 20</th>
                  <th>Relative Vol</th>
                </tr>
              </thead>
              <tbody>
                {data.companies.map((c) => (
                  <tr key={c.symbol}>
                    <td><b>{c.company}</b></td>
                    <td><span className="badge">{c.symbol}</span></td>
                    <td className="table-value">₹{fmt(c.current_price)}</td>
                    <td className="table-value">₹{fmt(c.forecast_price)}</td>
                    <td className={c.expected_return_pct >= 0 ? 'positive' : 'negative'}>{pct(c.expected_return_pct)}</td>
                    <td className={c.expected_net_return_pct >= 0 ? 'positive' : 'negative'} style={{ fontWeight: 700 }}>
                      {pct(c.expected_net_return_pct)}
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: c.verdict === 'BUY' ? '#12372a' : c.verdict === 'SELL' ? '#38161c' : '#332717',
                          color: c.verdict === 'BUY' ? '#8bd4a6' : c.verdict === 'SELL' ? '#e58b98' : '#e6be75',
                          borderColor: c.verdict === 'BUY' ? '#1f6b4a' : c.verdict === 'SELL' ? '#852232' : '#85642a',
                        }}
                      >
                        {c.verdict}
                      </span>
                    </td>
                    <td className="table-value">{Math.round(c.confidence * 100)}%</td>
                    <td>{c.risk_level}</td>
                    <td className="table-value">{c.indicators.rsi}</td>
                    <td className="table-value">₹{fmt(c.indicators.ema20)}</td>
                    <td className="table-value">{c.indicators.rel_vol.toFixed(2)}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <footer>
        MIRAI Quantitative Platform · Decisions are calculated deterministically from verified company datasets · Incorporates estimated round-trip transaction costs · Past performance does not guarantee future results.
      </footer>
    </div>
  );
}

export default PredictionsPage;
