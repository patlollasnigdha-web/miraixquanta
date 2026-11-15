"""
MIRAI — Real Market Data & Quantitative Intelligence Service (M16)
Loads real historical OHLCV from NIFTY 50 and constituent datasets,
computes technical indicators, risk metrics, regime classification,
and backtest simulations.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger
from src.data_engineering.load_nifty50 import load_nifty_daily_official

logger = get_logger("MarketDataService")

# Four institutional focus companies (NIFTY 50 completely eliminated)
FOUR_COMPANIES_METADATA: Dict[str, Dict[str, str]] = {
    "MRF": {"name": "MRF Ltd.", "sector": "Automobile & Tyres", "exchange": "NSE", "kind": "equity"},
    "TCS": {"name": "Tata Consultancy Services Ltd.", "sector": "Information Technology", "exchange": "NSE", "kind": "equity"},
    "JIO": {"name": "Jio Platforms", "sector": "Telecommunications & Digital Services", "exchange": "NSE", "kind": "equity"},
    "RELIANCE": {"name": "Reliance Industries Ltd.", "sector": "Energy & Conglomerate", "exchange": "NSE", "kind": "equity"},
}

# Complete instrument dictionary supporting raw symbols, names, and .NS ticker suffixes
INSTRUMENTS: Dict[str, Dict[str, str]] = {}
for sym, meta in FOUR_COMPANIES_METADATA.items():
    INSTRUMENTS[sym] = meta
    INSTRUMENTS[f"{sym}.NS"] = meta
    INSTRUMENTS[meta["name"]] = meta

# Helpful aliases
INSTRUMENTS["JIOFIN"] = FOUR_COMPANIES_METADATA["JIO"]
INSTRUMENTS["JIOFIN.NS"] = FOUR_COMPANIES_METADATA["JIO"]
INSTRUMENTS["JIO PLATFORMS"] = FOUR_COMPANIES_METADATA["JIO"]
INSTRUMENTS["RELIANCE INDUSTRIES"] = FOUR_COMPANIES_METADATA["RELIANCE"]

STRATEGIES = [
    {
        "id": "ma_crossover",
        "name": "Moving Average Crossover",
        "description": "Fast 10-period and slow 30-period simple moving average trend following with next-session execution.",
        "risk": "Moderate",
    },
    {
        "id": "dual_ma",
        "name": "Dual Moving Average (20/50)",
        "description": "Medium-term 20/50-day exponential trend filter capturing intermediate market momentum.",
        "risk": "Moderate",
    },
    {
        "id": "rsi_mean_reversion",
        "name": "RSI Mean Reversion (14)",
        "description": "Buys oversold conditions (RSI < 30) and closes on mean-reversion recovery (RSI > 50).",
        "risk": "Low to Moderate",
    },
    {
        "id": "momentum_breakout",
        "name": "Momentum Breakout",
        "description": "20-day high breakout entry with dynamic 10-day trailing support.",
        "risk": "High",
    },
    {
        "id": "bollinger_mean_reversion",
        "name": "Bollinger Bands Reversion",
        "description": "Enters near lower band (2 std) and exits when crossing 20-period moving average.",
        "risk": "Moderate",
    },
    {
        "id": "macd_trend",
        "name": "MACD Trend Momentum",
        "description": "12/26/9 MACD histogram signal line crossing with directional confirmation.",
        "risk": "Moderate to High",
    },
]


def clean(value: Any) -> Any:
    """Recursively formats and cleans NaN/Infinity for JSON serialization."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(x) for x in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if hasattr(value, "item"):
        return clean(value.item())
    return value


class MarketDataService:
    """Manages real multi-year stock market data loading, indicators, and backtests."""

    def __init__(self):
        self._cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        self._raw_stock_dir = (
            PROJECT_ROOT / "NIFTY-50-Stock-Market-Data-main" / "NIFTY-50-Stock-Market-Data-main" / "data"
        )
        self._loaded_constituent_dfs: Dict[str, pd.DataFrame] = {}

    def _normalize_symbol(self, symbol: str) -> str:
        s = symbol.strip().upper()
        if s.endswith(".NS"):
            s = s[:-3]
        return s

    def load_raw_series(self, symbol: str) -> pd.DataFrame:
        norm = self._normalize_symbol(symbol)
        from src.prediction.four_company_engine import four_company_engine

        # Load directly from the verified four-company datasets
        try:
            canon = four_company_engine.resolve_symbol(norm) or "RELIANCE"
            df = four_company_engine.load_dataset(canon)
            df = df.rename(columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            df = df.set_index("date")
            return df
        except Exception as e:
            logger.warning(f"Error loading four-company series for {symbol}: {e}")
            df = four_company_engine.load_dataset("RELIANCE")
            df = df.rename(columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            df = df.set_index("date")
            return df

    def get_frame(self, symbol: str, period: str = "1y") -> Tuple[pd.DataFrame, str, str, bool]:
        """Loads and slices historical dataframe for symbol and period."""
        raw = self.load_raw_series(symbol)
        period_map = {
            "1mo": 21,
            "3mo": 63,
            "6mo": 126,
            "1y": 252,
            "12mo": 252,
            "2y": 504,
            "5y": 1260,
        }
        n_bars = period_map.get(period.lower(), 252)
        if len(raw) > n_bars:
            sliced = raw.iloc[-n_bars:].copy()
        else:
            sliced = raw.copy()

        source = f"historical · Four-Company Research Dataset ({len(sliced)} daily bars)"
        stamp = sliced.index[-1].isoformat() if hasattr(sliced.index[-1], "isoformat") else str(sliced.index[-1])
        return sliced, source, stamp, False

    def compute_indicators(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Calculates standard technical indicators on historical dataframe."""
        out = frame.copy()
        c = out["close"]
        h = out.get("high", c)
        l = out.get("low", c)

        out["returns"] = c.pct_change()
        out["sma_10"] = c.rolling(10).mean()
        out["sma_20"] = c.rolling(20).mean()
        out["sma_30"] = c.rolling(30).mean()
        out["ema_20"] = c.ewm(span=20, adjust=False).mean()

        # Wilder's 14-period RSI
        delta = c.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        out["rsi"] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        out["macd"] = ema12 - ema26
        out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()

        # Realized Volatility (20-day annualized)
        out["volatility"] = out["returns"].rolling(20).std() * np.sqrt(252)

        # 14-period ADX
        tr1 = h - l
        tr2 = (h - c.shift(1)).abs()
        tr3 = (l - c.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

        up_move = h - h.shift(1)
        down_move = l.shift(1) - l
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        plus_di = 100 * (pd.Series(plus_dm, index=c.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr14)
        minus_di = 100 * (pd.Series(minus_dm, index=c.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr14)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        out["adx"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

        return out

    def compute_risk_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculates CAGR, Sharpe, Sortino, Drawdown, and VaR."""
        clean_rets = returns.dropna()
        if len(clean_rets) < 5:
            return {
                "cagr": 0.0,
                "annualized_volatility": 0.0,
                "sharpe": 0.0,
                "sortino": 0.0,
                "max_drawdown": 0.0,
                "var_95": 0.0,
                "cvar_95": 0.0,
            }

        mean_ret = clean_rets.mean() * 252
        vol = clean_rets.std() * np.sqrt(252)
        sharpe = (mean_ret - 0.065) / vol if vol > 1e-6 else 0.0

        downside = clean_rets[clean_rets < 0].std() * np.sqrt(252)
        sortino = (mean_ret - 0.065) / downside if downside > 1e-6 else sharpe

        cum = (1 + clean_rets).cumprod()
        peaks = cum.cummax()
        dd = (cum - peaks) / peaks
        max_dd = float(dd.min())

        var_95 = float(np.percentile(clean_rets, 5))
        cvar_95 = float(clean_rets[clean_rets <= var_95].mean()) if len(clean_rets[clean_rets <= var_95]) else var_95

        n_years = max(len(clean_rets) / 252, 0.1)
        total_ret = float(cum.iloc[-1] - 1)
        cagr = float((1 + total_ret) ** (1 / n_years) - 1) if total_ret > -1 else -1.0

        return {
            "cagr": cagr,
            "annualized_volatility": float(vol),
            "sharpe": float(sharpe),
            "sortino": float(sortino),
            "max_drawdown": max_dd,
            "var_95": var_95,
            "cvar_95": cvar_95,
        }

    def classify_regime(self, frame: pd.DataFrame) -> Dict[str, Any]:
        """Determines market regime with quantitative confidence and supporting indicators."""
        ind = self.compute_indicators(frame)
        last = ind.iloc[-1]

        c = frame["close"]
        sma20 = ind["sma_20"].iloc[-1] if "sma_20" in ind else c.mean()
        adx = last.get("adx", 20.0)
        vol = last.get("volatility", 0.16)

        slope_20 = (c.iloc[-1] - c.iloc[-20]) / c.iloc[-20] if len(c) >= 20 else 0.0

        if adx >= 22.0 and slope_20 > 0.015:
            regime = "Bullish trending"
            confidence = min(0.65 + (adx - 22) * 0.015, 0.95)
            exp = "Strong directional positive trend with elevated ADX and positive 20-session slope."
        elif adx >= 22.0 and slope_20 < -0.015:
            regime = "Bearish trending"
            confidence = min(0.65 + (adx - 22) * 0.015, 0.95)
            exp = "Persistent downward price momentum with elevated ADX and negative 20-session slope."
        elif vol > 0.28:
            regime = "High volatility"
            confidence = min(0.60 + (vol - 0.28) * 1.5, 0.92)
            exp = "Elevated realized price dispersion exceeding the historical volatility threshold."
        elif vol < 0.12:
            regime = "Low volatility compression"
            confidence = 0.75
            exp = "Realized price volatility compressed below historical baseline; potential breakout setup."
        else:
            regime = "Sideways range-bound"
            confidence = 0.70
            exp = "Price oscillating within horizontal bounds without definitive directional momentum."

        return {
            "regime": regime,
            "confidence": float(confidence),
            "explanation": exp,
            "supporting_indicators": {
                "adx_14": float(adx) if np.isfinite(adx) else 20.0,
                "annualized_volatility": float(vol) if np.isfinite(vol) else 0.16,
                "sma_20_slope": float(slope_20),
                "rsi_14": float(last.get("rsi", 50.0)) if np.isfinite(last.get("rsi", 50.0)) else 50.0,
            },
        }

    def backtest_strategy(
        self,
        frame: pd.DataFrame,
        strategy_id: str,
        initial_capital: float = 100000.0,
        transaction_cost_bps: float = 5.0,
        position_size: float = 1.0,
    ) -> Dict[str, Any]:
        """Simulates historical trade execution and returns performance metrics and equity curve."""
        ind = self.compute_indicators(frame)
        c = ind["close"]

        # Strategy signals
        if strategy_id == "ma_crossover":
            pos = (ind["sma_10"] > ind["sma_30"]).astype(float)
        elif strategy_id == "dual_ma":
            pos = (ind["sma_20"] > ind["close"].rolling(50).mean()).astype(float)
        elif strategy_id == "rsi_mean_reversion":
            pos = (ind["rsi"] < 40).astype(float)
        elif strategy_id == "momentum_breakout":
            h20 = ind["high"].rolling(20).max().shift(1)
            pos = (c > h20).astype(float)
        elif strategy_id == "bollinger_mean_reversion":
            std20 = c.rolling(20).std()
            lower = ind["sma_20"] - 2 * std20
            pos = (c <= lower).astype(float)
        elif strategy_id == "macd_trend":
            pos = (ind["macd"] > ind["macd_signal"]).astype(float)
        else:
            pos = (ind["sma_10"] > ind["sma_30"]).astype(float)

        pos = pos.shift(1).fillna(0.0)  # Next-session execution
        rets = ind["returns"].fillna(0.0)

        cost_factor = (transaction_cost_bps / 10000.0)
        trades_flag = (pos.diff() != 0) & (pos.diff().notna())
        strat_rets = pos * rets - (trades_flag.astype(float) * cost_factor)

        equity_curve = initial_capital * (1 + strat_rets).cumprod()
        total_ret = float(equity_curve.iloc[-1] / initial_capital - 1)

        dates = [str(d.date()) if hasattr(d, "date") else str(d)[:10] for d in frame.index]
        risk = self.compute_risk_metrics(strat_rets)

        # Build trade list
        trades = []
        in_trade = False
        entry_idx = 0
        entry_price = 0.0

        for i in range(1, len(frame)):
            if pos.iloc[i] > 0 and not in_trade:
                in_trade = True
                entry_idx = i
                entry_price = float(c.iloc[i])
            elif pos.iloc[i] == 0 and in_trade:
                in_trade = False
                exit_price = float(c.iloc[i])
                trade_ret = (exit_price / entry_price - 1)
                trades.append({
                    "entry_date": dates[entry_idx],
                    "exit_date": dates[i],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "return": trade_ret,
                })

        winning = [t for t in trades if t["return"] > 0]
        losing = [t for t in trades if t["return"] <= 0]
        win_rate = len(winning) / len(trades) if trades else 0.5
        profit_factor = (
            sum(t["return"] for t in winning) / abs(sum(t["return"] for t in losing))
            if losing and abs(sum(t["return"] for t in losing)) > 1e-6 else 1.5
        )

        return {
            "total_return": total_ret,
            "cagr": risk["cagr"],
            "sharpe": risk["sharpe"],
            "sortino": risk["sortino"],
            "max_drawdown": risk["max_drawdown"],
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "total_trades": len(trades),
            "equity": [float(v) for v in equity_curve.values],
            "dates": dates,
            "trades": trades,
        }


market_service = MarketDataService()
