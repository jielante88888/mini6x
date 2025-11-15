"""
订单历史记录和执行状态跟踪API
提供订单执行历史查询、执行状态监控和实时状态更新功能
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...storage.models import (
    OrderHistory, ExecutionStatusLog, Order, AutoOrder, Account, User,
    ExecutionStatus, OrderType, OrderSide
)

# 创建路由器
router = APIRouter(prefix="/api/v1/order-history", tags=["order-history"])


# Pydantic模型
class OrderHistoryResponse(BaseModel):
    """订单历史响应模型"""
    id: int
    order_id: int
    auto_order_id: Optional[int]
    account_id: int
    user_id: int
    symbol: str
    order_type: str
    order_side: str
    quantity: float
    price: Optional[float]
    execution_status: str
    filled_quantity: float
    average_price: Optional[float]
    commission: Optional[float]
    error_message: Optional[str]
    error_code: Optional[str]
    retry_count: int
    max_retries: int
    execution_start_time: datetime
    execution_end_time: Optional[datetime]
    execution_duration: Optional[float]
    exchange: str
    exchange_order_id: Optional[str]
    client_order_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    # 扩展信息
    account_name: Optional[str] = None
    auto_order_strategy_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ExecutionStatusLogResponse(BaseModel):
    """执行状态变更日志响应模型"""
    id: int
    order_id: int
    order_history_id: int
    auto_order_id: Optional[int]
    previous_status: Optional[str]
    new_status: str
    status_change_reason: Optional[str]
    additional_data: Optional[Dict[str, Any]]
    current_filled_quantity: float
    current_average_price: Optional[float]
    status_changed_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderHistoryFilters(BaseModel):
    """订单历史过滤器"""
    user_id: Optional[int] = None
    account_id: Optional[int] = None
    symbol: Optional[str] = None
    order_type: Optional[OrderType] = None
    order_side: Optional[OrderSide] = None
    execution_status: Optional[ExecutionStatus] = None
    exchange: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Query(default=50, ge=1, le=200)
    offset: int = Query(default=0, ge=0)
    
    # 排序
    sort_by: str = Query(default="execution_start_time", regex="^(execution_start_time|created_at|execution_duration|quantity)$")
    sort_order: str = Query(default="desc", regex="^(asc|desc)$")


class OrderHistoryStats(BaseModel):
    """订单历史统计模型"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    partially_filled_executions: int
    cancelled_executions: int
    total_volume: float
    total_pnl: float
    average_execution_time: float
    success_rate: float
    failure_rate: float
    
    # 按时间统计
    executions_today: int
    executions_this_week: int
    executions_this_month: int
    
    # 按交易对统计
    top_symbols: List[Dict[str, Any]]
    top_exchanges: List[Dict[str, Any]]


class RealTimeExecutionStatus(BaseModel):
    """实时执行状态模型"""
    order_id: int
    order_history_id: int
    auto_order_id: Optional[int]
    current_status: ExecutionStatus
    progress_percentage: float
    estimated_completion_time: Optional[datetime]
    last_update_time: datetime
    error_info: Optional[str]
    retry_info: Optional[Dict[str, Any]]


# API端点实现

@router.get("/", response_model=List[OrderHistoryResponse])
async def get_order_history(
    filters: OrderHistoryFilters = Depends(),
    db: Session = Depends(get_db)
):
    """
    获取订单执行历史列表
    
    支持按用户、账户、交易对、订单类型、执行状态等条件过滤
    支持分页和排序
    """
    try:
        # 构建查询
        query = db.query(OrderHistory).join(Order, OrderHistory.order_id == Order.id)
        
        # 应用过滤器
        if filters.user_id:
            query = query.filter(OrderHistory.user_id == filters.user_id)
        if filters.account_id:
            query = query.filter(OrderHistory.account_id == filters.account_id)
        if filters.symbol:
            query = query.filter(OrderHistory.symbol == filters.symbol)
        if filters.order_type:
            query = query.filter(OrderHistory.order_type == filters.order_type)
        if filters.order_side:
            query = query.filter(OrderHistory.order_side == filters.order_side)
        if filters.execution_status:
            query = query.filter(OrderHistory.execution_status == filters.execution_status)
        if filters.exchange:
            query = query.filter(OrderHistory.exchange == filters.exchange)
        if filters.start_date:
            query = query.filter(OrderHistory.execution_start_time >= filters.start_date)
        if filters.end_date:
            query = query.filter(OrderHistory.execution_start_time <= filters.end_date)
        
        # 应用排序
        sort_column = getattr(OrderHistory, filters.sort_by, OrderHistory.execution_start_time)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # 应用分页
        query = query.offset(filters.offset).limit(filters.limit)
        
        # 执行查询
        results = query.all()
        
        # 转换为响应模型并添加扩展信息
        response_list = []
        for result in results:
            response_data = OrderHistoryResponse.from_orm(result).dict()
            
            # 添加账户名称
            account = db.query(Account).filter(Account.id == result.account_id).first()
            if account:
                response_data['account_name'] = f"{account.exchange.value}_{account.account_type}"
            
            # 添加自动订单策略名称
            if result.auto_order_id:
                auto_order = db.query(AutoOrder).filter(AutoOrder.id == result.auto_order_id).first()
                if auto_order:
                    response_data['auto_order_strategy_name'] = auto_order.strategy_name
            
            response_list.append(OrderHistoryResponse(**response_data))
        
        return response_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单历史失败: {str(e)}")


@router.get("/stats", response_model=OrderHistoryStats)
async def get_order_history_stats(
    user_id: Optional[int] = Query(None),
    account_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    获取订单历史统计信息
    """
    try:
        # 构建基础查询
        query = db.query(OrderHistory)
        
        # 应用过滤器
        if user_id:
            query = query.filter(OrderHistory.user_id == user_id)
        if account_id:
            query = query.filter(OrderHistory.account_id == account_id)
        if start_date:
            query = query.filter(OrderHistory.execution_start_time >= start_date)
        if end_date:
            query = query.filter(OrderHistory.execution_start_time <= end_date)
        
        # 获取总数
        total_executions = query.count()
        
        # 获取成功/失败统计
        successful_executions = query.filter(
            OrderHistory.execution_status == ExecutionStatus.SUCCESS
        ).count()
        
        failed_executions = query.filter(
            OrderHistory.execution_status == ExecutionStatus.FAILED
        ).count()
        
        partially_filled_executions = query.filter(
            OrderHistory.execution_status == ExecutionStatus.PARTIALLY_FILLED
        ).count()
        
        cancelled_executions = query.filter(
            OrderHistory.execution_status == ExecutionStatus.CANCELLED
        ).count()
        
        # 计算总交易量和盈亏
        stats_query = query.with_entities(
            func.sum(OrderHistory.filled_quantity).label('total_volume'),
            func.avg(OrderHistory.execution_duration).label('avg_execution_time')
        ).first()
        
        total_volume = float(stats_query.total_volume or 0)
        average_execution_time = float(stats_query.avg_execution_time or 0)
        
        # 计算成功率
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        failure_rate = (failed_executions / total_executions * 100) if total_executions > 0 else 0
        
        # 时间范围统计
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        executions_today = query.filter(OrderHistory.execution_start_time >= today_start).count()
        executions_this_week = query.filter(OrderHistory.execution_start_time >= week_start).count()
        executions_this_month = query.filter(OrderHistory.execution_start_time >= month_start).count()
        
        # 获取热门交易对
        top_symbols_query = query.with_entities(
            OrderHistory.symbol,
            func.count(OrderHistory.id).label('execution_count')
        ).group_by(OrderHistory.symbol).order_by(desc('execution_count')).limit(5).all()
        
        top_symbols = [{"symbol": symbol, "count": count} for symbol, count in top_symbols_query]
        
        # 获取热门交易所
        top_exchanges_query = query.with_entities(
            OrderHistory.exchange,
            func.count(OrderHistory.id).label('execution_count')
        ).group_by(OrderHistory.exchange).order_by(desc('execution_count')).limit(5).all()
        
        top_exchanges = [{"exchange": exchange, "count": count} for exchange, count in top_exchanges_query]
        
        return OrderHistoryStats(
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            partially_filled_executions=partially_filled_executions,
            cancelled_executions=cancelled_executions,
            total_volume=total_volume,
            total_pnl=0.0,  # TODO: 计算实际盈亏
            average_execution_time=average_execution_time,
            success_rate=success_rate,
            failure_rate=failure_rate,
            executions_today=executions_today,
            executions_this_week=executions_this_week,
            executions_this_month=executions_this_month,
            top_symbols=top_symbols,
            top_exchanges=top_exchanges
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/execution-status/{order_id}", response_model=List[ExecutionStatusLogResponse])
async def get_execution_status_log(
    order_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    获取指定订单的执行状态变更日志
    """
    try:
        logs = db.query(ExecutionStatusLog).filter(
            ExecutionStatusLog.order_id == order_id
        ).order_by(desc(ExecutionStatusLog.status_changed_at)).limit(limit).all()
        
        return [ExecutionStatusLogResponse.from_orm(log) for log in logs]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取执行状态日志失败: {str(e)}")


@router.get("/real-time-status", response_model=List[RealTimeExecutionStatus])
async def get_real_time_execution_status(
    user_id: Optional[int] = Query(None),
    account_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    获取实时执行状态
    获取正在执行的订单的实时状态信息
    """
    try:
        # 查询正在执行的订单
        query = db.query(OrderHistory).filter(
            OrderHistory.execution_status.in_([
                ExecutionStatus.PENDING,
                ExecutionStatus.EXECUTING,
                ExecutionStatus.RETRYING
            ])
        )
        
        if user_id:
            query = query.filter(OrderHistory.user_id == user_id)
        if account_id:
            query = query.filter(OrderHistory.account_id == account_id)
        
        # 获取正在执行的订单
        executing_orders = query.order_by(desc(OrderHistory.execution_start_time)).all()
        
        result = []
        for order in executing_orders:
            # 计算执行进度
            if order.quantity > 0:
                progress = float(order.filled_quantity / order.quantity * 100)
            else:
                progress = 0.0
            
            # 估算完成时间
            estimated_completion = None
            if order.execution_start_time and order.execution_duration:
                if order.filled_quantity > 0:
                    remaining_quantity = order.quantity - order.filled_quantity
                    filled_rate = order.filled_quantity / (datetime.now() - order.execution_start_time).total_seconds()
                    if filled_rate > 0:
                        remaining_seconds = remaining_quantity / filled_rate
                        estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)
            
            result.append(RealTimeExecutionStatus(
                order_id=order.order_id,
                order_history_id=order.id,
                auto_order_id=order.auto_order_id,
                current_status=order.execution_status,
                progress_percentage=progress,
                estimated_completion_time=estimated_completion,
                last_update_time=order.updated_at,
                error_info=order.error_message if order.execution_status == ExecutionStatus.FAILED else None,
                retry_info={
                    "current_retry": order.retry_count,
                    "max_retries": order.max_retries,
                    "can_retry": order.retry_count < order.max_retries
                } if order.execution_status == ExecutionStatus.RETRYING else None
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时执行状态失败: {str(e)}")


@router.get("/order/{order_id}", response_model=OrderHistoryResponse)
async def get_order_history_by_order_id(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定订单的完整执行历史
    """
    try:
        order_history = db.query(OrderHistory).filter(
            OrderHistory.order_id == order_id
        ).order_by(desc(OrderHistory.execution_start_time)).first()
        
        if not order_history:
            raise HTTPException(status_code=404, detail="未找到订单执行历史")
        
        # 转换为响应模型
        response_data = OrderHistoryResponse.from_orm(order_history).dict()
        
        # 添加扩展信息
        account = db.query(Account).filter(Account.id == order_history.account_id).first()
        if account:
            response_data['account_name'] = f"{account.exchange.value}_{account.account_type}"
        
        if order_history.auto_order_id:
            auto_order = db.query(AutoOrder).filter(AutoOrder.id == order_history.auto_order_id).first()
            if auto_order:
                response_data['auto_order_strategy_name'] = auto_order.strategy_name
        
        return OrderHistoryResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单历史失败: {str(e)}")


@router.post("/order-history/{order_id}/update-status")
async def update_execution_status(
    order_id: int,
    status_update: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    更新订单执行状态
    用于手动更新订单状态（通常由执行引擎调用）
    """
    try:
        # 查找订单历史记录
        order_history = db.query(OrderHistory).filter(
            OrderHistory.order_id == order_id
        ).order_by(desc(OrderHistory.execution_start_time)).first()
        
        if not order_history:
            raise HTTPException(status_code=404, detail="未找到订单历史记录")
        
        # 更新状态
        previous_status = order_history.execution_status
        
        if 'execution_status' in status_update:
            order_history.execution_status = ExecutionStatus(status_update['execution_status'])
        
        if 'filled_quantity' in status_update:
            order_history.filled_quantity = Decimal(str(status_update['filled_quantity']))
        
        if 'average_price' in status_update:
            order_history.average_price = Decimal(str(status_update['average_price'])) if status_update['average_price'] else None
        
        if 'commission' in status_update:
            order_history.commission = Decimal(str(status_update['commission'])) if status_update['commission'] else None
        
        if 'error_message' in status_update:
            order_history.error_message = status_update['error_message']
        
        if 'error_code' in status_update:
            order_history.error_code = status_update['error_code']
        
        if 'retry_count' in status_update:
            order_history.retry_count = status_update['retry_count']
        
        # 更新执行时间
        if order_history.execution_status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            order_history.execution_end_time = datetime.now()
            if order_history.execution_start_time:
                order_history.execution_duration = (order_history.execution_end_time - order_history.execution_start_time).total_seconds()
        
        order_history.updated_at = datetime.now()
        
        # 创建状态变更日志
        status_log = ExecutionStatusLog(
            order_id=order_id,
            order_history_id=order_history.id,
            auto_order_id=order_history.auto_order_id,
            previous_status=previous_status,
            new_status=order_history.execution_status,
            status_change_reason=status_update.get('status_change_reason'),
            additional_data=status_update.get('additional_data'),
            current_filled_quantity=order_history.filled_quantity,
            current_average_price=order_history.average_price,
            status_changed_at=datetime.now()
        )
        
        db.add(status_log)
        db.commit()
        
        return {"message": "执行状态更新成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新执行状态失败: {str(e)}")