import 'dart:async';
import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 失败类型枚举
enum FailureType {
  networkTimeout,      // 网络超时
  serverError,         // 服务器错误
  rateLimit,          // 频率限制
  authentication,     // 认证失败
  serviceMaintenance, // 服务维护
  unknown            // 未知错误
}

/// 重连策略枚举
enum ReconnectionStrategy {
  immediate,          // 立即重连
  exponential,        // 指数退避
  linear,            // 线性退避
  jitter,            // 抖动退避
  adaptive           // 自适应重连
}

/// 重连状态枚举
enum ReconnectionState {
  idle,              // 空闲
  attempting,        // 尝试重连
  scheduled,         // 计划重连
  backoff,          // 退避重连
  success,          // 重连成功
  failed            // 重连失败
}

/// 重连配置类
class ReconnectionConfig {
  final int maxAttempts;           // 最大重连次数
  final Duration initialDelay;     // 初始延迟
  final Duration maxDelay;         // 最大延迟
  final double backoffMultiplier;  // 退避倍数
  final bool useJitter;           // 是否使用抖动
  final Duration timeout;         // 超时时间
  
  const ReconnectionConfig({
    this.maxAttempts = 5,
    this.initialDelay = const Duration(seconds: 1),
    this.maxDelay = const Duration(minutes: 5),
    this.backoffMultiplier = 2.0,
    this.useJitter = true,
    this.timeout = const Duration(seconds: 30),
  });

  ReconnectionConfig copyWith({
    int? maxAttempts,
    Duration? initialDelay,
    Duration? maxDelay,
    double? backoffMultiplier,
    bool? useJitter,
    Duration? timeout,
  }) {
    return ReconnectionConfig(
      maxAttempts: maxAttempts ?? this.maxAttempts,
      initialDelay: initialDelay ?? this.initialDelay,
      maxDelay: maxDelay ?? this.maxDelay,
      backoffMultiplier: backoffMultiplier ?? this.backoffMultiplier,
      useJitter: useJitter ?? this.useJitter,
      timeout: timeout ?? this.timeout,
    );
  }
}

/// 重连记录类
class ReconnectionRecord {
  final DateTime timestamp;
  final FailureType failureType;
  final int attemptNumber;
  final Duration delay;
  final bool success;
  final String? errorMessage;
  
  const ReconnectionRecord({
    required this.timestamp,
    required this.failureType,
    required this.attemptNumber,
    required this.delay,
    required this.success,
    this.errorMessage,
  });

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'failureType': failureType.name,
      'attemptNumber': attemptNumber,
      'delay': delay.inMilliseconds,
      'success': success,
      'errorMessage': errorMessage,
    };
  }

  factory ReconnectionRecord.fromJson(Map<String, dynamic> json) {
    return ReconnectionRecord(
      timestamp: DateTime.parse(json['timestamp']),
      failureType: FailureType.values.firstWhere(
        (e) => e.name == json['failureType'],
        orElse: () => FailureType.unknown,
      ),
      attemptNumber: json['attemptNumber'],
      delay: Duration(milliseconds: json['delay']),
      success: json['success'],
      errorMessage: json['errorMessage'],
    );
  }
}

/// 重连管理器
class ReconnectionManager {
  final Map<String, Timer> _reconnectionTimers = {};
  final Map<String, List<ReconnectionRecord>> _reconnectionHistory = {};
  final Random _random = Random();
  
  /// 为指定交易所启动重连
  Future<bool> startReconnection(
    String exchange,
    FailureType failureType, {
    ReconnectionConfig? config,
  }) async {
    final defaultConfig = _getConfigForFailureType(failureType);
    final finalConfig = config ?? defaultConfig;
    
    // 清理旧的重连尝试
    _cancelReconnection(exchange);
    
    // 开始重连过程
    return _attemptReconnection(exchange, failureType, 1, finalConfig);
  }
  
  /// 取消重连
  void cancelReconnection(String exchange) {
    _cancelReconnection(exchange);
  }
  
  /// 获取重连历史
  List<ReconnectionRecord> getReconnectionHistory(String exchange) {
    return _reconnectionHistory[exchange] ?? [];
  }
  
  /// 获取重连统计
  ReconnectionStatistics getStatistics(String exchange) {
    final history = getReconnectionHistory(exchange);
    final now = DateTime.now();
    final last24Hours = history.where(
      (record) => now.difference(record.timestamp).inHours < 24
    ).toList();
    
    final totalAttempts = history.length;
    final successfulAttempts = history.where((record) => record.success).length;
    final failedAttempts = totalAttempts - successfulAttempts;
    
    final averageDelay = last24Hours.isNotEmpty
        ? last24Hours.fold<Duration>(
            Duration.zero,
            (sum, record) => sum + record.delay,
          ) ~/ last24Hours.length
        : Duration.zero;
    
    final lastAttempt = history.isNotEmpty ? history.last : null;
    
    return ReconnectionStatistics(
      totalAttempts: totalAttempts,
      successfulAttempts: successfulAttempts,
      failedAttempts: failedAttempts,
      successRate: totalAttempts > 0 ? successfulAttempts / totalAttempts : 0.0,
      averageDelay: averageDelay,
      lastAttempt: lastAttempt,
      recentAttempts: last24Hours.length,
    );
  }
  
  /// 根据失败类型获取默认配置
  ReconnectionConfig _getConfigForFailureType(FailureType failureType) {
    switch (failureType) {
      case FailureType.networkTimeout:
        return const ReconnectionConfig(
          maxAttempts: 3,
          initialDelay: Duration(seconds: 2),
          maxDelay: Duration(minutes: 1),
          backoffMultiplier: 2.0,
          useJitter: true,
        );
      case FailureType.serverError:
        return const ReconnectionConfig(
          maxAttempts: 5,
          initialDelay: Duration(seconds: 5),
          maxDelay: Duration(minutes: 2),
          backoffMultiplier: 1.5,
          useJitter: true,
        );
      case FailureType.rateLimit:
        return const ReconnectionConfig(
          maxAttempts: 3,
          initialDelay: Duration(seconds: 60),
          maxDelay: Duration(minutes: 10),
          backoffMultiplier: 1.2,
          useJitter: false,
        );
      case FailureType.authentication:
        return const ReconnectionConfig(
          maxAttempts: 1,
          initialDelay: Duration(seconds: 1),
          maxDelay: Duration(seconds: 1),
          backoffMultiplier: 1.0,
          useJitter: false,
        );
      case FailureType.serviceMaintenance:
        return const ReconnectionConfig(
          maxAttempts: 10,
          initialDelay: Duration(minutes: 5),
          maxDelay: Duration(minutes: 30),
          backoffMultiplier: 1.0,
          useJitter: false,
        );
      case FailureType.unknown:
        return const ReconnectionConfig(
          maxAttempts: 3,
          initialDelay: Duration(seconds: 3),
          maxDelay: Duration(minutes: 2),
          backoffMultiplier: 2.0,
          useJitter: true,
        );
    }
  }
  
  /// 执行重连尝试
  Future<bool> _attemptReconnection(
    String exchange,
    FailureType failureType,
    int attemptNumber,
    ReconnectionConfig config,
  ) async {
    if (attemptNumber > config.maxAttempts) {
      _recordReconnectionAttempt(
        exchange,
        failureType,
        attemptNumber,
        Duration.zero,
        false,
        '达到最大重连次数',
      );
      return false;
    }
    
    // 计算延迟时间
    final delay = _calculateDelay(attemptNumber, config, failureType);
    
    _recordReconnectionAttempt(
      exchange,
      failureType,
      attemptNumber,
      delay,
      true, // 标记为尝试
    );
    
    // 等待延迟
    await Future.delayed(delay);
    
    // 执行重连逻辑（模拟）
    final success = await _performReconnectionAttempt(exchange, failureType, config.timeout);
    
    if (success) {
      _recordReconnectionAttempt(
        exchange,
        failureType,
        attemptNumber,
        delay,
        true,
        null,
      );
      return true;
    } else {
      // 如果还有重试次数，计划下一次重连
      if (attemptNumber < config.maxAttempts) {
        return _attemptReconnection(exchange, failureType, attemptNumber + 1, config);
      } else {
        _recordReconnectionAttempt(
          exchange,
          failureType,
          attemptNumber,
          delay,
          false,
          '重连失败',
        );
        return false;
      }
    }
  }
  
  /// 计算延迟时间
  Duration _calculateDelay(int attemptNumber, ReconnectionConfig config, FailureType failureType) {
    // 对于认证失败，立即重连
    if (failureType == FailureType.authentication) {
      return config.initialDelay;
    }
    
    // 对于服务维护，使用固定长延迟
    if (failureType == FailureType.serviceMaintenance) {
      return config.initialDelay * attemptNumber;
    }
    
    // 对于频率限制，使用线性退避
    if (failureType == FailureType.rateLimit) {
      return config.initialDelay * attemptNumber;
    }
    
    // 默认使用指数退避
    Duration delay = config.initialDelay * pow(config.backoffMultiplier, attemptNumber - 1) as Duration;
    
    // 限制最大延迟
    if (delay > config.maxDelay) {
      delay = config.maxDelay;
    }
    
    // 添加抖动
    if (config.useJitter) {
      final jitter = Duration(milliseconds: _random.nextInt(1000));
      delay = delay + jitter;
    }
    
    return delay;
  }
  
  /// 执行实际的重连尝试
  Future<bool> _performReconnectionAttempt(String exchange, FailureType failureType, Duration timeout) async {
    try {
      // 这里应该调用实际的重连逻辑
      // 为了演示目的，我们模拟不同的成功率
      final successProbability = _getSuccessProbability(failureType);
      final success = _random.nextDouble() < successProbability;
      
      await Future.delayed(Duration(milliseconds: 100 + _random.nextInt(200)));
      
      return success;
    } catch (e) {
      return false;
    }
  }
  
  /// 获取失败类型的成功概率
  double _getSuccessProbability(FailureType failureType) {
    switch (failureType) {
      case FailureType.networkTimeout:
        return 0.8;
      case FailureType.serverError:
        return 0.6;
      case FailureType.rateLimit:
        return 0.4;
      case FailureType.authentication:
        return 0.1; // 认证问题通常需要手动解决
      case FailureType.serviceMaintenance:
        return 0.3; // 维护期间重连成功率较低
      case FailureType.unknown:
        return 0.5;
    }
  }
  
  /// 记录重连尝试
  void _recordReconnectionAttempt(
    String exchange,
    FailureType failureType,
    int attemptNumber,
    Duration delay,
    bool attempted, [
    String? errorMessage,
  ]) {
    final record = ReconnectionRecord(
      timestamp: DateTime.now(),
      failureType: failureType,
      attemptNumber: attemptNumber,
      delay: delay,
      success: attempted && errorMessage == null,
      errorMessage: errorMessage,
    );
    
    if (!_reconnectionHistory.containsKey(exchange)) {
      _reconnectionHistory[exchange] = [];
    }
    
    _reconnectionHistory[exchange]!.add(record);
    
    // 保持历史记录在合理范围内（最近100次）
    if (_reconnectionHistory[exchange]!.length > 100) {
      _reconnectionHistory[exchange] = _reconnectionHistory[exchange]!.sublist(50);
    }
  }
  
  /// 取消重连
  void _cancelReconnection(String exchange) {
    final timer = _reconnectionTimers[exchange];
    if (timer != null) {
      timer.cancel();
      _reconnectionTimers.remove(exchange);
    }
  }
}

/// 重连统计类
class ReconnectionStatistics {
  final int totalAttempts;
  final int successfulAttempts;
  final int failedAttempts;
  final double successRate;
  final Duration averageDelay;
  final ReconnectionRecord? lastAttempt;
  final int recentAttempts;
  
  const ReconnectionStatistics({
    required this.totalAttempts,
    required this.successfulAttempts,
    required this.failedAttempts,
    required this.successRate,
    required this.averageDelay,
    this.lastAttempt,
    required this.recentAttempts,
  });
}

/// 重连通知器
class ReconnectionNotifier extends StateNotifier<Map<String, ReconnectionState>> {
  final ReconnectionManager _reconnectionManager = ReconnectionManager();
  
  ReconnectionNotifier() : super({});
  
  /// 启动重连
  Future<bool> startReconnection(
    String exchange,
    FailureType failureType, {
    ReconnectionConfig? config,
  }) async {
    state = {...state, exchange: ReconnectionState.attempting};
    
    try {
      final success = await _reconnectionManager.startReconnection(
        exchange,
        failureType,
        config: config,
      );
      
      state = {
        ...state,
        exchange: success ? ReconnectionState.success : ReconnectionState.failed,
      };
      
      return success;
    } catch (e) {
      state = {...state, exchange: ReconnectionState.failed};
      return false;
    }
  }
  
  /// 取消重连
  void cancelReconnection(String exchange) {
    _reconnectionManager.cancelReconnection(exchange);
    state = {...state, exchange: ReconnectionState.idle};
  }
  
  /// 获取重连历史
  List<ReconnectionRecord> getHistory(String exchange) {
    return _reconnectionManager.getReconnectionHistory(exchange);
  }
  
  /// 获取重连统计
  ReconnectionStatistics getStatistics(String exchange) {
    return _reconnectionManager.getStatistics(exchange);
  }
  
  /// 重置重连状态
  void resetState(String exchange) {
    state = {...state, exchange: ReconnectionState.idle};
  }
}

/// 提供者
final reconnectionProvider = StateNotifierProvider<ReconnectionNotifier, Map<String, ReconnectionState>>(
  (ref) => ReconnectionNotifier(),
);

final reconnectionManagerProvider = Provider<ReconnectionManager>((ref) {
  return ReconnectionManager();
});