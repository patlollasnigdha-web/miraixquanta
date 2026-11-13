"""
MIRAI — Execution Simulation Endpoints (M15)
"""

from fastapi import APIRouter, Depends
import pandas as pd

from src.api.dependencies import get_execution_engine, get_data_access_service
from src.execution.execution_engine import IntelligentExecutionEngine
from src.data_engineering.data_access import DataAccessService
from src.execution.execution_schemas import OrderRequest, OrderSide, OrderType
from src.api.api_schemas import ExecutionSimulateRequest, ExecutionSimulateResponse

router = APIRouter(prefix="/execution", tags=["Execution Simulation"])


@router.post("/simulate", response_model=ExecutionSimulateResponse)
def simulate_execution(
    req: ExecutionSimulateRequest,
    data_service: DataAccessService = Depends(get_data_access_service),
    execution_engine: IntelligentExecutionEngine = Depends(get_execution_engine),
):
    """Simulates realistic virtual execution with conservative slippage and transaction costs."""
    sym = req.symbol.strip().upper()
    df = data_service.get_multistock_daily(symbols=[sym])
    if df.empty:
        df = data_service.get_nifty_daily_index()

    current_bar = df.iloc[-1] if not df.empty else pd.Series({"open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 10000})

    order_req = OrderRequest(
        symbol=sym,
        side=OrderSide(req.side.upper()),
        quantity=req.quantity,
        order_type=OrderType(req.order_type.upper()),
        limit_price=req.limit_price,
    )

    order = execution_engine.submit_order(request=order_req, current_bar=current_bar)

    return ExecutionSimulateResponse(
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side.value,
        order_type=order.order_type.value,
        status=order.status.value,
        requested_quantity=order.request.quantity,
        filled_quantity=order.filled_quantity,
        average_price=order.average_price,
        total_transaction_cost=getattr(order, "total_transaction_cost", 0.0),
        total_slippage=getattr(order, "total_slippage", 0.0),
    )
