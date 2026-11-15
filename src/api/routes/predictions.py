"""
MIRAI — Predictions Endpoints (M15)
"""

from fastapi import APIRouter, Depends, Query
from typing import Any, Dict, Optional
import pandas as pd

from src.api.dependencies import get_data_access_service
from src.data_engineering.data_access import DataAccessService
from src.api.api_schemas import PredictionRequest, PredictionResponse
from src.prediction.four_company_engine import four_company_engine

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/companies")
@router.get("/four-companies")
async def get_four_company_predictions(
    horizon: int = Query(5, ge=1, le=30),
    include_ollama: bool = Query(True)
) -> Dict[str, Any]:
    """
    Returns multi-factor predictions, P&L verdicts, and Ollama explanations
    for all four institutional companies: MRF, TCS, Jio Platforms, and Reliance Industries.
    """
    return await four_company_engine.get_all_four_predictions(horizon=horizon, include_ollama=include_ollama)


@router.get("/companies/{symbol}")
async def get_single_company_prediction(
    symbol: str,
    horizon: int = Query(5, ge=1, le=30)
) -> Dict[str, Any]:
    """Returns prediction, verdict, and Ollama explanation for a single company."""
    analysis = four_company_engine.predict_and_decide(symbol, horizon=horizon)
    if "error" not in analysis:
        analysis["ollama_explanation"] = await four_company_engine.generate_ollama_explanation(analysis)
    return analysis


@router.post("", response_model=PredictionResponse)
def get_predictions(
    req: PredictionRequest,
    data_service: DataAccessService = Depends(get_data_access_service),
):
    """Generates directional price predictions using Four-Company Decision Engine."""
    sym = req.symbol.strip().upper()
    try:
        analysis = four_company_engine.predict_and_decide(sym, horizon=5)
        if "expected_net_return_pct" in analysis:
            net_ret = analysis["expected_net_return_pct"]
            direction = "UPWARD" if net_ret > 1.0 else ("DOWNWARD" if net_ret < -1.0 else "STATIONARY")
            conf = analysis["confidence"]
        else:
            direction = "STATIONARY"
            conf = 0.50
    except Exception:
        direction = "STATIONARY"
        conf = 0.50

    return PredictionResponse(
        symbol=sym,
        pipeline="four_company_focus",
        horizon=req.horizon,
        predicted_direction=direction,
        confidence=round(float(conf), 2),
        model_version=f"{req.model_name or 'four_company_engine'}_v2.0",
        limitations=[
            "Deterministic multi-factor quantitative engine output; past returns do not guarantee future performance.",
            "Incorporates 0.20% estimated round-trip transaction costs.",
        ],
    )
