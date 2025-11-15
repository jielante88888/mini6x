import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';

/// 策略类型
enum StrategyType {
  grid('grid', '网格策略'),
  martingale('martingale', '马丁格尔策略'),
  arbitrage('arbitrage', '套利策略');

  const StrategyType(this.value, this.displayName);
  final String value;
  final String displayName;
}

/// 策略状态
enum StrategyStatus {
  inactive('inactive', '未启动'),
  running('running', '运行中'),
  paused('paused', '已暂停'),
  stopped('stopped', '已停止'),
  error('error', '错误');

  const StrategyStatus(this.value, this.displayName);
  final String value;
  final String displayName;
}

/// 策略配置模型
class StrategyConfig {
  final String id;
  final String name;
  final StrategyType type;
  final String symbol;
  final String exchange;
  final double baseQuantity;
  final double minOrderSize;
  final double maxOrderSize;
  final double profitTarget;
  final double stopLoss;
  final bool isActive;
  final StrategyStatus status;
  final DateTime createdAt;
  final DateTime? updatedAt;
  
  // 网格策略特定参数
  final int? gridLevels;
  final double? gridSpacing;
  
  // 马丁格尔策略特定参数
  final double? martingaleMultiplier;
  final int? maxMartingaleSteps;
  
  // 套利策略特定参数
  final double? arbitrageThreshold;
  final List<String>? targetExchanges;

  StrategyConfig({
    required this.id,
    required this.name,
    required this.type,
    required this.symbol,
    required this.exchange,
    required this.baseQuantity,
    required this.minOrderSize,
    required this.maxOrderSize,
    required this.profitTarget,
    required this.stopLoss,
    required this.isActive,
    required this.status,
    required this.createdAt,
    this.updatedAt,
    this.gridLevels,
    this.gridSpacing,
    this.martingaleMultiplier,
    this.maxMartingaleSteps,
    this.arbitrageThreshold,
    this.targetExchanges,
  });

  factory StrategyConfig.fromJson(Map<String, dynamic> json) {
    return StrategyConfig(
      id: json['id'],
      name: json['name'],
      type: StrategyType.values.firstWhere(
        (e) => e.value == json['type'],
        orElse: () => StrategyType.grid,
      ),
      symbol: json['symbol'],
      exchange: json['exchange'],
      baseQuantity: (json['base_quantity'] as num).toDouble(),
      minOrderSize: (json['min_order_size'] as num).toDouble(),
      maxOrderSize: (json['max_order_size'] as num).toDouble(),
      profitTarget: (json['profit_target'] as num).toDouble(),
      stopLoss: (json['stop_loss'] as num).toDouble(),
      isActive: json['is_active'] ?? true,
      status: StrategyStatus.values.firstWhere(
        (e) => e.value == json['status'],
        orElse: () => StrategyStatus.inactive,
      ),
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null 
        ? DateTime.parse(json['updated_at']) 
        : null,
      gridLevels: json['grid_levels'],
      gridSpacing: json['grid_spacing']?.toDouble(),
      martingaleMultiplier: json['martingale_multiplier']?.toDouble(),
      maxMartingaleSteps: json['max_martingale_steps'],
      arbitrageThreshold: json['arbitrage_threshold']?.toDouble(),
      targetExchanges: json['target_exchanges'] != null 
        ? List<String>.from(json['target_exchanges']) 
        : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'type': type.value,
      'symbol': symbol,
      'exchange': exchange,
      'base_quantity': baseQuantity,
      'min_order_size': minOrderSize,
      'max_order_size': maxOrderSize,
      'profit_target': profitTarget,
      'stop_loss': stopLoss,
      'is_active': isActive,
      'status': status.value,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'grid_levels': gridLevels,
      'grid_spacing': gridSpacing,
      'martingale_multiplier': martingaleMultiplier,
      'max_martingale_steps': maxMartingaleSteps,
      'arbitrage_threshold': arbitrageThreshold,
      'target_exchanges': targetExchanges,
    };
  }

  StrategyConfig copyWith({
    String? id,
    String? name,
    StrategyType? type,
    String? symbol,
    String? exchange,
    double? baseQuantity,
    double? minOrderSize,
    double? maxOrderSize,
    double? profitTarget,
    double? stopLoss,
    bool? isActive,
    StrategyStatus? status,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? gridLevels,
    double? gridSpacing,
    double? martingaleMultiplier,
    int? maxMartingaleSteps,
    double? arbitrageThreshold,
    List<String>? targetExchanges,
  }) {
    return StrategyConfig(
      id: id ?? this.id,
      name: name ?? this.name,
      type: type ?? this.type,
      symbol: symbol ?? this.symbol,
      exchange: exchange ?? this.exchange,
      baseQuantity: baseQuantity ?? this.baseQuantity,
      minOrderSize: minOrderSize ?? this.minOrderSize,
      maxOrderSize: maxOrderSize ?? this.maxOrderSize,
      profitTarget: profitTarget ?? this.profitTarget,
      stopLoss: stopLoss ?? this.stopLoss,
      isActive: isActive ?? this.isActive,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      gridLevels: gridLevels ?? this.gridLevels,
      gridSpacing: gridSpacing ?? this.gridSpacing,
      martingaleMultiplier: martingaleMultiplier ?? this.martingaleMultiplier,
      maxMartingaleSteps: maxMartingaleSteps ?? this.maxMartingaleSteps,
      arbitrageThreshold: arbitrageThreshold ?? this.arbitrageThreshold,
      targetExchanges: targetExchanges ?? this.targetExchanges,
    );
  }
}

/// 策略性能数据
class StrategyPerformance {
  final String strategyId;
  final double totalPnL;
  final double totalCommission;
  final double netPnL;
  final double winRate;
  final double profitFactor;
  final double maxDrawdown;
  final double currentDrawdown;
  final double sharpeRatio;
  final double sortinoRatio;
  final double totalReturns;
  final int totalTrades;
  final DateTime lastUpdated;

  StrategyPerformance({
    required this.strategyId,
    required this.totalPnL,
    required this.totalCommission,
    required this.netPnL,
    required this.winRate,
    required this.profitFactor,
    required this.maxDrawdown,
    required this.currentDrawdown,
    required this.sharpeRatio,
    required this.sortinoRatio,
    required this.totalReturns,
    required this.totalTrades,
    required this.lastUpdated,
  });

  factory StrategyPerformance.fromJson(Map<String, dynamic> json) {
    return StrategyPerformance(
      strategyId: json['strategy_id'],
      totalPnL: (json['total_pnl'] as num).toDouble(),
      totalCommission: (json['total_commission'] as num).toDouble(),
      netPnL: (json['net_pnl'] as num).toDouble(),
      winRate: (json['win_rate'] as num).toDouble(),
      profitFactor: (json['profit_factor'] as num).toDouble(),
      maxDrawdown: (json['max_drawdown'] as num).toDouble(),
      currentDrawdown: (json['current_drawdown'] as num).toDouble(),
      sharpeRatio: (json['sharpe_ratio'] as num).toDouble(),
      sortinoRatio: (json['sortino_ratio'] as num).toDouble(),
      totalReturns: (json['total_returns'] as num).toDouble(),
      totalTrades: json['total_trades'],
      lastUpdated: DateTime.parse(json['last_updated']),
    );
  }
}

/// API响应状态
enum ApiState { initial, loading, success, error }

/// 策略Provider状态
class StrategyState {
  final List<StrategyConfig> strategies;
  final Map<String, StrategyPerformance> performanceData;
  final ApiState apiState;
  final String? error;

  StrategyState({
    this.strategies = const [],
    this.performanceData = const {},
    this.apiState = ApiState.initial,
    this.error,
  });

  StrategyState copyWith({
    List<StrategyConfig>? strategies,
    Map<String, StrategyPerformance>? performanceData,
    ApiState? apiState,
    String? error,
  }) {
    return StrategyState(
      strategies: strategies ?? this.strategies,
      performanceData: performanceData ?? this.performanceData,
      apiState: apiState ?? this.apiState,
      error: error,
    );
  }
}

/// 策略Provider
@riverpod
class StrategyNotifier extends StateNotifier<StrategyState> {
  static const String _baseUrl = 'http://localhost:8000/api';
  
  StrategyNotifier() : super(StrategyState()) {
    _loadStrategies();
  }

  /// 加载策略列表
  Future<void> _loadStrategies() async {
    state = state.copyWith(apiState: ApiState.loading);
    
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/strategies'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        final strategies = data.map((json) => StrategyConfig.fromJson(json)).toList();
        
        // 加载性能数据
        await _loadPerformanceData(strategies.map((s) => s.id).toList());
        
        state = state.copyWith(
          strategies: strategies,
          apiState: ApiState.success,
        );
      } else {
        throw Exception('Failed to load strategies: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        apiState: ApiState.error,
        error: e.toString(),
      );
    }
  }

  /// 加载策略性能数据
  Future<void> _loadPerformanceData(List<String> strategyIds) async {
    final performanceData = <String, StrategyPerformance>{};
    
    for (final id in strategyIds) {
      try {
        final response = await http.get(
          Uri.parse('$_baseUrl/strategies/$id/performance'),
          headers: {'Content-Type': 'application/json'},
        );

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          performanceData[id] = StrategyPerformance.fromJson(data);
        }
      } catch (e) {
        // 忽略单个策略的性能加载失败
        debugPrint('Failed to load performance for strategy $id: $e');
      }
    }
    
    state = state.copyWith(performanceData: performanceData);
  }

  /// 创建新策略
  Future<bool> createStrategy(StrategyConfig config) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/strategies'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(config.toJson()),
      );

      if (response.statusCode == 201) {
        // 重新加载策略列表
        await _loadStrategies();
        return true;
      } else {
        throw Exception('Failed to create strategy: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        apiState: ApiState.error,
        error: e.toString(),
      );
      return false;
    }
  }

  /// 更新策略
  Future<bool> updateStrategy(String id, StrategyConfig config) async {
    try {
      final response = await http.put(
        Uri.parse('$_baseUrl/strategies/$id'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(config.toJson()),
      );

      if (response.statusCode == 200) {
        // 重新加载策略列表
        await _loadStrategies();
        return true;
      } else {
        throw Exception('Failed to update strategy: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        apiState: ApiState.error,
        error: e.toString(),
      );
      return false;
    }
  }

  /// 删除策略
  Future<bool> deleteStrategy(String id) async {
    try {
      final response = await http.delete(
        Uri.parse('$_baseUrl/strategies/$id'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        // 重新加载策略列表
        await _loadStrategies();
        return true;
      } else {
        throw Exception('Failed to delete strategy: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        apiState: ApiState.error,
        error: e.toString(),
      );
      return false;
    }
  }

  /// 启动策略
  Future<bool> startStrategy(String id) async {
    return await _updateStrategyStatus(id, StrategyStatus.running);
  }

  /// 暂停策略
  Future<bool> pauseStrategy(String id) async {
    return await _updateStrategyStatus(id, StrategyStatus.paused);
  }

  /// 停止策略
  Future<bool> stopStrategy(String id) async {
    return await _updateStrategyStatus(id, StrategyStatus.stopped);
  }

  /// 更新策略状态
  Future<bool> _updateStrategyStatus(String id, StrategyStatus status) async {
    try {
      final response = await http.patch(
        Uri.parse('$_baseUrl/strategies/$id/status'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'status': status.value}),
      );

      if (response.statusCode == 200) {
        // 更新本地状态
        final updatedStrategies = state.strategies.map((strategy) {
          if (strategy.id == id) {
            return strategy.copyWith(status: status);
          }
          return strategy;
        }).toList();
        
        state = state.copyWith(strategies: updatedStrategies);
        return true;
      } else {
        throw Exception('Failed to update strategy status: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        apiState: ApiState.error,
        error: e.toString(),
      );
      return false;
    }
  }

  /// 刷新策略列表
  Future<void> refreshStrategies() async {
    await _loadStrategies();
  }

  /// 获取策略性能
  StrategyPerformance? getStrategyPerformance(String strategyId) {
    return state.performanceData[strategyId];
  }

  /// 获取活跃策略
  List<StrategyConfig> getActiveStrategies() {
    return state.strategies.where((s) => s.isActive).toList();
  }

  /// 获取策略配置表单的数据验证
  static Map<String, String> validateConfig(StrategyConfig config) {
    final errors = <String, String>{};

    if (config.name.trim().isEmpty) {
      errors['name'] = '策略名称不能为空';
    }

    if (config.baseQuantity <= 0) {
      errors['baseQuantity'] = '基础数量必须大于0';
    }

    if (config.minOrderSize <= 0) {
      errors['minOrderSize'] = '最小订单大小必须大于0';
    }

    if (config.maxOrderSize <= 0) {
      errors['maxOrderSize'] = '最大订单大小必须大于0';
    }

    if (config.minOrderSize > config.maxOrderSize) {
      errors['orderSize'] = '最小订单大小不能大于最大订单大小';
    }

    if (config.profitTarget <= 0) {
      errors['profitTarget'] = '盈利目标必须大于0';
    }

    if (config.stopLoss < 0) {
      errors['stopLoss'] = '止损不能为负数';
    }

    // 根据策略类型验证特定参数
    switch (config.type) {
      case StrategyType.grid:
        if (config.gridLevels == null || config.gridLevels! <= 0) {
          errors['gridLevels'] = '网格层数必须大于0';
        }
        if (config.gridSpacing == null || config.gridSpacing! <= 0) {
          errors['gridSpacing'] = '网格间距必须大于0';
        }
        break;
      case StrategyType.martingale:
        if (config.martingaleMultiplier == null || config.martingaleMultiplier! <= 1.0) {
          errors['martingaleMultiplier'] = '马丁格尔倍数必须大于1';
        }
        if (config.maxMartingaleSteps == null || config.maxMartingaleSteps! <= 0) {
          errors['maxMartingaleSteps'] = '最大马丁格尔步数必须大于0';
        }
        break;
      case StrategyType.arbitrage:
        if (config.arbitrageThreshold == null || config.arbitrageThreshold! <= 0) {
          errors['arbitrageThreshold'] = '套利阈值必须大于0';
        }
        break;
    }

    return errors;
  }
}

/// Provider实例
final strategyProvider = StateNotifierProvider<StrategyNotifier, StrategyState>((ref) {
  return StrategyNotifier();
});

/// 获取活跃策略的Provider
final activeStrategiesProvider = Provider<List<StrategyConfig>>((ref) {
  final strategyState = ref.watch(strategyProvider);
  return strategyState.strategies.where((s) => s.isActive).toList();
});

/// 获取策略性能的Provider
final strategyPerformanceProvider = Provider.family<StrategyPerformance?, String>((ref, strategyId) {
  final strategyState = ref.watch(strategyProvider);
  return strategyState.performanceData[strategyId];
});