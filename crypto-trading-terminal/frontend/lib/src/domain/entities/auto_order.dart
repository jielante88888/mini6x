import 'package:equatable/equatable.dart';

/// 订单侧
enum OrderSide {
  buy('buy'),
  sell('sell');

  const OrderSide(this.value);
  final String value;
}

/// 订单类型
enum OrderType {
  market('market'),
  limit('limit'),
  stop('stop'),
  stopLimit('stop_limit');

  const OrderType(this.value);
  final String value;
}

/// 市场类型
enum MarketType {
  spot('spot'),
  futures('futures');

  const MarketType(this.value);
  final String value;
}

/// 订单状态
enum OrderStatus {
  newStatus('new'),
  pending('pending'),
  submitted('submitted'),
  filled('filled'),
  cancelled('cancelled'),
  rejected('rejected'),
  expired('expired');

  const OrderStatus(this.value);
  final String value;
}

/// 风险等级
enum RiskLevel {
  low('low'),
  medium('medium'),
  high('high'),
  critical('critical');

  const RiskLevel(this.value);
  final String value;
}

/// 自动订单实体
class AutoOrder extends Equatable {
  final int id;
  final String autoOrderId;
  final String strategyName;
  final String symbol;
  final MarketType marketType;
  final OrderSide orderSide;
  final double quantity;
  final int entryConditionId;
  final double? stopLossPrice;
  final double? takeProfitPrice;
  final double maxSlippage;
  final double maxSpread;
  final OrderStatus status;
  final bool isActive;
  final bool isPaused;
  final int triggerCount;
  final DateTime? lastTriggered;
  final int executionCount;
  final Map<String, dynamic>? lastExecutionResult;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? expiresAt;

  const AutoOrder({
    required this.id,
    required this.autoOrderId,
    required this.strategyName,
    required this.symbol,
    required this.marketType,
    required this.orderSide,
    required this.quantity,
    required this.entryConditionId,
    this.stopLossPrice,
    this.takeProfitPrice,
    this.maxSlippage = 0.01,
    this.maxSpread = 0.005,
    this.status = OrderStatus.newStatus,
    this.isActive = true,
    this.isPaused = false,
    this.triggerCount = 0,
    this.lastTriggered,
    this.executionCount = 0,
    this.lastExecutionResult,
    required this.createdAt,
    required this.updatedAt,
    this.expiresAt,
  });

  @override
  List<Object?> get props => [
    id,
    autoOrderId,
    strategyName,
    symbol,
    marketType,
    orderSide,
    quantity,
    entryConditionId,
    stopLossPrice,
    takeProfitPrice,
    maxSlippage,
    maxSpread,
    status,
    isActive,
    isPaused,
    triggerCount,
    lastTriggered,
    executionCount,
    lastExecutionResult,
    createdAt,
    updatedAt,
    expiresAt,
  ];

  /// 从 JSON 创建实例
  factory AutoOrder.fromJson(Map<String, dynamic> json) {
    return AutoOrder(
      id: json['id'] as int,
      autoOrderId: json['auto_order_id'] as String,
      strategyName: json['strategy_name'] as String,
      symbol: json['symbol'] as String,
      marketType: MarketType.values.firstWhere(
        (e) => e.value == json['market_type'],
        orElse: () => MarketType.spot,
      ),
      orderSide: OrderSide.values.firstWhere(
        (e) => e.value == json['order_side'],
        orElse: () => OrderSide.buy,
      ),
      quantity: (json['quantity'] as num).toDouble(),
      entryConditionId: json['entry_condition_id'] as int,
      stopLossPrice: json['stop_loss_price']?.toDouble(),
      takeProfitPrice: json['take_profit_price']?.toDouble(),
      maxSlippage: (json['max_slippage'] as num?)?.toDouble() ?? 0.01,
      maxSpread: (json['max_spread'] as num?)?.toDouble() ?? 0.005,
      status: OrderStatus.values.firstWhere(
        (e) => e.value == json['status'],
        orElse: () => OrderStatus.newStatus,
      ),
      isActive: json['is_active'] as bool,
      isPaused: json['is_paused'] as bool,
      triggerCount: json['trigger_count'] as int,
      lastTriggered: json['last_triggered'] != null
          ? DateTime.parse(json['last_triggered'] as String)
          : null,
      executionCount: json['execution_count'] as int,
      lastExecutionResult: json['last_execution_result'] as Map<String, dynamic>?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'] as String)
          : null,
    );
  }

  /// 转换为 JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'auto_order_id': autoOrderId,
      'strategy_name': strategyName,
      'symbol': symbol,
      'market_type': marketType.value,
      'order_side': orderSide.value,
      'quantity': quantity,
      'entry_condition_id': entryConditionId,
      'stop_loss_price': stopLossPrice,
      'take_profit_price': takeProfitPrice,
      'max_slippage': maxSlippage,
      'max_spread': maxSpread,
      'status': status.value,
      'is_active': isActive,
      'is_paused': isPaused,
      'trigger_count': triggerCount,
      'last_triggered': lastTriggered?.toIso8601String(),
      'execution_count': executionCount,
      'last_execution_result': lastExecutionResult,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'expires_at': expiresAt?.toIso8601String(),
    };
  }

  /// 创建副本
  AutoOrder copyWith({
    int? id,
    String? autoOrderId,
    String? strategyName,
    String? symbol,
    MarketType? marketType,
    OrderSide? orderSide,
    double? quantity,
    int? entryConditionId,
    double? stopLossPrice,
    double? takeProfitPrice,
    double? maxSlippage,
    double? maxSpread,
    OrderStatus? status,
    bool? isActive,
    bool? isPaused,
    int? triggerCount,
    DateTime? lastTriggered,
    int? executionCount,
    Map<String, dynamic>? lastExecutionResult,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? expiresAt,
  }) {
    return AutoOrder(
      id: id ?? this.id,
      autoOrderId: autoOrderId ?? this.autoOrderId,
      strategyName: strategyName ?? this.strategyName,
      symbol: symbol ?? this.symbol,
      marketType: marketType ?? this.marketType,
      orderSide: orderSide ?? this.orderSide,
      quantity: quantity ?? this.quantity,
      entryConditionId: entryConditionId ?? this.entryConditionId,
      stopLossPrice: stopLossPrice ?? this.stopLossPrice,
      takeProfitPrice: takeProfitPrice ?? this.takeProfitPrice,
      maxSlippage: maxSlippage ?? this.maxSlippage,
      maxSpread: maxSpread ?? this.maxSpread,
      status: status ?? this.status,
      isActive: isActive ?? this.isActive,
      isPaused: isPaused ?? this.isPaused,
      triggerCount: triggerCount ?? this.triggerCount,
      lastTriggered: lastTriggered ?? this.lastTriggered,
      executionCount: executionCount ?? this.executionCount,
      lastExecutionResult: lastExecutionResult ?? this.lastExecutionResult,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      expiresAt: expiresAt ?? this.expiresAt,
    );
  }

  /// 获取状态显示文本
  String get statusDisplayText {
    switch (status) {
      case OrderStatus.newStatus:
        return '新建';
      case OrderStatus.pending:
        return '待执行';
      case OrderStatus.submitted:
        return '已提交';
      case OrderStatus.filled:
        return '已成交';
      case OrderStatus.cancelled:
        return '已取消';
      case OrderStatus.rejected:
        return '已拒绝';
      case OrderStatus.expired:
        return '已过期';
    }
  }

  /// 获取状态颜色
  String get statusColor {
    if (!isActive) return 'grey';
    if (isPaused) return 'orange';
    
    switch (status) {
      case OrderStatus.newStatus:
        return 'blue';
      case OrderStatus.pending:
        return 'amber';
      case OrderStatus.submitted:
        return 'indigo';
      case OrderStatus.filled:
        return 'green';
      case OrderStatus.cancelled:
        return 'red';
      case OrderStatus.rejected:
        return 'red';
      case OrderStatus.expired:
        return 'grey';
    }
  }

  /// 获取最后执行状态
  bool? get isLastExecutionSuccessful {
    return lastExecutionResult?['success'] as bool?;
  }

  /// 获取最后执行消息
  String? get lastExecutionMessage {
    return lastExecutionResult?['message'] as String?;
  }

  /// 是否已过期
  bool get isExpired {
    return expiresAt != null && DateTime.now().isAfter(expiresAt!);
  }

  /// 是否可以执行
  bool get canExecute {
    return isActive && !isPaused && !isExpired;
  }
}

/// 创建自动订单请求
class CreateAutoOrderRequest extends Equatable {
  final String strategyName;
  final String symbol;
  final MarketType marketType;
  final OrderSide orderSide;
  final double quantity;
  final int entryConditionId;
  final double? stopLossPrice;
  final double? takeProfitPrice;
  final double maxSlippage;
  final double maxSpread;
  final DateTime? expiresAt;

  const CreateAutoOrderRequest({
    required this.strategyName,
    required this.symbol,
    required this.marketType,
    required this.orderSide,
    required this.quantity,
    required this.entryConditionId,
    this.stopLossPrice,
    this.takeProfitPrice,
    this.maxSlippage = 0.01,
    this.maxSpread = 0.005,
    this.expiresAt,
  });

  @override
  List<Object?> get props => [
    strategyName,
    symbol,
    marketType,
    orderSide,
    quantity,
    entryConditionId,
    stopLossPrice,
    takeProfitPrice,
    maxSlippage,
    maxSpread,
    expiresAt,
  ];

  Map<String, dynamic> toJson() {
    return {
      'strategy_name': strategyName,
      'symbol': symbol,
      'market_type': marketType.value,
      'order_side': orderSide.value,
      'quantity': quantity,
      'entry_condition_id': entryConditionId,
      'stop_loss_price': stopLossPrice,
      'take_profit_price': takeProfitPrice,
      'max_slippage': maxSlippage,
      'max_spread': maxSpread,
      'expires_at': expiresAt?.toIso8601String(),
    };
  }
}

/// 风险检查结果
class RiskCheckResult extends Equatable {
  final bool isApproved;
  final RiskLevel riskLevel;
  final String message;
  final String alertType;
  final double? currentValue;
  final double? limitValue;
  final Map<String, dynamic>? details;

  const RiskCheckResult({
    required this.isApproved,
    required this.riskLevel,
    required this.message,
    required this.alertType,
    this.currentValue,
    this.limitValue,
    this.details,
  });

  @override
  List<Object?> get props => [
    isApproved,
    riskLevel,
    message,
    alertType,
    currentValue,
    limitValue,
    details,
  ];

  factory RiskCheckResult.fromJson(Map<String, dynamic> json) {
    return RiskCheckResult(
      isApproved: json['is_approved'] as bool,
      riskLevel: RiskLevel.values.firstWhere(
        (e) => e.value == json['risk_level'],
        orElse: () => RiskLevel.medium,
      ),
      message: json['message'] as String,
      alertType: json['alert_type'] as String,
      currentValue: json['current_value']?.toDouble(),
      limitValue: json['limit_value']?.toDouble(),
      details: json['details'] as Map<String, dynamic>?,
    );
  }
}