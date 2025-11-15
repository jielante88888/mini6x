import 'package:equatable/equatable.dart';

/// 风险等级
enum RiskLevel { LOW, MEDIUM, HIGH, CRITICAL }

/// 市场类型
enum MarketType { spot, futures }

/// 警告严重性
enum AlertSeverity { INFO, WARNING, CRITICAL, BLOCKED }

/// 仓位方向
enum PositionSide { LONG, SHORT }

/// 风险仪表板数据
class RiskDashboardData extends Equatable {
  final DashboardSummary summary;
  final RiskDistribution riskDistribution;
  final PerformanceMetrics performance;

  const RiskDashboardData({
    required this.summary,
    required this.riskDistribution,
    required this.performance,
  });

  factory RiskDashboardData.fromJson(Map<String, dynamic> json) {
    return RiskDashboardData(
      summary: DashboardSummary.fromJson(json['summary']),
      riskDistribution: RiskDistribution.fromJson(json['risk_distribution']),
      performance: PerformanceMetrics.fromJson(json['performance']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'summary': summary.toJson(),
      'risk_distribution': riskDistribution.toJson(),
      'performance': performance.toJson(),
    };
  }

  @override
  List<Object?> get props => [summary, riskDistribution, performance];
}

/// 仪表板摘要
class DashboardSummary extends Equatable {
  final int totalAccounts;
  final int totalPositions;
  final double totalPositionsValue;
  final double totalUnrealizedPnl;
  final int unacknowledgedAlerts;
  final int activeAutoOrders;
  final String overallRiskLevel;

  const DashboardSummary({
    required this.totalAccounts,
    required this.totalPositions,
    required this.totalPositionsValue,
    required this.totalUnrealizedPnl,
    required this.unacknowledgedAlerts,
    required this.activeAutoOrders,
    required this.overallRiskLevel,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      totalAccounts: json['total_accounts'],
      totalPositions: json['total_positions'],
      totalPositionsValue: (json['total_positions_value'] as num).toDouble(),
      totalUnrealizedPnl: (json['total_unrealized_pnl'] as num).toDouble(),
      unacknowledgedAlerts: json['unacknowledged_alerts'],
      activeAutoOrders: json['active_auto_orders'],
      overallRiskLevel: json['overall_risk_level'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_accounts': totalAccounts,
      'total_positions': totalPositions,
      'total_positions_value': totalPositionsValue,
      'total_unrealized_pnl': totalUnrealizedPnl,
      'unacknowledged_alerts': unacknowledgedAlerts,
      'active_auto_orders': activeAutoOrders,
      'overall_risk_level': overallRiskLevel,
    };
  }

  @override
  List<Object?> get props => [
        totalAccounts,
        totalPositions,
        totalPositionsValue,
        totalUnrealizedPnl,
        unacknowledgedAlerts,
        activeAutoOrders,
        overallRiskLevel,
      ];
}

/// 风险分布
class RiskDistribution extends Equatable {
  final int lowRisk;
  final int mediumRisk;
  final int highRisk;
  final int criticalRisk;

  const RiskDistribution({
    required this.lowRisk,
    required this.mediumRisk,
    required this.highRisk,
    required this.criticalRisk,
  });

  factory RiskDistribution.fromJson(Map<String, dynamic> json) {
    return RiskDistribution(
      lowRisk: json['low_risk'] ?? 0,
      mediumRisk: json['medium_risk'] ?? 0,
      highRisk: json['high_risk'] ?? 0,
      criticalRisk: json['critical_risk'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'low_risk': lowRisk,
      'medium_risk': mediumRisk,
      'high_risk': highRisk,
      'critical_risk': criticalRisk,
    };
  }

  @override
  List<Object?> get props => [lowRisk, mediumRisk, highRisk, criticalRisk];
}

/// 性能指标
class PerformanceMetrics extends Equatable {
  final double dailyPnl;
  final double winRate;
  final int totalTrades;

  const PerformanceMetrics({
    required this.dailyPnl,
    required this.winRate,
    required this.totalTrades,
  });

  factory PerformanceMetrics.fromJson(Map<String, dynamic> json) {
    return PerformanceMetrics(
      dailyPnl: (json['daily_pnl'] as num).toDouble(),
      winRate: (json['win_rate'] as num).toDouble(),
      totalTrades: json['total_trades'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'daily_pnl': dailyPnl,
      'win_rate': winRate,
      'total_trades': totalTrades,
    };
  }

  @override
  List<Object?> get props => [dailyPnl, winRate, totalTrades];
}

/// 仓位风险信息
class PositionRisk extends Equatable {
  final int positionId;
  final int accountId;
  final String symbol;
  final String marketType;
  final double quantity;
  final double quantityAvailable;
  final double quantityFrozen;
  final double avgPrice;
  final double entryPrice;
  final double unrealizedPnl;
  final double realizedPnl;
  final int? leverage;
  final String? positionSide;
  final String status;
  final String updatedAt;
  final String riskLevel;
  final double exposurePercent;
  final double marginRatio;
  final double? liquidationPrice;

  const PositionRisk({
    required this.positionId,
    required this.accountId,
    required this.symbol,
    required this.marketType,
    required this.quantity,
    required this.quantityAvailable,
    required this.quantityFrozen,
    required this.avgPrice,
    required this.entryPrice,
    required this.unrealizedPnl,
    required this.realizedPnl,
    this.leverage,
    this.positionSide,
    required this.status,
    required this.updatedAt,
    required this.riskLevel,
    required this.exposurePercent,
    required this.marginRatio,
    this.liquidationPrice,
  });

  factory PositionRisk.fromJson(Map<String, dynamic> json) {
    return PositionRisk(
      positionId: json['position_id'],
      accountId: json['account_id'],
      symbol: json['symbol'],
      marketType: json['market_type'],
      quantity: (json['quantity'] as num).toDouble(),
      quantityAvailable: (json['quantity_available'] as num).toDouble(),
      quantityFrozen: (json['quantity_frozen'] as num).toDouble(),
      avgPrice: (json['avg_price'] as num).toDouble(),
      entryPrice: (json['entry_price'] as num).toDouble(),
      unrealizedPnl: (json['unrealized_pnl'] as num).toDouble(),
      realizedPnl: (json['realized_pnl'] as num).toDouble(),
      leverage: json['leverage'],
      positionSide: json['position_side'],
      status: json['status'],
      updatedAt: json['updated_at'],
      riskLevel: json['risk_level'],
      exposurePercent: (json['exposure_percent'] as num).toDouble(),
      marginRatio: (json['margin_ratio'] as num).toDouble(),
      liquidationPrice: json['liquidation_price'] != null
          ? (json['liquidation_price'] as num).toDouble()
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'position_id': positionId,
      'account_id': accountId,
      'symbol': symbol,
      'market_type': marketType,
      'quantity': quantity,
      'quantity_available': quantityAvailable,
      'quantity_frozen': quantityFrozen,
      'avg_price': avgPrice,
      'entry_price': entryPrice,
      'unrealized_pnl': unrealizedPnl,
      'realized_pnl': realizedPnl,
      'leverage': leverage,
      'position_side': positionSide,
      'status': status,
      'updated_at': updatedAt,
      'risk_level': riskLevel,
      'exposure_percent': exposurePercent,
      'margin_ratio': marginRatio,
      'liquidation_price': liquidationPrice,
    };
  }

  /// 计算盈亏百分比
  double get pnlPercent {
    if (entryPrice <= 0) return 0.0;
    return ((avgPrice - entryPrice) / entryPrice) * 100;
  }

  /// 是否为多头仓位
  bool get isLong => positionSide == 'LONG';

  /// 是否为空头仓位
  bool get isShort => positionSide == 'SHORT';

  @override
  List<Object?> get props => [
        positionId,
        accountId,
        symbol,
        marketType,
        quantity,
        quantityAvailable,
        quantityFrozen,
        avgPrice,
        entryPrice,
        unrealizedPnl,
        realizedPnl,
        leverage,
        positionSide,
        status,
        updatedAt,
        riskLevel,
        exposurePercent,
        marginRatio,
        liquidationPrice,
      ];
}

/// 风险警告
class RiskAlert extends Equatable {
  final int alertId;
  final int accountId;
  final String severity;
  final String message;
  final String alertType;
  final String? symbol;
  final int? autoOrderId;
  final int? orderId;
  final Map<String, dynamic> details;
  final double? currentValue;
  final double? limitValue;
  final bool isAcknowledged;
  final DateTime? acknowledgedAt;
  final bool isResolved;
  final DateTime? resolvedAt;
  final bool notificationSent;
  final DateTime timestamp;

  const RiskAlert({
    required this.alertId,
    required this.accountId,
    required this.severity,
    required this.message,
    required this.alertType,
    this.symbol,
    this.autoOrderId,
    this.orderId,
    required this.details,
    this.currentValue,
    this.limitValue,
    required this.isAcknowledged,
    this.acknowledgedAt,
    required this.isResolved,
    this.resolvedAt,
    required this.notificationSent,
    required this.timestamp,
  });

  factory RiskAlert.fromJson(Map<String, dynamic> json) {
    return RiskAlert(
      alertId: json['alert_id'],
      accountId: json['account_id'],
      severity: json['severity'],
      message: json['message'],
      alertType: json['alert_type'],
      symbol: json['symbol'],
      autoOrderId: json['auto_order_id'],
      orderId: json['order_id'],
      details: json['details'] as Map<String, dynamic>? ?? {},
      currentValue: json['current_value']?.toDouble(),
      limitValue: json['limit_value']?.toDouble(),
      isAcknowledged: json['is_acknowledged'] ?? false,
      acknowledgedAt: json['acknowledged_at'] != null
          ? DateTime.parse(json['acknowledged_at'])
          : null,
      isResolved: json['is_resolved'] ?? false,
      resolvedAt: json['resolved_at'] != null
          ? DateTime.parse(json['resolved_at'])
          : null,
      notificationSent: json['notification_sent'] ?? false,
      timestamp: DateTime.parse(json['timestamp']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'alert_id': alertId,
      'account_id': accountId,
      'severity': severity,
      'message': message,
      'alert_type': alertType,
      'symbol': symbol,
      'auto_order_id': autoOrderId,
      'order_id': orderId,
      'details': details,
      'current_value': currentValue,
      'limit_value': limitValue,
      'is_acknowledged': isAcknowledged,
      'acknowledged_at': acknowledgedAt?.toIso8601String(),
      'is_resolved': isResolved,
      'resolved_at': resolvedAt?.toIso8601String(),
      'notification_sent': notificationSent,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  RiskAlert copyWith({
    int? alertId,
    int? accountId,
    String? severity,
    String? message,
    String? alertType,
    String? symbol,
    int? autoOrderId,
    int? orderId,
    Map<String, dynamic>? details,
    double? currentValue,
    double? limitValue,
    bool? isAcknowledged,
    DateTime? acknowledgedAt,
    bool? isResolved,
    DateTime? resolvedAt,
    bool? notificationSent,
    DateTime? timestamp,
  }) {
    return RiskAlert(
      alertId: alertId ?? this.alertId,
      accountId: accountId ?? this.accountId,
      severity: severity ?? this.severity,
      message: message ?? this.message,
      alertType: alertType ?? this.alertType,
      symbol: symbol ?? this.symbol,
      autoOrderId: autoOrderId ?? this.autoOrderId,
      orderId: orderId ?? this.orderId,
      details: details ?? this.details,
      currentValue: currentValue ?? this.currentValue,
      limitValue: limitValue ?? this.limitValue,
      isAcknowledged: isAcknowledged ?? this.isAcknowledged,
      acknowledgedAt: acknowledgedAt ?? this.acknowledgedAt,
      isResolved: isResolved ?? this.isResolved,
      resolvedAt: resolvedAt ?? this.resolvedAt,
      notificationSent: notificationSent ?? this.notificationSent,
      timestamp: timestamp ?? this.timestamp,
    );
  }

  @override
  List<Object?> get props => [
        alertId,
        accountId,
        severity,
        message,
        alertType,
        symbol,
        autoOrderId,
        orderId,
        details,
        currentValue,
        limitValue,
        isAcknowledged,
        acknowledgedAt,
        isResolved,
        resolvedAt,
        notificationSent,
        timestamp,
      ];
}

/// 风险指标
class RiskMetrics extends Equatable {
  final int totalTrades;
  final double totalVolume;
  final double totalPnl;
  final double winRate;
  final int orderCount;
  final double? avgExecutionTime;

  const RiskMetrics({
    required this.totalTrades,
    required this.totalVolume,
    required this.totalPnl,
    required this.winRate,
    required this.orderCount,
    this.avgExecutionTime,
  });

  factory RiskMetrics.fromJson(Map<String, dynamic> json) {
    return RiskMetrics(
      totalTrades: json['total_trades'] ?? 0,
      totalVolume: (json['total_volume'] as num).toDouble(),
      totalPnl: (json['total_pnl'] as num).toDouble(),
      winRate: (json['win_rate'] as num).toDouble(),
      orderCount: json['order_count'] ?? 0,
      avgExecutionTime: json['avg_execution_time']?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_trades': totalTrades,
      'total_volume': totalVolume,
      'total_pnl': totalPnl,
      'win_rate': winRate,
      'order_count': orderCount,
      'avg_execution_time': avgExecutionTime,
    };
  }

  @override
  List<Object?> get props => [
        totalTrades,
        totalVolume,
        totalPnl,
        winRate,
        orderCount,
        avgExecutionTime,
      ];
}

/// 风险配置
class RiskConfig extends Equatable {
  final int configId;
  final int accountId;
  final String configName;
  final double maxOrderSize;
  final double maxPositionSize;
  final int maxDailyTrades;
  final double maxDailyVolume;
  final double maxLossPerTrade;
  final double maxTotalExposure;
  final double stopLossPercentage;
  final double takeProfitPercentage;
  final String defaultRiskLevel;
  final String? tradingHoursStart;
  final String? tradingHoursEnd;
  final Map<String, dynamic>? additionalRules;
  final DateTime createdAt;
  final DateTime updatedAt;

  const RiskConfig({
    required this.configId,
    required this.accountId,
    required this.configName,
    required this.maxOrderSize,
    required this.maxPositionSize,
    required this.maxDailyTrades,
    required this.maxDailyVolume,
    required this.maxLossPerTrade,
    required this.maxTotalExposure,
    required this.stopLossPercentage,
    required this.takeProfitPercentage,
    required this.defaultRiskLevel,
    this.tradingHoursStart,
    this.tradingHoursEnd,
    this.additionalRules,
    required this.createdAt,
    required this.updatedAt,
  });

  factory RiskConfig.fromJson(Map<String, dynamic> json) {
    return RiskConfig(
      configId: json['config_id'],
      accountId: json['account_id'],
      configName: json['config_name'],
      maxOrderSize: (json['max_order_size'] as num).toDouble(),
      maxPositionSize: (json['max_position_size'] as num).toDouble(),
      maxDailyTrades: json['max_daily_trades'],
      maxDailyVolume: (json['max_daily_volume'] as num).toDouble(),
      maxLossPerTrade: (json['max_loss_per_trade'] as num).toDouble(),
      maxTotalExposure: (json['max_total_exposure'] as num).toDouble(),
      stopLossPercentage: (json['stop_loss_percentage'] as num).toDouble(),
      takeProfitPercentage: (json['take_profit_percentage'] as num).toDouble(),
      defaultRiskLevel: json['default_risk_level'],
      tradingHoursStart: json['trading_hours_start'],
      tradingHoursEnd: json['trading_hours_end'],
      additionalRules: json['additional_rules'] as Map<String, dynamic>?,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'config_id': configId,
      'account_id': accountId,
      'config_name': configName,
      'max_order_size': maxOrderSize,
      'max_position_size': maxPositionSize,
      'max_daily_trades': maxDailyTrades,
      'max_daily_volume': maxDailyVolume,
      'max_loss_per_trade': maxLossPerTrade,
      'max_total_exposure': maxTotalExposure,
      'stop_loss_percentage': stopLossPercentage,
      'take_profit_percentage': takeProfitPercentage,
      'default_risk_level': defaultRiskLevel,
      'trading_hours_start': tradingHoursStart,
      'trading_hours_end': tradingHoursEnd,
      'additional_rules': additionalRules,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  @override
  List<Object?> get props => [
        configId,
        accountId,
        configName,
        maxOrderSize,
        maxPositionSize,
        maxDailyTrades,
        maxDailyVolume,
        maxLossPerTrade,
        maxTotalExposure,
        stopLossPercentage,
        takeProfitPercentage,
        defaultRiskLevel,
        tradingHoursStart,
        tradingHoursEnd,
        additionalRules,
        createdAt,
        updatedAt,
      ];
}
