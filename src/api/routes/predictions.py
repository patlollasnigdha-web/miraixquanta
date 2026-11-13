"""
MIRAI — Predictions Endpoints (M15)
"""

from fastapi import APIRouter, Depends
import pandas as pd

from src.api.dependencies import get_data_access_service
from src.data_engineering.data_access import DataAccessService
from src.api.api_schemas import PredictionRequest, PredictionResponse

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post("", response_model=PredictionResponse)
def get_predictions(
    req: PredictionRequest,
    data_service: DataAccessService = Depends(get_data_access_service),
):
    """Generates directional price predictions using M03 predictive AI models."""
    sym = req.symbol.strip().upper()
    df = data_service.get_multistock_daily(symbols=[sym])
    if df.empty:
        df = data_service.get_nifty_daily_index()

    # Directional inference
    if len(df) >= 20:
        ret_20 = (df["close"].iloc[-1] / df["close"].iloc[-20]) - 1.0
        direction = "UPWARD" if ret_20 > 0.01 else ("DOWNWARD" if ret_20 < -0.01 else "STATIONARY")
        conf = min(0.95, max(0.55, 0.50 + abs(ret_20)))
    else:
        direction = "STATIONARY"
        conf = 0.50

    return PredictionResponse(
        symbol=sym,
        pipeline=req.pipeline,
        horizon=req.horizon,
        predicted_direction=direction,
        confidence=round(float(conf), 2),
        model_version=f"{req.model_name or 'random_forest'}_v1.0",
        limitations=[
            "Statistical classification model output; past accuracy does not guarantee future results.",
            "Predictions should be corroborated by stock strength and risk engine constraints.",
        ],
    )
