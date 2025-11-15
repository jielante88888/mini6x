import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/conditions_provider.dart';

/// 条件监控数据模型
class ConditionMonitorData {
  final String conditionId;
  final String conditionName;
  final String symbol;
  final ConditionType type;
  final bool isActive;
  final DateTime? lastTriggered;
  final DateTime? nextEvaluation;
  final int triggerCount;
  final double successRate;
  final Duration averageExecutionTime;
  final ConditionStatus status;
  final Map<String, dynamic> currentValue;
  final String? errorMessage;

  const ConditionMonitorData({
    required this.conditionId,
    required this.conditionName,
    required this.symbol,
    required this.type,
    this.isActive = true,
    this.lastTriggered,
    this.nextEvaluation,
    this.triggerCount = 0,
    this.successRate = 0.0,
    this.averageExecutionTime = Duration.zero,
    this.status = ConditionStatus.idle,
    required this.currentValue,
    this.errorMessage,
  });

  // 复制方法
  ConditionMonitorData copyWith({
    String? conditionId,
    String? conditionName,
    String? symbol,
    ConditionType? type,
    bool? isActive,
    DateTime? lastTriggered,
    DateTime? nextEvaluation,
    int? triggerCount,
    double? successRate,
    Duration? averageExecutionTime,
    ConditionStatus? status,
    Map<String, dynamic>? currentValue,
    String? errorMessage,
  }) {
    return ConditionMonitorData(
      conditionId: conditionId ?? this.conditionId,
      conditionName: conditionName ?? this.conditionName,
      symbol: symbol ?? this.symbol,
      type: type ?? this.type,
      isActive: isActive ?? this.isActive,
      lastTriggered: lastTriggered ?? this.lastTriggered,
      nextEvaluation: nextEvaluation ?? this.nextEvaluation,
      triggerCount: triggerCount ?? this.triggerCount,
      successRate: successRate ?? this.successRate,
      averageExecutionTime: averageExecutionTime ?? this.averageExecutionTime,
      status: status ?? this.status,
      currentValue: currentValue ?? this.currentValue,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }

  // JSON序列化
  Map<String, dynamic> toJson() {
    return {
      'condition_id': conditionId,
      'condition_name': conditionName,
      'symbol': symbol,
      'type': type.value,
      'is_active': isActive,
      'last_triggered': lastTriggered?.toIso8601String(),
      'next_evaluation': nextEvaluation?.toIso8601String(),
      'trigger_count': triggerCount,
      'success_rate': successRate,
      'average_execution_time': averageExecutionTime.inMilliseconds,
      'status': status.value,
      'current_value': currentValue,
      'error_message': errorMessage,
    };
  }

  // JSON反序列化
  factory ConditionMonitorData.fromJson(Map<String, dynamic> json) {
    return ConditionMonitorData(
      conditionId: json['condition_id'],
      conditionName: json['condition_name'],
      symbol: json['symbol'],
      type: ConditionType.values.firstWhere(
        (t) => t.value == json['type'],
      ),
      isActive: json['is_active'],
      lastTriggered: json['last_triggered'] != null 
          ? DateTime.parse(json['last_triggered'])
          : null,
      nextEvaluation: json['next_evaluation'] != null 
          ? DateTime.parse(json['next_evaluation'])
          : null,
      triggerCount: json['trigger_count'],
      successRate: (json['success_rate'] as num).toDouble(),
      averageExecutionTime: Duration(milliseconds: json['average_execution_time']),
      status: ConditionStatus.values.firstWhere(
        (s) => s.value == json['status'],
      ),
      currentValue: Map<String, dynamic>.from(json['current_value'] ?? {}),
      errorMessage: json['error_message'],
    );
  }
}

/// 条件状态
enum ConditionStatus {
  idle('idle', '空闲'),
  evaluating('evaluating', '评估中'),
  triggered('triggered', '已触发'),
  error('error', '错误'),
  disabled('disabled', '已禁用');

  const ConditionStatus(this.value, this.displayName);
  final String value;
  final String displayName;
}

/// 条件监控状态
class ConditionMonitorState {
  final List<ConditionMonitorData> conditions;
  final Map<String, ConditionStatus> statusMap;
  final Map<String, int> triggerCounts;
  final bool isLoading;
  final String? error;
  final DateTime lastUpdate;
  final int totalTriggers;
  final double overallSuccessRate;

  const ConditionMonitorState({
    this.conditions = const [],
    this.statusMap = const {},
    this.triggerCounts = const {},
    this.isLoading = false,
    this.error,
    this.lastUpdate = const DateTime.fromMillisecondsSinceEpoch(0),
    this.totalTriggers = 0,
    this.overallSuccessRate = 0.0,
  });

  ConditionMonitorState copyWith({
    List<ConditionMonitorData>? conditions,
    Map<String, ConditionStatus>? statusMap,
    Map<String, int>? triggerCounts,
    bool? isLoading,
    String? error,
    DateTime? lastUpdate,
    int? totalTriggers,
    double? overallSuccessRate,
  }) {
    return ConditionMonitorState(
      conditions: conditions ?? this.conditions,
      statusMap: statusMap ?? this.statusMap,
      triggerCounts: triggerCounts ?? this.triggerCounts,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      lastUpdate: lastUpdate ?? this.lastUpdate,
      totalTriggers: totalTriggers ?? this.totalTriggers,
      overallSuccessRate: overallSuccessRate ?? this.overallSuccessRate,
    );
  }
}

/// 条件监控管理Provider
class ConditionMonitorNotifier extends StateNotifier<ConditionMonitorState> {
  ConditionMonitorNotifier() : super(const ConditionMonitorState()) {
    _initializeMockData();
    _startMonitoring();
  }

  // 初始化模拟数据
  void _initializeMockData() {
    final now = DateTime.now();
    final mockConditions = [
      ConditionMonitorData(
        conditionId: 'cond-001',
        conditionName: 'BTC价格突破',
        symbol: 'BTC/USDT',
        type: ConditionType.price,
        isActive: true,
        lastTriggered: now.subtract(const Duration(minutes: 15)),
        nextEvaluation: now.add(const Duration(seconds: 30)),
        triggerCount: 5,
        successRate: 0.95,
        averageExecutionTime: const Duration(milliseconds: 150),
        status: ConditionStatus.idle,
        currentValue: {'price': 50234.50, 'threshold': 50000.00},
      ),
      ConditionMonitorData(
        conditionId: 'cond-002',
        conditionName: 'ETH成交量异常',
        symbol: 'ETH/USDT',
        type: ConditionType.volume,
        isActive: true,
        lastTriggered: now.subtract(const Duration(minutes: 45)),
        nextEvaluation: now.add(const Duration(seconds: 15)),
        triggerCount: 3,
        successRate: 0.88,
        averageExecutionTime: const Duration(milliseconds: 200),
        status: ConditionStatus.evaluating,
        currentValue: {'volume': 1250000, 'threshold': 1000000},
      ),
      ConditionMonitorData(
        conditionId: 'cond-003',
        conditionName: 'MACD金叉',
        symbol: 'BTC/USDT',
        type: ConditionType.technical,
        isActive: false,
        lastTriggered: now.subtract(const Duration(hours: 2)),
        triggerCount: 8,
        successRate: 0.75,
        averageExecutionTime: const Duration(milliseconds: 300),
        status: ConditionStatus.disabled,
        currentValue: {'macd': 0.85, 'signal': 0.78},
      ),
      ConditionMonitorData(
        conditionId: 'cond-004',
        conditionName: '时间条件预警',
        symbol: 'ALL',
        type: ConditionType.time,
        isActive: true,
        lastTriggered: now.subtract(const Duration(minutes: 5)),
        nextEvaluation: now.add(const Duration(minutes: 1)),
        triggerCount: 12,
        successRate: 1.0,
        averageExecutionTime: const Duration(milliseconds: 50),
        status: ConditionStatus.idle,
        currentValue: {'current_time': now.toIso8601String(), 'target_time': '15:30:00'},
      ),
    ];

    final statusMap = {
      'cond-001': ConditionStatus.idle,
      'cond-002': ConditionStatus.evaluating,
      'cond-003': ConditionStatus.disabled,
      'cond-004': ConditionStatus.idle,
    };

    final triggerCounts = {
      'cond-001': 5,
      'cond-002': 3,
      'cond-003': 8,
      'cond-004': 12,
    };

    state = state.copyWith(
      conditions: mockConditions,
      statusMap: statusMap,
      triggerCounts: triggerCounts,
      lastUpdate: now,
      totalTriggers: 28,
      overallSuccessRate: 0.89,
    );
  }

  // 开始监控
  void _startMonitoring() {
    // 每5秒更新一次状态
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 5));
      _updateMonitoringData();
      return true; // 持续运行
    });
  }

  // 更新监控数据
  void _updateMonitoringData() {
    final updatedConditions = state.conditions.map((condition) {
      // 模拟状态变化
      final random = DateTime.now().millisecond % 100;
      ConditionStatus newStatus;
      
      if (random < 10) {
        newStatus = ConditionStatus.evaluating;
      } else if (random < 15) {
        newStatus = ConditionStatus.triggered;
      } else {
        newStatus = ConditionStatus.idle;
      }

      return condition.copyWith(
        status: newStatus,
        nextEvaluation: DateTime.now().add(Duration(seconds: 10 + random % 30)),
      );
    }).toList();

    state = state.copyWith(
      conditions: updatedConditions,
      lastUpdate: DateTime.now(),
    );
  }

  // 切换条件激活状态
  Future<void> toggleCondition(String conditionId) async {
    final updatedConditions = state.conditions.map((condition) {
      if (condition.conditionId == conditionId) {
        return condition.copyWith(
          isActive: !condition.isActive,
          status: !condition.isActive ? ConditionStatus.idle : ConditionStatus.disabled,
        );
      }
      return condition;
    }).toList();

    state = state.copyWith(
      conditions: updatedConditions,
      lastUpdate: DateTime.now(),
    );
  }

  // 重置条件统计
  void resetConditionStatistics(String conditionId) {
    final updatedConditions = state.conditions.map((condition) {
      if (condition.conditionId == conditionId) {
        return condition.copyWith(
          triggerCount: 0,
          successRate: 0.0,
        );
      }
      return condition;
    }).toList();

    state = state.copyWith(
      conditions: updatedConditions,
      lastUpdate: DateTime.now(),
    );
  }

  // 获取统计信息
  Map<String, dynamic> getStatistics() {
    final activeConditions = state.conditions.where((c) => c.isActive).length;
    final totalConditions = state.conditions.length;
    final evaluatingConditions = state.conditions.where((c) => c.status == ConditionStatus.evaluating).length;
    final triggeredConditions = state.conditions.where((c) => c.status == ConditionStatus.triggered).length;
    final errorConditions = state.conditions.where((c) => c.status == ConditionStatus.error).length;

    return {
      'total_conditions': totalConditions,
      'active_conditions': activeConditions,
      'evaluating_conditions': evaluatingConditions,
      'triggered_conditions': triggeredConditions,
      'error_conditions': errorConditions,
      'total_triggers': state.totalTriggers,
      'overall_success_rate': state.overallSuccessRate,
      'last_update': state.lastUpdate,
    };
  }

  // 按状态分组条件
  Map<ConditionStatus, List<ConditionMonitorData>> getConditionsByStatus() {
    final Map<ConditionStatus, List<ConditionMonitorData>> grouped = {};
    for (final condition in state.conditions) {
      grouped.putIfAbsent(condition.status, () => []).add(condition);
    }
    return grouped;
  }

  // 获取类型统计
  Map<ConditionType, int> getConditionTypeStats() {
    final Map<ConditionType, int> stats = {};
    for (final condition in state.conditions) {
      stats[condition.type] = (stats[condition.type] ?? 0) + 1;
    }
    return stats;
  }

  // 获取最近触发历史
  List<ConditionMonitorData> getRecentTriggeredConditions() {
    return state.conditions
        .where((c) => c.lastTriggered != null)
        .toList()
      ..sort((a, b) => b.lastTriggered!.compareTo(a.lastTriggered!));
  }

  // 清除错误
  void clearError() {
    state = state.copyWith(error: null);
  }
}

// Provider实例
final conditionMonitorProvider = StateNotifierProvider<ConditionMonitorNotifier, ConditionMonitorState>(
  (ref) => ConditionMonitorNotifier(),
);

// 条件统计Provider
final conditionStatisticsProvider = Provider<Map<String, dynamic>>((ref) {
  final notifier = ref.read(conditionMonitorProvider.notifier);
  return notifier.getStatistics();
});

// 按状态分组的条件Provider
final conditionsByStatusProvider = Provider<Map<ConditionStatus, List<ConditionMonitorData>>>((ref) {
  final monitorState = ref.watch(conditionMonitorProvider);
  return monitorState.conditions.fold<Map<ConditionStatus, List<ConditionMonitorData>>>({}, (grouped, condition) {
    grouped.putIfAbsent(condition.status, () => []).add(condition);
    return grouped;
  });
});

// 类型统计Provider
final conditionTypeStatsProvider = Provider<Map<ConditionType, int>>((ref) {
  final notifier = ref.read(conditionMonitorProvider.notifier);
  return notifier.getConditionTypeStats();
});

// 最近触发的条件Provider
final recentTriggeredConditionsProvider = Provider<List<ConditionMonitorData>>((ref) {
  final notifier = ref.read(conditionMonitorProvider.notifier);
  return notifier.getRecentTriggeredConditions();
});
