import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

// 条件类型枚举
enum ConditionType {
  price('price', '价格条件'),
  volume('volume', '成交量条件'),
  time('time', '时间条件'),
  technical('technical', '技术指标条件'),
  market('market', '市场预警条件');

  const ConditionType(this.value, this.displayName);
  final String value;
  final String displayName;
}

// 条件运算符枚举
enum ConditionOperator {
  greaterThan('>', '大于'),
  lessThan('<', '小于'),
  equal('==', '等于'),
  greaterEqual('>=', '大于等于'),
  lessEqual('<=', '小于等于'),
  notEqual('!=', '不等于');

  const ConditionOperator(this.value, this.displayName);
  final String value;
  final String displayName;
}

// 优先级枚举
enum ConditionPriority {
  low(1, '低优先级', 'ℹ️'),
  normal(2, '正常', '✅'),
  high(3, '高优先级', '⚠️'),
  urgent(4, '紧急', '🔴'),
  critical(5, '严重', '🆘');

  const ConditionPriority(this.value, this.displayName, this.emoji);
  final int value;
  final String displayName;
  final String emoji;
}

// 条件状态
enum ConditionStatus {
  enabled('enabled', '启用'),
  disabled('disabled', '禁用'),
  triggered('triggered', '已触发');

  const ConditionStatus(this.value, this.displayName);
  final String value;
  final String displayName;
}

// 条件模型
class Condition {
  final String id;
  final String name;
  final String? description;
  final ConditionType type;
  final ConditionOperator operator;
  final dynamic value;
  final String symbol;
  final bool enabled;
  final int priority;
  final ConditionStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? lastTriggered;
  final int triggerCount;
  final Map<String, dynamic> metadata;

  const Condition({
    required this.id,
    required this.name,
    this.description,
    required this.type,
    required this.operator,
    required this.value,
    required this.symbol,
    this.enabled = true,
    this.priority = 2,
    this.status = ConditionStatus.enabled,
    required this.createdAt,
    required this.updatedAt,
    this.lastTriggered,
    this.triggerCount = 0,
    this.metadata = const {},
  });

  // 工厂构造函数
  factory Condition.create({
    required String name,
    String? description,
    required ConditionType type,
    required ConditionOperator operator,
    required dynamic value,
    required String symbol,
    int priority = 2,
    Map<String, dynamic> metadata = const {},
  }) {
    final now = DateTime.now();
    return Condition(
      id: const Uuid().v4(),
      name: name,
      description: description,
      type: type,
      operator: operator,
      value: value,
      symbol: symbol,
      enabled: true,
      priority: priority,
      status: ConditionStatus.enabled,
      createdAt: now,
      updatedAt: now,
      lastTriggered: null,
      triggerCount: 0,
      metadata: metadata,
    );
  }

  // 复制方法
  Condition copyWith({
    String? id,
    String? name,
    String? description,
    ConditionType? type,
    ConditionOperator? operator,
    dynamic value,
    String? symbol,
    bool? enabled,
    int? priority,
    ConditionStatus? status,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? lastTriggered,
    int? triggerCount,
    Map<String, dynamic>? metadata,
  }) {
    return Condition(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      type: type ?? this.type,
      operator: operator ?? this.operator,
      value: value ?? this.value,
      symbol: symbol ?? this.symbol,
      enabled: enabled ?? this.enabled,
      priority: priority ?? this.priority,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      lastTriggered: lastTriggered ?? this.lastTriggered,
      triggerCount: triggerCount ?? this.triggerCount,
      metadata: metadata ?? this.metadata,
    );
  }

  // 转换为JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'type': type.value,
      'operator': operator.value,
      'value': value,
      'symbol': symbol,
      'enabled': enabled,
      'priority': priority,
      'status': status.value,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'lastTriggered': lastTriggered?.toIso8601String(),
      'triggerCount': triggerCount,
      'metadata': metadata,
    };
  }

  // 从JSON创建
  factory Condition.fromJson(Map<String, dynamic> json) {
    return Condition(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      type: ConditionType.values.firstWhere((t) => t.value == json['type']),
      operator: ConditionOperator.values.firstWhere((o) => o.value == json['operator']),
      value: json['value'],
      symbol: json['symbol'],
      enabled: json['enabled'],
      priority: json['priority'],
      status: ConditionStatus.values.firstWhere((s) => s.value == json['status']),
      createdAt: DateTime.parse(json['createdAt']),
      updatedAt: DateTime.parse(json['updatedAt']),
      lastTriggered: json['lastTriggered'] != null ? DateTime.parse(json['lastTriggered']) : null,
      triggerCount: json['triggerCount'],
      metadata: Map<String, dynamic>.from(json['metadata'] ?? {}),
    );
  }

  // 格式化显示值
  String get formattedValue {
    if (type == ConditionType.price || type == ConditionType.volume) {
      if (value is num) {
        if (type == ConditionType.price) {
          return '\$${value.toStringAsFixed(2)}';
        } else {
          final num valueNum = value as num;
          if (valueNum >= 1000000) {
            return '${(valueNum / 1000000).toStringAsFixed(1)}M';
          } else if (valueNum >= 1000) {
            return '${(valueNum / 1000).toStringAsFixed(1)}K';
          } else {
            return valueNum.toString();
          }
        }
      }
    }
    return value.toString();
  }

  // 获取优先级显示
  String get priorityDisplay {
    return ConditionPriority.values
        .firstWhere((p) => p.value == priority)
        .displayName;
  }

  // 获取优先级emoji
  String get priorityEmoji {
    return ConditionPriority.values
        .firstWhere((p) => p.value == priority)
        .emoji;
  }
}

// 条件通知配置
class ConditionNotification {
  final bool enabled;
  final List<String> channels; // popup, desktop, telegram, email
  final String template;
  final Map<String, dynamic> templateVariables;

  const ConditionNotification({
    this.enabled = true,
    this.channels = const [],
    this.template = 'default',
    this.templateVariables = const {},
  });

  ConditionNotification copyWith({
    bool? enabled,
    List<String>? channels,
    String? template,
    Map<String, dynamic>? templateVariables,
  }) {
    return ConditionNotification(
      enabled: enabled ?? this.enabled,
      channels: channels ?? this.channels,
      template: template ?? this.template,
      templateVariables: templateVariables ?? this.templateVariables,
    );
  }
}

// 条件Provider状态
class ConditionsState {
  final List<Condition> conditions;
  final bool isLoading;
  final String? error;
  final Map<String, ConditionNotification> notificationConfigs;

  const ConditionsState({
    this.conditions = const [],
    this.isLoading = false,
    this.error,
    this.notificationConfigs = const {},
  });

  ConditionsState copyWith({
    List<Condition>? conditions,
    bool? isLoading,
    String? error,
    Map<String, ConditionNotification>? notificationConfigs,
  }) {
    return ConditionsState(
      conditions: conditions ?? this.conditions,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      notificationConfigs: notificationConfigs ?? this.notificationConfigs,
    );
  }
}

// 条件管理Provider
class ConditionsNotifier extends StateNotifier<ConditionsState> {
  ConditionsNotifier() : super(const ConditionsState()) {
    _loadConditions();
  }

  // 加载条件
  Future<void> _loadConditions() async {
    state = state.copyWith(isLoading: true);
    try {
      // TODO: 从后端API加载条件
      // 这里先使用模拟数据
      await Future.delayed(const Duration(milliseconds: 500));
      
      final mockConditions = <Condition>[
        Condition.create(
          name: 'BTC价格预警',
          description: '当BTC价格超过70000时发送通知',
          type: ConditionType.price,
          operator: ConditionOperator.greaterThan,
          value: 70000,
          symbol: 'BTC/USDT',
          priority: 3,
        ),
        Condition.create(
          name: 'ETH成交量异常',
          description: 'ETH成交量突然增加时发送通知',
          type: ConditionType.volume,
          operator: ConditionOperator.greaterThan,
          value: 1000000,
          symbol: 'ETH/USDT',
          priority: 2,
        ),
      ];

      state = state.copyWith(
        conditions: mockConditions,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 添加条件
  Future<void> addCondition(Condition condition) async {
    state = state.copyWith(isLoading: true);
    try {
      // TODO: 保存到后端API
      await Future.delayed(const Duration(milliseconds: 300));
      
      state = state.copyWith(
        conditions: [...state.conditions, condition],
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 更新条件
  Future<void> updateCondition(Condition updatedCondition) async {
    state = state.copyWith(isLoading: true);
    try {
      // TODO: 更新后端API
      await Future.delayed(const Duration(milliseconds: 300));
      
      final updatedConditions = state.conditions.map((condition) {
        return condition.id == updatedCondition.id ? updatedCondition : condition;
      }).toList();
      
      state = state.copyWith(
        conditions: updatedConditions,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 删除条件
  Future<void> deleteCondition(String conditionId) async {
    state = state.copyWith(isLoading: true);
    try {
      // TODO: 删除后端API
      await Future.delayed(const Duration(milliseconds: 300));
      
      final updatedConditions = state.conditions
          .where((condition) => condition.id != conditionId)
          .toList();
      
      state = state.copyWith(
        conditions: updatedConditions,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 切换条件启用状态
  Future<void> toggleCondition(String conditionId) async {
    final condition = state.conditions.firstWhere((c) => c.id == conditionId);
    final updatedCondition = condition.copyWith(
      enabled: !condition.enabled,
      status: !condition.enabled ? ConditionStatus.enabled : ConditionStatus.disabled,
      updatedAt: DateTime.now(),
    );
    
    await updateCondition(updatedCondition);
  }

  // 获取条件统计
  Map<String, int> getConditionStatistics() {
    return {
      'total': state.conditions.length,
      'enabled': state.conditions.where((c) => c.enabled).length,
      'disabled': state.conditions.where((c) => !c.enabled).length,
      'triggered': state.conditions.where((c) => c.triggerCount > 0).length,
    };
  }

  // 按类型分组条件
  Map<ConditionType, List<Condition>> getConditionsByType() {
    final Map<ConditionType, List<Condition>> grouped = {};
    for (final condition in state.conditions) {
      grouped.putIfAbsent(condition.type, () => []).add(condition);
    }
    return grouped;
  }

  // 清除错误
  void clearError() {
    state = state.copyWith(error: null);
  }
}

// Provider实例
final conditionsProvider = StateNotifierProvider<ConditionsNotifier, ConditionsState>(
  (ref) => ConditionsNotifier(),
);

// 条件过滤Provider
final conditionsFilterProvider = StateProvider<String>((ref) => '');

// 条件排序Provider
final conditionsSortProvider = StateProvider<String>((ref) => 'created_desc');

// 过滤后的条件Provider
final filteredConditionsProvider = Provider<List<Condition>>((ref) {
  final conditionsState = ref.watch(conditionsProvider);
  final filter = ref.watch(conditionsFilterProvider);
  final sort = ref.watch(conditionsSortProvider);
  
  List<Condition> filtered = conditionsState.conditions;
  
  // 应用过滤
  if (filter.isNotEmpty) {
    final filterLower = filter.toLowerCase();
    filtered = filtered.where((condition) {
      return condition.name.toLowerCase().contains(filterLower) ||
             condition.description?.toLowerCase().contains(filterLower) == true ||
             condition.symbol.toLowerCase().contains(filterLower);
    }).toList();
  }
  
  // 应用排序
  switch (sort) {
    case 'name_asc':
      filtered.sort((a, b) => a.name.compareTo(b.name));
      break;
    case 'priority_desc':
      filtered.sort((a, b) => b.priority.compareTo(a.priority));
      break;
    case 'triggered_desc':
      filtered.sort((a, b) => b.triggerCount.compareTo(a.triggerCount));
      break;
    case 'created_desc':
    default:
      filtered.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      break;
  }
  
  return filtered;
});
