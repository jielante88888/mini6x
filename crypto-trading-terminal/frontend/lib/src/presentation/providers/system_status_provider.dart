import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 交易所状态枚举
enum ExchangeStatus {
  connected,
  disconnected,
  reconnecting,
  error,
  maintenance
}

/// 市场数据类型
enum MarketType {
  spot,
  futures
}

/// 系统状态数据类
class SystemStatusData {
  final ExchangeStatus binanceStatus;
  final ExchangeStatus okxStatus;
  final MarketType activeMarketType;
  final String activeExchange;
  final DateTime? lastUpdate;
  final int? binanceLatency;
  final int? okxLatency;
  final String? errorMessage;
  final bool failoverActive;
  final DateTime? failoverTime;
  
  const SystemStatusData({
    required this.binanceStatus,
    required this.okxStatus,
    required this.activeMarketType,
    required this.activeExchange,
    this.lastUpdate,
    this.binanceLatency,
    this.okxLatency,
    this.errorMessage,
    this.failoverActive = false,
    this.failoverTime,
  });

  /// 获取币安状态颜色
  String get binanceStatusColor {
    switch (binanceStatus) {
      case ExchangeStatus.connected:
        return '#4CAF50'; // 绿色
      case ExchangeStatus.reconnecting:
        return '#FF9800'; // 橙色
      case ExchangeStatus.disconnected:
        return '#F44336'; // 红色
      case ExchangeStatus.error:
        return '#E91E63'; // 粉红色
      case ExchangeStatus.maintenance:
        return '#9C27B0'; // 紫色
    }
  }

  /// 获取OKX状态颜色
  String get okxStatusColor {
    switch (okxStatus) {
      case ExchangeStatus.connected:
        return '#4CAF50'; // 绿色
      case ExchangeStatus.reconnecting:
        return '#FF9800'; // 橙色
      case ExchangeStatus.disconnected:
        return '#F44336'; // 红色
      case ExchangeStatus.error:
        return '#E91E63'; // 粉红色
      case ExchangeStatus.maintenance:
        return '#9C27B0'; // 紫色
    }
  }

  /// 获取币安状态描述
  String get binanceStatusDescription {
    switch (binanceStatus) {
      case ExchangeStatus.connected:
        return '连接正常';
      case ExchangeStatus.reconnecting:
        return '重连中';
      case ExchangeStatus.disconnected:
        return '连接断开';
      case ExchangeStatus.error:
        return '连接错误';
      case ExchangeStatus.maintenance:
        return '维护中';
    }
  }

  /// 获取OKX状态描述
  String get okxStatusDescription {
    switch (okxStatus) {
      case ExchangeStatus.connected:
        return '连接正常';
      case ExchangeStatus.reconnecting:
        return '重连中';
      case ExchangeStatus.disconnected:
        return '连接断开';
      case ExchangeStatus.error:
        return '连接错误';
      case ExchangeStatus.maintenance:
        return '维护中';
    }
  }

  /// 获取总体状态颜色
  String get overallStatusColor {
    final allConnected = binanceStatus == ExchangeStatus.connected && 
                         okxStatus == ExchangeStatus.connected;
    final anyConnected = binanceStatus == ExchangeStatus.connected || 
                        okxStatus == ExchangeStatus.connected;
    
    if (allConnected) {
      return '#4CAF50'; // 绿色 - 所有连接正常
    } else if (anyConnected) {
      return '#FF9800'; // 橙色 - 部分连接正常
    } else {
      return '#F44336'; // 红色 - 所有连接断开
    }
  }

  /// 获取总体状态描述
  String get overallStatusDescription {
    final allConnected = binanceStatus == ExchangeStatus.connected && 
                         okxStatus == ExchangeStatus.connected;
    final anyConnected = binanceStatus == ExchangeStatus.connected || 
                        okxStatus == ExchangeStatus.connected;
    
    if (allConnected) {
      return '系统正常';
    } else if (anyConnected) {
      return '部分可用';
    } else {
      return '系统异常';
    }
  }

  /// 是否显示警告状态
  bool get hasWarning {
    return binanceStatus != ExchangeStatus.connected || 
           okxStatus != ExchangeStatus.connected ||
           failoverActive;
  }

  /// 获取主要活跃交易所
  String get primaryExchange {
    if (binanceStatus == ExchangeStatus.connected) return 'binance';
    if (okxStatus == ExchangeStatus.connected) return 'okx';
    return 'none';
  }

  SystemStatusData copyWith({
    ExchangeStatus? binanceStatus,
    ExchangeStatus? okxStatus,
    MarketType? activeMarketType,
    String? activeExchange,
    DateTime? lastUpdate,
    int? binanceLatency,
    int? okxLatency,
    String? errorMessage,
    bool? failoverActive,
    DateTime? failoverTime,
  }) {
    return SystemStatusData(
      binanceStatus: binanceStatus ?? this.binanceStatus,
      okxStatus: okxStatus ?? this.okxStatus,
      activeMarketType: activeMarketType ?? this.activeMarketType,
      activeExchange: activeExchange ?? this.activeExchange,
      lastUpdate: lastUpdate ?? this.lastUpdate,
      binanceLatency: binanceLatency ?? this.binanceLatency,
      okxLatency: okxLatency ?? this.okxLatency,
      errorMessage: errorMessage ?? this.errorMessage,
      failoverActive: failoverActive ?? this.failoverActive,
      failoverTime: failoverTime ?? this.failoverTime,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'binanceStatus': binanceStatus.name,
      'okxStatus': okxStatus.name,
      'activeMarketType': activeMarketType.name,
      'activeExchange': activeExchange,
      'lastUpdate': lastUpdate?.toIso8601String(),
      'binanceLatency': binanceLatency,
      'okxLatency': okxLatency,
      'errorMessage': errorMessage,
      'failoverActive': failoverActive,
      'failoverTime': failoverTime?.toIso8601String(),
    };
  }

  factory SystemStatusData.fromJson(Map<String, dynamic> json) {
    return SystemStatusData(
      binanceStatus: ExchangeStatus.values.firstWhere(
        (e) => e.name == json['binanceStatus'],
        orElse: () => ExchangeStatus.disconnected,
      ),
      okxStatus: ExchangeStatus.values.firstWhere(
        (e) => e.name == json['okxStatus'],
        orElse: () => ExchangeStatus.disconnected,
      ),
      activeMarketType: MarketType.values.firstWhere(
        (e) => e.name == json['activeMarketType'],
        orElse: () => MarketType.spot,
      ),
      activeExchange: json['activeExchange'] ?? 'binance',
      lastUpdate: json['lastUpdate'] != null 
          ? DateTime.parse(json['lastUpdate']) 
          : null,
      binanceLatency: json['binanceLatency'],
      okxLatency: json['okxLatency'],
      errorMessage: json['errorMessage'],
      failoverActive: json['failoverActive'] ?? false,
      failoverTime: json['failoverTime'] != null 
          ? DateTime.parse(json['failoverTime']) 
          : null,
    );
  }
}

/// 系统状态通知器
class SystemStatusNotifier extends StateNotifier<SystemStatusData> {
  Timer? _statusCheckTimer;
  Timer? _reconnectTimer;
  final Duration _statusCheckInterval = const Duration(seconds: 10);
  final Duration _reconnectInterval = const Duration(seconds: 30);

  SystemStatusNotifier() 
      : super(const SystemStatusData(
          binanceStatus: ExchangeStatus.disconnected,
          okxStatus: ExchangeStatus.disconnected,
          activeMarketType: MarketType.spot,
          activeExchange: 'binance',
        )) {
    _initializeStatusMonitoring();
  }

  /// 初始化状态监控
  void _initializeStatusMonitoring() {
    // 模拟初始状态检查
    _checkExchangeStatus();
    
    // 启动定期状态检查
    _statusCheckTimer = Timer.periodic(_statusCheckInterval, (_) {
      _checkExchangeStatus();
    });
  }

  /// 检查交易所状态
  void _checkExchangeStatus() {
    // 模拟API调用检查状态
    _simulateStatusCheck();
  }

  /// 模拟状态检查
  void _simulateStatusCheck() {
    // 这里应该调用真实的API来检查状态
    // 为了演示目的，我们使用模拟数据
    final now = DateTime.now();
    
    // 模拟随机状态变化
    final binanceStatus = _generateRandomStatus(state.binanceStatus);
    final okxStatus = _generateRandomStatus(state.okxStatus);
    
    // 模拟延迟数据
    final binanceLatency = binanceStatus == ExchangeStatus.connected 
        ? _generateRandomLatency() 
        : null;
    final okxLatency = okxStatus == ExchangeStatus.connected 
        ? _generateRandomLatency() 
        : null;

    state = state.copyWith(
      binanceStatus: binanceStatus,
      okxStatus: okxStatus,
      lastUpdate: now,
      binanceLatency: binanceLatency,
      okxLatency: okxLatency,
    );

    // 如果有交易所断开，尝试重连
    if (binanceStatus == ExchangeStatus.disconnected || 
        okxStatus == ExchangeStatus.disconnected) {
      _attemptReconnection();
    }
  }

  /// 生成随机状态
  ExchangeStatus _generateRandomStatus(ExchangeStatus currentStatus) {
    // 90%概率保持当前状态，10%概率发生变化
    if (DateTime.now().millisecond % 10 == 0) {
      final statuses = ExchangeStatus.values;
      return statuses[DateTime.now().millisecond % statuses.length];
    }
    return currentStatus;
  }

  /// 生成随机延迟
  int _generateRandomLatency() {
    return 50 + (DateTime.now().millisecond % 200); // 50-250ms
  }

  /// 尝试重连
  void _attemptReconnection() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(_reconnectInterval, () {
      if (state.binanceStatus == ExchangeStatus.disconnected) {
        state = state.copyWith(binanceStatus: ExchangeStatus.reconnecting);
        
        // 模拟重连过程
        Timer(const Duration(seconds: 3), () {
          if (DateTime.now().millisecond % 3 == 0) {
            // 模拟重连成功
            state = state.copyWith(
              binanceStatus: ExchangeStatus.connected,
              lastUpdate: DateTime.now(),
            );
          } else {
            // 模拟重连失败
            state = state.copyWith(
              binanceStatus: ExchangeStatus.disconnected,
              errorMessage: '重连失败，请检查网络连接',
            );
          }
        });
      }

      if (state.okxStatus == ExchangeStatus.disconnected) {
        state = state.copyWith(okxStatus: ExchangeStatus.reconnecting);
        
        // 模拟重连过程
        Timer(const Duration(seconds: 5), () {
          if (DateTime.now().millisecond % 4 == 0) {
            // 模拟重连成功
            state = state.copyWith(
              okxStatus: ExchangeStatus.connected,
              lastUpdate: DateTime.now(),
            );
          } else {
            // 模拟重连失败
            state = state.copyWith(
              okxStatus: ExchangeStatus.disconnected,
              errorMessage: 'OKX重连失败，请稍后重试',
            );
          }
        });
      }
    });
  }

  /// 手动重连指定交易所
  void reconnectExchange(String exchange) {
    if (exchange.toLowerCase() == 'binance') {
      state = state.copyWith(
        binanceStatus: ExchangeStatus.reconnecting,
        errorMessage: null,
      );
      
      Timer(const Duration(seconds: 2), () {
        state = state.copyWith(
          binanceStatus: ExchangeStatus.connected,
          lastUpdate: DateTime.now(),
          binanceLatency: _generateRandomLatency(),
        );
      });
    } else if (exchange.toLowerCase() == 'okx') {
      state = state.copyWith(
        okxStatus: ExchangeStatus.reconnecting,
        errorMessage: null,
      );
      
      Timer(const Duration(seconds: 3), () {
        state = state.copyWith(
          okxStatus: ExchangeStatus.connected,
          lastUpdate: DateTime.now(),
          okxLatency: _generateRandomLatency(),
        );
      });
    }
  }

  /// 设置活跃市场类型
  void setActiveMarketType(MarketType marketType) {
    state = state.copyWith(activeMarketType: marketType);
  }

  /// 设置活跃交易所
  void setActiveExchange(String exchange) {
    state = state.copyWith(activeExchange: exchange);
  }

  /// 清除错误消息
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }

  /// 获取状态摘要
  String getStatusSummary() {
    final connectedCount = [
      state.binanceStatus == ExchangeStatus.connected,
      state.okxStatus == ExchangeStatus.connected,
    ].where((status) => status).length;

    return '$connectedCount/2 交易所连接正常';
  }

  /// 检查是否需要显示通知
  bool shouldShowNotification() {
    return state.hasWarning && state.errorMessage != null;
  }

  @override
  void dispose() {
    _statusCheckTimer?.cancel();
    _reconnectTimer?.cancel();
    super.dispose();
  }
}

/// 系统状态提供者
final systemStatusProvider = 
    StateNotifierProvider<SystemStatusNotifier, SystemStatusData>((ref) {
  return SystemStatusNotifier();
});

/// 币安状态提供者
final binanceStatusProvider = Provider<ExchangeStatus>((ref) {
  return ref.watch(systemStatusProvider).binanceStatus;
});

/// OKX状态提供者
final okxStatusProvider = Provider<ExchangeStatus>((ref) {
  return ref.watch(systemStatusProvider).okxStatus;
});

/// 系统状态摘要提供者
final systemStatusSummaryProvider = Provider<String>((ref) {
  return ref.watch(systemStatusProvider).getStatusSummary();
});

/// 是否显示状态通知提供者
final shouldShowStatusNotificationProvider = Provider<bool>((ref) {
  return ref.watch(systemStatusProvider).shouldShowNotification();
});