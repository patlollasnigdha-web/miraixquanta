"""
ASTRAQUANT X — Limit Order Book (LOB) Feature Engineering
Computes microstructure features including spreads, micro-prices, depth imbalances,
and Order Flow Imbalance (OFI).
"""

from typing import Union
import numpy as np
import pandas as pd


def compute_bid_ask_spread(
    ask_price: Union[np.ndarray, pd.Series, float],
    bid_price: Union[np.ndarray, pd.Series, float],
) -> Union[np.ndarray, pd.Series, float]:
    """Computes the nominal bid-ask spread: ask - bid."""
    return ask_price - bid_price


def compute_relative_spread(
    ask_price: Union[np.ndarray, pd.Series],
    bid_price: Union[np.ndarray, pd.Series],
) -> Union[np.ndarray, pd.Series]:
    """Computes the percentage / relative spread: 2 * (ask - bid) / (ask + bid)."""
    mid = (ask_price + bid_price) / 2.0
    # Avoid zero division
    mid_safe = np.where(mid == 0, 1e-8, mid)
    return (ask_price - bid_price) / mid_safe


def compute_mid_price(
    ask_price: Union[np.ndarray, pd.Series, float],
    bid_price: Union[np.ndarray, pd.Series, float],
) -> Union[np.ndarray, pd.Series, float]:
    """Computes simple arithmetic mid-price."""
    return (ask_price + bid_price) / 2.0


def compute_micro_price(
    ask_price: Union[np.ndarray, pd.Series],
    ask_volume: Union[np.ndarray, pd.Series],
    bid_price: Union[np.ndarray, pd.Series],
    bid_volume: Union[np.ndarray, pd.Series],
) -> Union[np.ndarray, pd.Series]:
    """
    Computes volume-weighted micro-price:
    (ask_price * bid_volume + bid_price * ask_volume) / (bid_volume + ask_volume)
    Reflects the price weighted toward the side with less depth.
    """
    total_vol = bid_volume + ask_volume
    total_vol_safe = np.where(total_vol == 0, 1e-8, total_vol)
    return (ask_price * bid_volume + bid_price * ask_volume) / total_vol_safe


def compute_depth_imbalance(
    bid_volume: Union[np.ndarray, pd.Series],
    ask_volume: Union[np.ndarray, pd.Series],
) -> Union[np.ndarray, pd.Series]:
    """
    Computes order book depth imbalance ratio in [-1, +1]:
    (bid_volume - ask_volume) / (bid_volume + ask_volume)
    """
    total_vol = bid_volume + ask_volume
    total_vol_safe = np.where(total_vol == 0, 1e-8, total_vol)
    return (bid_volume - ask_volume) / total_vol_safe


def compute_multi_level_imbalance(
    bid_volumes: np.ndarray,
    ask_volumes: np.ndarray,
    levels: int = 5,
) -> np.ndarray:
    """
    Computes aggregate depth imbalance across top N levels.
    bid_volumes, ask_volumes shape: (n_samples, n_levels)
    """
    b_sum = np.sum(bid_volumes[:, :levels], axis=1)
    a_sum = np.sum(ask_volumes[:, :levels], axis=1)
    tot = b_sum + a_sum
    tot_safe = np.where(tot == 0, 1e-8, tot)
    return (b_sum - a_sum) / tot_safe


def compute_order_flow_imbalance(
    bid_prices: np.ndarray,
    bid_volumes: np.ndarray,
    ask_prices: np.ndarray,
    ask_volumes: np.ndarray,
) -> np.ndarray:
    """
    Computes Order Flow Imbalance (OFI) based on Cont, Kukanov & Stoikov (2014):
    Tracks changes in best bid and best ask price and volume levels.
    Inputs must be 1D time-series arrays representing consecutive events.
    """
    n = len(bid_prices)
    ofi = np.zeros(n, dtype=np.float32)

    for t in range(1, n):
        # Bid side change
        if bid_prices[t] > bid_prices[t - 1]:
            delta_v_bid = bid_volumes[t]
        elif bid_prices[t] == bid_prices[t - 1]:
            delta_v_bid = bid_volumes[t] - bid_volumes[t - 1]
        else:
            delta_v_bid = -bid_volumes[t - 1]

        # Ask side change
        if ask_prices[t] < ask_prices[t - 1]:
            delta_v_ask = ask_volumes[t]
        elif ask_prices[t] == ask_prices[t - 1]:
            delta_v_ask = ask_volumes[t] - ask_volumes[t - 1]
        else:
            delta_v_ask = -ask_volumes[t - 1]

        ofi[t] = delta_v_bid - delta_v_ask

    return ofi
