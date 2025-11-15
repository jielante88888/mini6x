import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/ai_analysis/model_performance_models.dart';
import '../../infrastructure/services/ai_analysis_service.dart';

// State Notifier for Model Performance
class ModelPerformanceNotifier extends StateNotifier<ModelPerformanceState> {
  ModelPerformanceNotifier(this._service) : super(const ModelPerformanceState()) {
    _initialize();
  }

  final AIAnalysisService _service;

  void _initialize() {
    // Initialize with sample data for development
    _loadSampleData();
  }

  Future<void> loadModelPerformance() async {
    try {
      state = state.copyWith(isLoading: true);
      
      // Load available models
      final models = await _service.getAvailableModels();
      state = state.copyWith(
        isLoading: false,
        availableModels: models,
      );

      // If there's a model, select it and load its performance
      if (models.isNotEmpty) {
        final firstModel = models.first['modelId'] as String;
        await selectModel(firstModel);
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load model performance: $e',
      );
    }
  }

  Future<void> selectModel(String modelId) async {
    try {
      state = state.copyWith(selectedModelId: modelId);
      
      // Load model performance data
      final performance = await _service.getModelPerformanceSummary(modelId);
      final alerts = await _service.getModelAlerts(modelId);
      final versions = await _service.getModelVersions(modelId);
      final history = await _service.getModelPerformanceHistory(modelId);
      final healthScore = await _service.getModelHealthScore(modelId);

      state = state.copyWith(
        selectedModelPerformance: performance,
        alerts: alerts,
        modelVersions: versions,
        performanceHistory: history,
        modelHealthScore: healthScore,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        error: 'Failed to load model data: $e',
      );
    }
  }

  Future<void> refreshData() async {
    if (state.selectedModelId != null) {
      await selectModel(state.selectedModelId!);
    }
  }

  Future<void> triggerRetraining(String modelId) async {
    try {
      final request = await _service.triggerModelRetraining(
        modelId,
        'manual',
        'User triggered manual retraining',
      );

      // Add to retraining requests
      final updatedRequests = [...state.retrainingRequests, request];
      state = state.copyWith(retrainingRequests: updatedRequests);

      // Refresh data
      await refreshData();
    } catch (e) {
      state = state.copyWith(error: 'Failed to trigger retraining: $e');
    }
  }

  Future<void> acknowledgeAlert(String alertId) async {
    try {
      await _service.acknowledgeAlert(alertId);
      
      // Update local state
      final updatedAlerts = state.alerts.map((alert) {
        if (alert.alertId == alertId) {
          return alert.copyWith(acknowledged: true);
        }
        return alert;
      }).toList();

      state = state.copyWith(alerts: updatedAlerts);
    } catch (e) {
      state = state.copyWith(error: 'Failed to acknowledge alert: $e');
    }
  }

  Future<void> resolveAlert(String alertId) async {
    try {
      await _service.resolveAlert(alertId);
      
      // Update local state
      final updatedAlerts = state.alerts.map((alert) {
        if (alert.alertId == alertId) {
          return alert.copyWith(
            acknowledged: true,
            resolved: true,
          );
        }
        return alert;
      }).toList();

      state = state.copyWith(alerts: updatedAlerts);
    } catch (e) {
      state = state.copyWith(error: 'Failed to resolve alert: $e');
    }
  }

  Future<void> activateVersion(String versionId) async {
    try {
      await _service.activateModelVersion(versionId);
      
      // Refresh versions
      if (state.selectedModelId != null) {
        final versions = await _service.getModelVersions(state.selectedModelId!);
        state = state.copyWith(modelVersions: versions);
      }
    } catch (e) {
      state = state.copyWith(error: 'Failed to activate version: $e');
    }
  }

  Future<void> rollbackVersion(String versionId) async {
    try {
      await _service.rollbackToVersion(versionId);
      
      // Refresh versions
      if (state.selectedModelId != null) {
        final versions = await _service.getModelVersions(state.selectedModelId!);
        state = state.copyWith(modelVersions: versions);
      }
    } catch (e) {
      state = state.copyWith(error: 'Failed to rollback version: $e');
    }
  }

  Future<void> loadRetrainingRequests() async {
    try {
      final requests = await _service.getRetrainingRequests();
      state = state.copyWith(retrainingRequests: requests);
    } catch (e) {
      state = state.copyWith(error: 'Failed to load retraining requests: $e');
    }
  }

  Future<void> cancelRetrainingRequest(String requestId) async {
    try {
      await _service.cancelRetrainingRequest(requestId);
      
      // Update local state
      final updatedRequests = state.retrainingRequests.where((req) => 
        req.requestId != requestId
      ).toList();
      
      state = state.copyWith(retrainingRequests: updatedRequests);
    } catch (e) {
      state = state.copyWith(error: 'Failed to cancel retraining: $e');
    }
  }

  Future<void> loadDataDriftAnalysis(String modelId) async {
    try {
      final driftResults = await _service.getDataDriftAnalysis(modelId);
      state = state.copyWith(dataDriftResults: driftResults);
    } catch (e) {
      state = state.copyWith(error: 'Failed to load drift analysis: $e');
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }

  void _loadSampleData() {
    // Load sample data for development
    final sampleModels = [
      {'modelId': 'price_predictor_v1', 'status': 'healthy'},
      {'modelId': 'signal_scorer_v2', 'status': 'degraded'},
      {'modelId': 'trend_analyzer_v1', 'status': 'healthy'},
    ];

    final sampleAlerts = [
      ModelAlert(
        alertId: 'alert_001',
        modelId: 'price_predictor_v1',
        level: 'warning',
        title: '模型准确率下降',
        message: '价格预测模型的准确率在过去1小时内下降了3%',
        metricName: 'accuracy',
        currentValue: 0.84,
        thresholdValue: 0.87,
        timestamp: DateTime.now().subtract(const Duration(minutes: 30)),
      ),
      ModelAlert(
        alertId: 'alert_002',
        modelId: 'signal_scorer_v2',
        level: 'critical',
        title: '预测延迟过高',
        message: '信号评分模型的预测延迟超过2秒阈值',
        metricName: 'prediction_latency',
        currentValue: 2100.0,
        thresholdValue: 2000.0,
        timestamp: DateTime.now().subtract(const Duration(minutes: 15)),
      ),
    ];

    final sampleVersions = [
      ModelVersion(
        versionId: 'price_predictor_v1_001',
        modelId: 'price_predictor_v1',
        versionNumber: 'v1.2.0',
        creationTime: DateTime.now().subtract(const Duration(days: 7)),
        accuracy: 0.87,
        f1Score: 0.85,
        predictionLatencyMs: 250.0,
        trainingDataHash: 'abc123def456',
        modelFilePath: '/models/price_predictor_v1/v1.2.0.pkl',
        isActive: true,
        notes: 'Improved accuracy on ETH data',
      ),
      ModelVersion(
        versionId: 'price_predictor_v1_000',
        modelId: 'price_predictor_v1',
        versionNumber: 'v1.1.0',
        creationTime: DateTime.now().subtract(const Duration(days: 14)),
        accuracy: 0.84,
        f1Score: 0.82,
        predictionLatencyMs: 280.0,
        trainingDataHash: 'def456ghi789',
        modelFilePath: '/models/price_predictor_v1/v1.1.0.pkl',
        isActive: false,
        notes: 'Initial release',
      ),
    ];

    final samplePerformanceHistory = List.generate(24, (index) {
      final timestamp = DateTime.now().subtract(Duration(hours: 24 - index));
      return PerformanceHistoryPoint(
        timestamp: timestamp,
        accuracy: 0.82 + (index * 0.002),
        precision: 0.80 + (index * 0.001),
        recall: 0.79 + (index * 0.001),
        f1Score: 0.81 + (index * 0.002),
        latencyMs: 300.0 - (index * 2),
        errorRate: 0.02 - (index * 0.0001),
      );
    });

    final sampleHealthScore = ModelHealthScore(
      overallScore: 0.85,
      healthCategory: 'good',
      componentScores: const ComponentScores(
        accuracyScore: 0.87,
        latencyScore: 0.90,
        errorScore: 0.85,
        driftScore: 0.80,
      ),
      recommendations: [
        '模型整体健康状况良好',
        '建议定期更新训练数据以防止概念漂移',
        '监控预测延迟，确保在500ms以内',
      ],
    );

    state = state.copyWith(
      availableModels: sampleModels,
      selectedModelId: 'price_predictor_v1',
      selectedModelPerformance: ModelPerformanceSummary(
        modelId: 'price_predictor_v1',
        status: 'healthy',
        latestMetrics: const ModelMetrics(
          accuracy: 0.87,
          precision: 0.85,
          recall: 0.83,
          f1Score: 0.85,
          aucScore: 0.89,
          predictionLatencyMs: 250.0,
          throughputPredictionsPerSecond: 150.0,
          dataDriftScore: 0.05,
          conceptDriftScore: 0.03,
          predictionConfidenceAvg: 0.82,
          errorRate: 0.015,
          memoryUsageMb: 512.0,
          cpuUsagePercent: 45.0,
        ),
        trends: const ModelTrends(
          accuracyTrend: 'improving',
          latencyTrend: 'stable',
        ),
        lastUpdated: DateTime.now().toIso8601String(),
      ),
      alerts: sampleAlerts,
      modelVersions: sampleVersions,
      performanceHistory: samplePerformanceHistory,
      modelHealthScore: sampleHealthScore,
    );
  }
}

// Provider for the Model Performance state
final modelPerformanceProvider = 
    StateNotifierProvider<ModelPerformanceNotifier, ModelPerformanceState>(
  (ref) => ModelPerformanceNotifier(AIAnalysisService()),
);

// State class for Model Performance
class ModelPerformanceState {
  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> availableModels;
  final String? selectedModelId;
  final ModelPerformanceSummary? selectedModelPerformance;
  final List<ModelAlert> alerts;
  final List<ModelVersion> modelVersions;
  final List<PerformanceHistoryPoint> performanceHistory;
  final ModelHealthScore? modelHealthScore;
  final List<RetrainingRequest> retrainingRequests;
  final List<DataDriftResult> dataDriftResults;
  final MonitorStats? monitorStats;

  const ModelPerformanceState({
    this.isLoading = false,
    this.error,
    this.availableModels = const [],
    this.selectedModelId,
    this.selectedModelPerformance,
    this.alerts = const [],
    this.modelVersions = const [],
    this.performanceHistory = const [],
    this.modelHealthScore,
    this.retrainingRequests = const [],
    this.dataDriftResults = const [],
    this.monitorStats,
  });

  ModelPerformanceState copyWith({
    bool? isLoading,
    String? error,
    List<Map<String, dynamic>>? availableModels,
    String? selectedModelId,
    ModelPerformanceSummary? selectedModelPerformance,
    List<ModelAlert>? alerts,
    List<ModelVersion>? modelVersions,
    List<PerformanceHistoryPoint>? performanceHistory,
    ModelHealthScore? modelHealthScore,
    List<RetrainingRequest>? retrainingRequests,
    List<DataDriftResult>? dataDriftResults,
    MonitorStats? monitorStats,
  }) {
    return ModelPerformanceState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      availableModels: availableModels ?? this.availableModels,
      selectedModelId: selectedModelId ?? this.selectedModelId,
      selectedModelPerformance: selectedModelPerformance ?? this.selectedModelPerformance,
      alerts: alerts ?? this.alerts,
      modelVersions: modelVersions ?? this.modelVersions,
      performanceHistory: performanceHistory ?? this.performanceHistory,
      modelHealthScore: modelHealthScore ?? this.modelHealthScore,
      retrainingRequests: retrainingRequests ?? this.retrainingRequests,
      dataDriftResults: dataDriftResults ?? this.dataDriftResults,
      monitorStats: monitorStats ?? this.monitorStats,
    );
  }

  // Computed properties
  List<ModelAlert> get unacknowledgedAlerts => 
      alerts.where((alert) => !alert.acknowledged).toList();

  List<ModelAlert> get criticalAlerts => 
      alerts.where((alert) => alert.level == 'critical').toList();

  ModelVersion? get activeVersion => 
      modelVersions.firstWhere(
        (version) => version.isActive,
        orElse: () => null as ModelVersion,
      );

  bool get hasActiveRetraining => 
      retrainingRequests.any((req) => req.status == 'training');

  String? get selectedModelStatus {
    if (selectedModelId == null) return null;
    
    final model = availableModels.firstWhere(
      (model) => model['modelId'] == selectedModelId,
      orElse: () => {},
    );
    
    return model['status'] as String?;
  }
}

// Extension for convenient data access
extension ModelPerformanceStateExtension on ModelPerformanceState {
  /// Get performance trend for a specific metric
  String getAccuracyTrend() {
    return selectedModelPerformance?.trends?.accuracyTrend ?? 'stable';
  }

  /// Get latency trend
  String getLatencyTrend() {
    return selectedModelPerformance?.trends?.latencyTrend ?? 'stable';
  }

  /// Check if model is healthy
  bool get isModelHealthy {
    return selectedModelStatus == 'healthy';
  }

  /// Get alert count by level
  Map<String, int> get alertCountByLevel {
    final Map<String, int> counts = {};
    for (final alert in alerts) {
      counts[alert.level] = (counts[alert.level] ?? 0) + 1;
    }
    return counts;
  }

  /// Get performance degradation percentage
  double getPerformanceDegradation() {
    final history = performanceHistory;
    if (history.length < 2) return 0.0;
    
    final currentAccuracy = history.last.accuracy;
    final previousAccuracy = history[history.length - 2].accuracy;
    
    return ((previousAccuracy - currentAccuracy) / previousAccuracy) * 100;
  }

  /// Get last 24 hours performance summary
  Map<String, double> get24HourPerformanceSummary {
    final recentHistory = performanceHistory.take(24).toList();
    if (recentHistory.isEmpty) return {};
    
    return {
      'avgAccuracy': recentHistory.map((p) => p.accuracy).reduce((a, b) => a + b) / recentHistory.length,
      'avgLatency': recentHistory.map((p) => p.latencyMs).reduce((a, b) => a + b) / recentHistory.length,
      'avgErrorRate': recentHistory.map((p) => p.errorRate).reduce((a, b) => a + b) / recentHistory.length,
    };
  }
}