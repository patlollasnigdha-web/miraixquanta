"""
Tests for MIRAI Market Data Adapter (M14)
Validates chronological replay, lookahead prevention, staleness checking, and pipeline isolation.
"""

import pytest
import numpy as np
import pandas as pd
from src.paper_trading.market_data_adapter import MarketDataAdapter
from src.paper_trading.paper_trading_schemas import PaperTradingMode


@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range("2026-01-01", periods=10, freq="1D")
    return pd.DataFrame({
        "open": [100.0, 102.0, 101.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0, 112.0],
        "high": [103.0, 104.0, 103.0, 107.0, 106.0, 109.0, 110.0, 109.0, 113.0, 115.0],
        "low": [99.0, 100.0, 99.0, 103.0, 102.0, 105.0, 106.0, 105.0, 108.0, 110.0],
        "close": [102.0, 101.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0, 112.0, 114.0],
        "volume": [1000] * 10,
    }, index=dates)


def test_chronological_replay_no_lookahead(sample_ohlcv):
    adapter = MarketDataAdapter(mode=PaperTradingMode.HISTORICAL_REPLAY)
    count = adapter.load_replay_data(symbol="TEST", custom_df=sample_ohlcv)
    assert count == 10
    assert adapter.has_next_bar() is True

    # Step through first 3 bars
    for i in range(3):
        res = adapter.get_next_bar()
        assert res is not None
        current_bar, history_slice = res
        # Current bar matches index
        assert current_bar.name == sample_ohlcv.index[i]
        # History slice length is exactly i+1 (strict zero lookahead)
        assert len(history_slice) == i + 1
        assert history_slice.index[-1] == sample_ohlcv.index[i]


def test_pause_resume_stop_replay(sample_ohlcv):
    adapter = MarketDataAdapter()
    adapter.load_replay_data(custom_df=sample_ohlcv)

    # Step 1
    res1 = adapter.get_next_bar()
    assert res1 is not None

    # Pause
    adapter.pause()
    assert adapter.get_next_bar() is None

    # Resume
    adapter.resume()
    res2 = adapter.get_next_bar()
    assert res2 is not None

    # Stop
    adapter.stop()
    assert adapter.has_next_bar() is False
    assert adapter.get_next_bar() is None


def test_staleness_detection():
    # Historical replay mode does not flag historical timestamps as stale
    hist_adapter = MarketDataAdapter(mode=PaperTradingMode.HISTORICAL_REPLAY)
    old_time = pd.Timestamp("2020-01-01 10:00:00")
    assert hist_adapter.is_data_stale(old_time) is False

    # Live feed mode flags bars older than timeout
    live_adapter = MarketDataAdapter(mode=PaperTradingMode.LIVE_FEED, stale_data_timeout_sec=60.0)
    now = pd.Timestamp.now()
    fresh_time = now - pd.Timedelta(seconds=10)
    stale_time = now - pd.Timedelta(seconds=120)

    assert live_adapter.is_data_stale(fresh_time, current_time=now) is False
    assert live_adapter.is_data_stale(stale_time, current_time=now) is True


def test_pipeline_isolation_rejection():
    adapter = MarketDataAdapter(pipeline_id="pipeline_b_nifty")
    fi2010_df = pd.DataFrame({
        "lob_feature_0": [1.0, 2.0],
        "lob_feature_1": [3.0, 4.0],
    })
    # Passing FI-2010 microstructure data to Indian Equity pipeline must raise ValueError
    with pytest.raises(ValueError, match="Pipeline Isolation Breach"):
        adapter.load_replay_data(custom_df=fi2010_df)
