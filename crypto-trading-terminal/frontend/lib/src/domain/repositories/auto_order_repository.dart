import '../entities/auto_order.dart';

/// 自动订单仓库接口
abstract class AutoOrderRepository {
  /// 获取所有自动订单
  Future<List<AutoOrder>> getAutoOrders({
    String? filter,
    String? search,
  });

  /// 根据ID获取自动订单
  Future<AutoOrder?> getAutoOrderById(int id);

  /// 创建自动订单
  Future<AutoOrder> createAutoOrder(CreateAutoOrderRequest request);

  /// 更新自动订单
  Future<AutoOrder> updateAutoOrder(int id, UpdateAutoOrderRequest request);

  /// 删除自动订单
  Future<void> deleteAutoOrder(int id);

  /// 切换订单状态
  Future<AutoOrder> toggleOrderStatus(int id, bool isActive);

  /// 重新执行订单
  Future<AutoOrder> retryOrder(int id);

  /// 获取执行历史
  Future<List<OrderExecution>> getExecutionHistory(int autoOrderId);

  /// 获取统计信息
  Future<AutoOrderStatistics> getStatistics();
}

/// 创建自动订单请求
class CreateAutoOrderRequest {
  final String strategyName;
  final String symbol;
  final OrderSide orderSide;
  final double quantity;
  final MarketType marketType;
  final double? stopLossPrice;
  final double? takeProfitPrice;
  final double maxSlippage;
  final double maxSpread;
  final int entryConditionId;

  const CreateAutoOrderRequest({
    required this.strategyName,
    required this.symbol,
    required this.orderSide,
    required this.quantity,
    required this.marketType,
    this.stopLossPrice,
    this.takeProfitPrice,
    this.maxSlippage = 0.01,
    this.maxSpread = 0.005,
    required this.entryConditionId,
  });

  Map<String, dynamic> toJson() {
    return {
      'strategy_name': strategyName,
      'symbol': symbol,
      'order_side': orderSide.name,
      'quantity': quantity,
      'market_type': marketType.name,
      'stop_loss_price': stopLossPrice,
      'take_profit_price': takeProfitPrice,
      'max_slippage': maxSlippage,
      'max_spread': maxSpread,
      'entry_condition_id': entryConditionId,
    };
  }
}

/// 更新自动订单请求
class UpdateAutoOrderRequest {
  final String? strategyName;
  final double? quantity;
  final double? stopLossPrice;
  final double? takeProfitPrice;
  final double? maxSlippage;
  final double? maxSpread;
  final bool? isActive;

  const UpdateAutoOrderRequest({
    this.strategyName,
    this.quantity,
    this.stopLossPrice,
    this.takeProfitPrice,
    this.maxSlippage,
    this.maxSpread,
    this.isActive,
  });

  Map<String, dynamic> toJson() {
    final data = <String, dynamic>{};
    if (strategyName != null) data['strategy_name'] = strategyName;
    if (quantity != null) data['quantity'] = quantity;
    if (stopLossPrice != null) data['stop_loss_price'] = stopLossPrice;
    if (takeProfitPrice != null) data['take_profit_price'] = takeProfitPrice;
    if (maxSlippage != null) data['max_slippage'] = maxSlippage;
    if (maxSpread != null) data['max_spread'] = maxSpread;
    if (isActive != null) data['is_active'] = isActive;
    return data;
  }
}

/// 订单执行记录
class OrderExecution {
  final int id;
  final int autoOrderId;
  final String executionId;
  final String status;
  final bool success;
  final String? message;
  final double? filledQuantity;
  final double? averagePrice;
  final double? commission;
  final DateTime executionTime;
  final int? latencyMs;
  final int retryCount;

  const OrderExecution({
    required this.id,
    required this.autoOrderId,
    required this.executionId,
    required this.status,
    required this.success,
    this.message,
    this.filledQuantity,
    this.averagePrice,
    this.commission,
    required this.executionTime,
    this.latencyMs,
    this.retryCount = 0,
  });

  factory OrderExecution.fromJson(Map<String, dynamic> json) {
    return OrderExecution(
      id: json['id'],
      autoOrderId: json['auto_order_id'],
      executionId: json['execution_id'],
      status: json['status'],
      success: json['success'],
      message: json['message'],
      filledQuantity: json['filled_quantity']?.toDouble(),
      averagePrice: json['average_price']?.toDouble(),
      commission: json['commission']?.toDouble(),
      executionTime: DateTime.parse(json['execution_time']),
      latencyMs: json['latency_ms'],
      retryCount: json['retry_count'] ?? 0,
    );
  }
}

/// 自动订单统计信息
class AutoOrderStatistics {
  final int totalOrders;
  final int activeOrders;
  final int pausedOrders;
  final int completedOrders;
  final double totalExecutionCount;
  final double successRate;
  final double averageExecutionTime;
  final double totalPnl;
  final int totalTriggerCount;

  const AutoOrderStatistics({
    required this.totalOrders,
    required this.activeOrders,
    required this.pausedOrders,
    required this.completedOrders,
    required this.totalExecutionCount,
    required this.successRate,
    required this.averageExecutionTime,
    required this.totalPnl,
    required this.totalTriggerCount,
  });

  factory AutoOrderStatistics.fromJson(Map<String, dynamic> json) {
    return AutoOrderStatistics(
      totalOrders: json['total_orders'] ?? 0,
      activeOrders: json['active_orders'] ?? 0,
      pausedOrders: json['paused_orders'] ?? 0,
      completedOrders: json['completed_orders'] ?? 0,
      totalExecutionCount: (json['total_execution_count'] ?? 0).toDouble(),
      successRate: (json['success_rate'] ?? 0).toDouble(),
      averageExecutionTime: (json['average_execution_time'] ?? 0).toDouble(),
      totalPnl: (json['total_pnl'] ?? 0).toDouble(),
      totalTriggerCount: json['total_trigger_count'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_orders': totalOrders,
      'active_orders': activeOrders,
      'paused_orders': pausedOrders,
      'completed_orders': completedOrders,
      'total_execution_count': totalExecutionCount,
      'success_rate': successRate,
      'average_execution_time': averageExecutionTime,
      'total_pnl': totalPnl,
      'total_trigger_count': totalTriggerCount,
    };
  }
}