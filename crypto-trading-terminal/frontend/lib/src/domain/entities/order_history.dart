import 'package:equatable/equatable.dart';

/// 执行状态枚举
enum ExecutionStatus {
  pending('pending', '待执行'),
  executing('executing', '执行中'),
  success('success', '成功'),
  failed('failed', '失败'),
  partiallyFilled('partially_filled', '部分成交'),
  cancelled('cancelled', '已取消'),
  retrying('retrying', '重试中'),
  timeout('timeout', '超时');

  const ExecutionStatus(this.value, this.displayName);
  final String value;
  final String displayName;
}

/// 订单历史记录实体
class OrderHistory extends Equatable {
  final int id;
  final int orderId;
  final int? autoOrderId;
  final int accountId;
  final int userId;
  final String symbol;
  final String orderType;
  final String orderSide;
  final double quantity;
  final double? price;
  final ExecutionStatus executionStatus;
  final double filledQuantity;
  final double? averagePrice;
  final double? commission;
  final String? errorMessage;
  final String? errorCode;
  final int retryCount;
  final int maxRetries;
  final DateTime executionStartTime;
  final DateTime? executionEndTime;
  final double? executionDuration;
  final String exchange;
  final String? exchangeOrderId;
  final String? clientOrderId;
  final Map<String, dynamic>? metadata;
  final DateTime createdAt;

  // 扩展信息
  final String? accountName;
  final String? autoOrderStrategyName;

  const OrderHistory({
    required this.id,
    required this.orderId,
    this.autoOrderId,
    required this.accountId,
    required this.userId,
    required this.symbol,
    required this.orderType,
    required this.orderSide,
    required this.quantity,
    this.price,
    required this.executionStatus,
    required this.filledQuantity,
    this.averagePrice,
    this.commission,
    this.errorMessage,
    this.errorCode,
    required this.retryCount,
    required this.maxRetries,
    required this.executionStartTime,
    this.executionEndTime,
    this.executionDuration,
    required this.exchange,
    this.exchangeOrderId,
    this.clientOrderId,
    this.metadata,
    required this.createdAt,
    this.accountName,
    this.autoOrderStrategyName,
  });

  /// 检查是否执行完成
  bool get isCompleted => executionStatus == ExecutionStatus.success || 
      executionStatus == ExecutionStatus.failed || 
      executionStatus == ExecutionStatus.cancelled;

  /// 检查是否成功
  bool get isSuccessful => executionStatus == ExecutionStatus.success;

  /// 检查是否失败
  bool get isFailed => executionStatus == ExecutionStatus.failed;

  /// 检查是否正在执行
  bool get isExecuting => executionStatus == ExecutionStatus.executing || 
      executionStatus == ExecutionStatus.retrying;

  /// 执行进度百分比
  double get progressPercentage => quantity > 0 ? (filledQuantity / quantity) * 100 : 0.0;

  /// 剩余数量
  double get remainingQuantity => quantity - filledQuantity;

  /// 预计完成时间
  DateTime? get estimatedCompletionTime {
    if (executionStartTime == null || executionDuration == null) return null;
    if (filledQuantity <= 0) return null;
    
    final remainingSeconds = remainingQuantity / (filledQuantity / 
        (DateTime.now().difference(executionStartTime).inSeconds));
    
    if (remainingSeconds.isNaN || remainingSeconds.isInfinite) return null;
    
    return DateTime.now().add(Duration(seconds: remainingSeconds.toInt()));
  }

  /// 获取状态颜色
  String get statusColor {
    switch (executionStatus) {
      case ExecutionStatus.success:
        return '#4CAF50'; // 绿色
      case ExecutionStatus.failed:
        return '#F44336'; // 红色
      case ExecutionStatus.executing:
      case ExecutionStatus.retrying:
        return '#2196F3'; // 蓝色
      case ExecutionStatus.partialFilled:
        return '#FF9800'; // 橙色
      case ExecutionStatus.cancelled:
        return '#9E9E9E'; // 灰色
      case ExecutionStatus.pending:
        return '#607D8B'; // 蓝灰色
      case ExecutionStatus.timeout:
        return '#E91E63'; // 粉色
      default:
        return '#757575'; // 默认灰色
    }
  }

  /// 获取状态图标
  String get statusIcon {
    switch (executionStatus) {
      case ExecutionStatus.success:
        return '✓';
      case ExecutionStatus.failed:
        return '✗';
      case ExecutionStatus.executing:
      case ExecutionStatus.retrying:
        return '⏳';
      case ExecutionStatus.partialFilled:
        return '⚠';
      case ExecutionStatus.cancelled:
        return '🚫';
      case ExecutionStatus.pending:
        return '⏸';
      case ExecutionStatus.timeout:
        return '⏰';
      default:
        return '❓';
    }
  }

  /// 格式化执行时长
  String get formattedExecutionDuration {
    if (executionDuration == null) return 'N/A';
    
    final seconds = executionDuration!.toInt();
    final minutes = seconds ~/ 60;
    final hours = minutes ~/ 60;
    
    if (hours > 0) {
      return '${hours}h ${minutes % 60}m ${seconds % 60}s';
    } else if (minutes > 0) {
      return '${minutes}m ${seconds % 60}s';
    } else {
      return '${seconds}s';
    }
  }

  @override
  List<Object?> get props => [
    id, orderId, autoOrderId, accountId, userId, symbol, orderType,
    orderSide, quantity, price, executionStatus, filledQuantity,
    averagePrice, commission, errorMessage, errorCode, retryCount,
    maxRetries, executionStartTime, executionEndTime, executionDuration,
    exchange, exchangeOrderId, clientOrderId, metadata, createdAt,
    accountName, autoOrderStrategyName,
  ];

  /// JSON序列化
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'order_id': orderId,
      'auto_order_id': autoOrderId,
      'account_id': accountId,
      'user_id': userId,
      'symbol': symbol,
      'order_type': orderType,
      'order_side': orderSide,
      'quantity': quantity,
      'price': price,
      'execution_status': executionStatus.value,
      'filled_quantity': filledQuantity,
      'average_price': averagePrice,
      'commission': commission,
      'error_message': errorMessage,
      'error_code': errorCode,
      'retry_count': retryCount,
      'max_retries': maxRetries,
      'execution_start_time': executionStartTime.toIso8601String(),
      'execution_end_time': executionEndTime?.toIso8601String(),
      'execution_duration': executionDuration,
      'exchange': exchange,
      'exchange_order_id': exchangeOrderId,
      'client_order_id': clientOrderId,
      'metadata': metadata,
      'created_at': createdAt.toIso8601String(),
      'account_name': accountName,
      'auto_order_strategy_name': autoOrderStrategyName,
    };
  }

  /// JSON反序列化
  factory OrderHistory.fromJson(Map<String, dynamic> json) {
    return OrderHistory(
      id: json['id'],
      orderId: json['order_id'],
      autoOrderId: json['auto_order_id'],
      accountId: json['account_id'],
      userId: json['user_id'],
      symbol: json['symbol'],
      orderType: json['order_type'],
      orderSide: json['order_side'],
      quantity: json['quantity'],
      price: json['price'],
      executionStatus: ExecutionStatus.values.firstWhere(
        (e) => e.value == json['execution_status'],
        orElse: () => ExecutionStatus.pending,
      ),
      filledQuantity: json['filled_quantity'] ?? 0.0,
      averagePrice: json['average_price'],
      commission: json['commission'],
      errorMessage: json['error_message'],
      errorCode: json['error_code'],
      retryCount: json['retry_count'] ?? 0,
      maxRetries: json['max_retries'] ?? 3,
      executionStartTime: DateTime.parse(json['execution_start_time']),
      executionEndTime: json['execution_end_time'] != null 
          ? DateTime.parse(json['execution_end_time']) : null,
      executionDuration: json['execution_duration'],
      exchange: json['exchange'],
      exchangeOrderId: json['exchange_order_id'],
      clientOrderId: json['client_order_id'],
      metadata: json['metadata'],
      createdAt: DateTime.parse(json['created_at']),
      accountName: json['account_name'],
      autoOrderStrategyName: json['auto_order_strategy_name'],
    );
  }

  /// 复制并修改
  OrderHistory copyWith({
    int? id,
    int? orderId,
    int? autoOrderId,
    int? accountId,
    int? userId,
    String? symbol,
    String? orderType,
    String? orderSide,
    double? quantity,
    double? price,
    ExecutionStatus? executionStatus,
    double? filledQuantity,
    double? averagePrice,
    double? commission,
    String? errorMessage,
    String? errorCode,
    int? retryCount,
    int? maxRetries,
    DateTime? executionStartTime,
    DateTime? executionEndTime,
    double? executionDuration,
    String? exchange,
    String? exchangeOrderId,
    String? clientOrderId,
    Map<String, dynamic>? metadata,
    DateTime? createdAt,
    String? accountName,
    String? autoOrderStrategyName,
  }) {
    return OrderHistory(
      id: id ?? this.id,
      orderId: orderId ?? this.orderId,
      autoOrderId: autoOrderId ?? this.autoOrderId,
      accountId: accountId ?? this.accountId,
      userId: userId ?? this.userId,
      symbol: symbol ?? this.symbol,
      orderType: orderType ?? this.orderType,
      orderSide: orderSide ?? this.orderSide,
      quantity: quantity ?? this.quantity,
      price: price ?? this.price,
      executionStatus: executionStatus ?? this.executionStatus,
      filledQuantity: filledQuantity ?? this.filledQuantity,
      averagePrice: averagePrice ?? this.averagePrice,
      commission: commission ?? this.commission,
      errorMessage: errorMessage ?? this.errorMessage,
      errorCode: errorCode ?? this.errorCode,
      retryCount: retryCount ?? this.retryCount,
      maxRetries: maxRetries ?? this.maxRetries,
      executionStartTime: executionStartTime ?? this.executionStartTime,
      executionEndTime: executionEndTime ?? this.executionEndTime,
      executionDuration: executionDuration ?? this.executionDuration,
      exchange: exchange ?? this.exchange,
      exchangeOrderId: exchangeOrderId ?? this.exchangeOrderId,
      clientOrderId: clientOrderId ?? this.clientOrderId,
      metadata: metadata ?? this.metadata,
      createdAt: createdAt ?? this.createdAt,
      accountName: accountName ?? this.accountName,
      autoOrderStrategyName: autoOrderStrategyName ?? this.autoOrderStrategyName,
    );
  }
}

/// 执行状态变更日志
class ExecutionStatusLog extends Equatable {
  final int id;
  final int orderId;
  final int orderHistoryId;
  final int? autoOrderId;
  final ExecutionStatus? previousStatus;
  final ExecutionStatus newStatus;
  final String? statusChangeReason;
  final Map<String, dynamic>? additionalData;
  final double currentFilledQuantity;
  final double? currentAveragePrice;
  final DateTime statusChangedAt;
  final DateTime createdAt;

  const ExecutionStatusLog({
    required this.id,
    required this.orderId,
    required this.orderHistoryId,
    this.autoOrderId,
    this.previousStatus,
    required this.newStatus,
    this.statusChangeReason,
    this.additionalData,
    required this.currentFilledQuantity,
    this.currentAveragePrice,
    required this.statusChangedAt,
    required this.createdAt,
  });

  @override
  List<Object?> get props => [
    id, orderId, orderHistoryId, autoOrderId, previousStatus, newStatus,
    statusChangeReason, additionalData, currentFilledQuantity,
    currentAveragePrice, statusChangedAt, createdAt,
  ];

  /// JSON序列化
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'order_id': orderId,
      'order_history_id': orderHistoryId,
      'auto_order_id': autoOrderId,
      'previous_status': previousStatus?.value,
      'new_status': newStatus.value,
      'status_change_reason': statusChangeReason,
      'additional_data': additionalData,
      'current_filled_quantity': currentFilledQuantity,
      'current_average_price': currentAveragePrice,
      'status_changed_at': statusChangedAt.toIso8601String(),
      'created_at': createdAt.toIso8601String(),
    };
  }

  /// JSON反序列化
  factory ExecutionStatusLog.fromJson(Map<String, dynamic> json) {
    return ExecutionStatusLog(
      id: json['id'],
      orderId: json['order_id'],
      orderHistoryId: json['order_history_id'],
      autoOrderId: json['auto_order_id'],
      previousStatus: json['previous_status'] != null 
          ? ExecutionStatus.values.firstWhere(
              (e) => e.value == json['previous_status'],
              orElse: () => ExecutionStatus.pending,
            ) : null,
      newStatus: ExecutionStatus.values.firstWhere(
        (e) => e.value == json['new_status'],
        orElse: () => ExecutionStatus.pending,
      ),
      statusChangeReason: json['status_change_reason'],
      additionalData: json['additional_data'],
      currentFilledQuantity: json['current_filled_quantity'] ?? 0.0,
      currentAveragePrice: json['current_average_price'],
      statusChangedAt: DateTime.parse(json['status_changed_at']),
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

/// 订单历史统计数据
class OrderHistoryStats extends Equatable {
  final int totalExecutions;
  final int successfulExecutions;
  final int failedExecutions;
  final int partiallyFilledExecutions;
  final int cancelledExecutions;
  final double totalVolume;
  final double totalPnl;
  final double averageExecutionTime;
  final double successRate;
  final double failureRate;
  final int executionsToday;
  final int executionsThisWeek;
  final int executionsThisMonth;
  final List<Map<String, dynamic>> topSymbols;
  final List<Map<String, dynamic>> topExchanges;

  const OrderHistoryStats({
    required this.totalExecutions,
    required this.successfulExecutions,
    required this.failedExecutions,
    required this.partiallyFilledExecutions,
    required this.cancelledExecutions,
    required this.totalVolume,
    required this.totalPnl,
    required this.averageExecutionTime,
    required this.successRate,
    required this.failureRate,
    required this.executionsToday,
    required this.executionsThisWeek,
    required this.executionsThisMonth,
    required this.topSymbols,
    required this.topExchanges,
  });

  @override
  List<Object?> get props => [
    totalExecutions, successfulExecutions, failedExecutions,
    partiallyFilledExecutions, cancelledExecutions, totalVolume,
    totalPnl, averageExecutionTime, successRate, failureRate,
    executionsToday, executionsThisWeek, executionsThisMonth,
    topSymbols, topExchanges,
  ];

  /// JSON序列化
  Map<String, dynamic> toJson() {
    return {
      'total_executions': totalExecutions,
      'successful_executions': successfulExecutions,
      'failed_executions': failedExecutions,
      'partially_filled_executions': partiallyFilledExecutions,
      'cancelled_executions': cancelledExecutions,
      'total_volume': totalVolume,
      'total_pnl': totalPnl,
      'average_execution_time': averageExecutionTime,
      'success_rate': successRate,
      'failure_rate': failureRate,
      'executions_today': executionsToday,
      'executions_this_week': executionsThisWeek,
      'executions_this_month': executionsThisMonth,
      'top_symbols': topSymbols,
      'top_exchanges': topExchanges,
    };
  }

  /// JSON反序列化
  factory OrderHistoryStats.fromJson(Map<String, dynamic> json) {
    return OrderHistoryStats(
      totalExecutions: json['total_executions'],
      successfulExecutions: json['successful_executions'],
      failedExecutions: json['failed_executions'],
      partiallyFilledExecutions: json['partially_filled_executions'],
      cancelledExecutions: json['cancelled_executions'],
      totalVolume: json['total_volume']?.toDouble() ?? 0.0,
      totalPnl: json['total_pnl']?.toDouble() ?? 0.0,
      averageExecutionTime: json['average_execution_time']?.toDouble() ?? 0.0,
      successRate: json['success_rate']?.toDouble() ?? 0.0,
      failureRate: json['failure_rate']?.toDouble() ?? 0.0,
      executionsToday: json['executions_today'],
      executionsThisWeek: json['executions_this_week'],
      executionsThisMonth: json['executions_this_month'],
      topSymbols: List<Map<String, dynamic>>.from(json['top_symbols'] ?? []),
      topExchanges: List<Map<String, dynamic>>.from(json['top_exchanges'] ?? []),
    );
  }
}

/// 实时执行状态
class RealTimeExecutionStatus extends Equatable {
  final int orderId;
  final int orderHistoryId;
  final int? autoOrderId;
  final ExecutionStatus currentStatus;
  final double progressPercentage;
  final DateTime? estimatedCompletionTime;
  final DateTime lastUpdateTime;
  final String? errorInfo;
  final Map<String, dynamic>? retryInfo;

  const RealTimeExecutionStatus({
    required this.orderId,
    required this.orderHistoryId,
    this.autoOrderId,
    required this.currentStatus,
    required this.progressPercentage,
    this.estimatedCompletionTime,
    required this.lastUpdateTime,
    this.errorInfo,
    this.retryInfo,
  });

  @override
  List<Object?> get props => [
    orderId, orderHistoryId, autoOrderId, currentStatus,
    progressPercentage, estimatedCompletionTime, lastUpdateTime,
    errorInfo, retryInfo,
  ];

  /// JSON序列化
  Map<String, dynamic> toJson() {
    return {
      'order_id': orderId,
      'order_history_id': orderHistoryId,
      'auto_order_id': autoOrderId,
      'current_status': currentStatus.value,
      'progress_percentage': progressPercentage,
      'estimated_completion_time': estimatedCompletionTime?.toIso8601String(),
      'last_update_time': lastUpdateTime.toIso8601String(),
      'error_info': errorInfo,
      'retry_info': retryInfo,
    };
  }

  /// JSON反序列化
  factory RealTimeExecutionStatus.fromJson(Map<String, dynamic> json) {
    return RealTimeExecutionStatus(
      orderId: json['order_id'],
      orderHistoryId: json['order_history_id'],
      autoOrderId: json['auto_order_id'],
      currentStatus: ExecutionStatus.values.firstWhere(
        (e) => e.value == json['current_status'],
        orElse: () => ExecutionStatus.pending,
      ),
      progressPercentage: json['progress_percentage']?.toDouble() ?? 0.0,
      estimatedCompletionTime: json['estimated_completion_time'] != null 
          ? DateTime.parse(json['estimated_completion_time']) : null,
      lastUpdateTime: DateTime.parse(json['last_update_time']),
      errorInfo: json['error_info'],
      retryInfo: json['retry_info'],
    );
  }
}