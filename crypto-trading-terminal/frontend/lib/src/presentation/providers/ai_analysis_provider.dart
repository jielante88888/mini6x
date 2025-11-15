import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/ai_analysis/models.dart';
import '../../infrastructure/services/ai_analysis_service.dart';

/// AI分析Provider - 管理AI分析相关状态
final aiAnalysisProvider = Provider.family<AIAnalysisNotifier, String>(
  (ref, symbol) => AIAnalysisNotifier(symbol),
);

/// AI分析Notifier
class AIAnalysisNotifier extends StateNotifier<AsyncValue<AIAnalysis>> {
  final String symbol;
  Timer? _realTimeTimer;
  final AIAnalysisService _service = AIAnalysisService();

  AIAnalysisNotifier(this.symbol) : super(const AsyncValue.loading()) {
    // 初始化时加载分析数据
    loadAnalysis();
  }

  /// 加载分析数据
  Future<void> loadAnalysis() async {
    try {
      state = const AsyncValue.loading();
      
      final analysis = await _service.getAnalysis(symbol);
      state = AsyncValue.data(analysis);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  /// 开始实时更新
  void startRealTimeUpdates() {
    _stopRealTimeUpdates();
    
    _realTimeTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => loadAnalysis(),
    );
  }

  /// 停止实时更新
  void _stopRealTimeUpdates() {
    _realTimeTimer?.cancel();
    _realTimeTimer = null;
  }

  /// 切换实时更新状态
  void toggleRealTimeUpdates(bool enabled) {
    if (enabled) {
      startRealTimeUpdates();
    } else {
      _stopRealTimeUpdates();
    }
  }

  @override
  void dispose() {
    _stopRealTimeUpdates();
    super.dispose();
  }
}

/// 分析引擎Provider
final analysisEngineProvider = Provider<AnalysisEngineNotifier>(
  (ref) => AnalysisEngineNotifier(),
);

/// 分析引擎Notifier - 管理整个分析引擎的状态
class AnalysisEngineNotifier extends StateNotifier<AsyncValue<AnalysisEngineInfo>> {
  final AIAnalysisService _service = AIAnalysisService();
  Timer? _statusTimer;

  AnalysisEngineNotifier() : super(const AsyncValue.loading()) {
    // 初始化时加载引擎信息
    loadEngineInfo();
    
    // 定期更新状态
    _statusTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => loadEngineInfo(),
    );
  }

  /// 加载引擎信息
  Future<void> loadEngineInfo() async {
    try {
      final engineInfo = await _service.getEngineInfo();
      state = AsyncValue.data(engineInfo);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  /// 启动实时分析引擎
  Future<void> startAnalysisEngine() async {
    try {
      await _service.startAnalysisEngine();
      await loadEngineInfo();
    } catch (error) {
      // 处理启动失败
      rethrow;
    }
  }

  /// 停止实时分析引擎
  Future<void> stopAnalysisEngine() async {
    try {
      await _service.stopAnalysisEngine();
      await loadEngineInfo();
    } catch (error) {
      // 处理停止失败
      rethrow;
    }
  }

  /// 清除缓存
  Future<void> clearCache([String? symbol]) async {
    try {
      await _service.clearCache(symbol);
      await loadEngineInfo();
    } catch (error) {
      // 处理清除失败
      rethrow;
    }
  }

  @override
  void dispose() {
    _statusTimer?.cancel();
    super.dispose();
  }
}

/// 洞察列表Provider
final insightsProvider = FutureProvider.family<List<AIInsight>, Map<String, dynamic>>(
  (ref, params) async {
    final service = AIAnalysisService();
    final symbol = params['symbol'] as String?;
    final insightType = params['insightType'] as InsightType?;
    final limit = params['limit'] as int? ?? 50;
    
    return service.getInsights(
      symbol: symbol,
      insightType: insightType,
      limit: limit,
    );
  },
);

/// 洞察过滤Provider
final insightFilterProvider = StateProvider<Map<String, dynamic>>(
  (ref) => {
    'symbol': null,
    'insightType': null,
    'priority': null,
  },
);

/// 性能数据Provider
final performanceDataProvider = FutureProvider.family<Map<String, dynamic>, String>(
  (ref, symbol) async {
    final service = AIAnalysisService();
    return service.getPerformanceData(symbol);
  },
);

/// 分析配置Provider
final analysisConfigProvider = StateProvider<AnalysisConfig>(
  (ref) => const AnalysisConfig(
    analysisIntervalSeconds: 30,
    maxConcurrentAnalyses: 5,
    enableRealTime: true,
    enableInsights: true,
    cacheExpiryMinutes: 15,
    performanceTrackingEnabled: true,
    alertThresholds: {
      'confidence': 0.7,
      'volatility': 0.05,
      'drawdown': 0.15,
    },
  ),
);

/// 更新分析配置
final updateAnalysisConfigProvider = FutureProvider.family<bool, AnalysisConfig>(
  (ref, config) async {
    final service = AIAnalysisService();
    return service.updateConfig(config);
  },
);

/// 市场数据Provider
final marketDataProvider = FutureProvider.family<Map<String, dynamic>, String>(
  (ref, symbol) async {
    final service = AIAnalysisService();
    return service.getMarketSummary(symbol);
  },
);

/// 信号数据Provider
final signalDataProvider = FutureProvider.family<Map<String, dynamic>, String>(
  (ref, symbol) async {
    final service = AIAnalysisService();
    return service.getSignalSummary(symbol);
  },
);

/// 信号历史Provider
final signalHistoryProvider = FutureProvider.family<List<Map<String, dynamic>>, String>(
  (ref, symbol) async {
    final service = AIAnalysisService();
    return service.getSignalHistory(symbol);
  },
);