import 'package:json_annotation/json_annotation.dart';

part 'model_performance_models.g.dart';

// Model Performance Summary
@JsonSerializable()
class ModelPerformanceSummary {
  final String modelId;
  final String status;
  final ModelMetrics latestMetrics;
  final ModelTrends? trends;
  final String lastUpdated;
  final List<String> tags;

  const ModelPerformanceSummary({
    required this.modelId,
    required this.status,
    required this.latestMetrics,
    this.trends,
    required this.lastUpdated,
    this.tags = const [],
  });

  factory ModelPerformanceSummary.fromJson(Map<String, dynamic> json) =>
      _$ModelPerformanceSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$ModelPerformanceSummaryToJson(this);

  ModelPerformanceSummary copyWith({
    String? modelId,
    String? status,
    ModelMetrics? latestMetrics,
    ModelTrends? trends,
    String? lastUpdated,
    List<String>? tags,
  }) {
    return ModelPerformanceSummary(
      modelId: modelId ?? this.modelId,
      status: status ?? this.status,
      latestMetrics: latestMetrics ?? this.latestMetrics,
      trends: trends ?? this.trends,
      lastUpdated: lastUpdated ?? this.lastUpdated,
      tags: tags ?? this.tags,
    );
  }
}

// Model Metrics
@JsonSerializable()
class ModelMetrics {
  @JsonKey(name: 'accuracy')
  final double accuracy;
  
  @JsonKey(name: 'precision')
  final double precision;
  
  @JsonKey(name: 'recall')
  final double recall;
  
  @JsonKey(name: 'f1Score')
  final double f1Score;
  
  @JsonKey(name: 'aucScore')
  final double aucScore;
  
  @JsonKey(name: 'predictionLatencyMs')
  final double predictionLatencyMs;
  
  @JsonKey(name: 'throughputPredictionsPerSecond')
  final double throughputPredictionsPerSecond;
  
  @JsonKey(name: 'dataDriftScore')
  final double dataDriftScore;
  
  @JsonKey(name: 'conceptDriftScore')
  final double conceptDriftScore;
  
  @JsonKey(name: 'predictionConfidenceAvg')
  final double predictionConfidenceAvg;
  
  @JsonKey(name: 'errorRate')
  final double errorRate;
  
  @JsonKey(name: 'memoryUsageMb')
  final double memoryUsageMb;
  
  @JsonKey(name: 'cpuUsagePercent')
  final double cpuUsagePercent;

  const ModelMetrics({
    required this.accuracy,
    required this.precision,
    required this.recall,
    required this.f1Score,
    required this.aucScore,
    required this.predictionLatencyMs,
    required this.throughputPredictionsPerSecond,
    required this.dataDriftScore,
    required this.conceptDriftScore,
    required this.predictionConfidenceAvg,
    required this.errorRate,
    required this.memoryUsageMb,
    required this.cpuUsagePercent,
  });

  factory ModelMetrics.fromJson(Map<String, dynamic> json) =>
      _$ModelMetricsFromJson(json);

  Map<String, dynamic> toJson() => _$ModelMetricsToJson(this);

  ModelMetrics copyWith({
    double? accuracy,
    double? precision,
    double? recall,
    double? f1Score,
    double? aucScore,
    double? predictionLatencyMs,
    double? throughputPredictionsPerSecond,
    double? dataDriftScore,
    double? conceptDriftScore,
    double? predictionConfidenceAvg,
    double? errorRate,
    double? memoryUsageMb,
    double? cpuUsagePercent,
  }) {
    return ModelMetrics(
      accuracy: accuracy ?? this.accuracy,
      precision: precision ?? this.precision,
      recall: recall ?? this.recall,
      f1Score: f1Score ?? this.f1Score,
      aucScore: aucScore ?? this.aucScore,
      predictionLatencyMs: predictionLatencyMs ?? this.predictionLatencyMs,
      throughputPredictionsPerSecond: throughputPredictionsPerSecond ?? this.throughputPredictionsPerSecond,
      dataDriftScore: dataDriftScore ?? this.dataDriftScore,
      conceptDriftScore: conceptDriftScore ?? this.conceptDriftScore,
      predictionConfidenceAvg: predictionConfidenceAvg ?? this.predictionConfidenceAvg,
      errorRate: errorRate ?? this.errorRate,
      memoryUsageMb: memoryUsageMb ?? this.memoryUsageMb,
      cpuUsagePercent: cpuUsagePercent ?? this.cpuUsagePercent,
    );
  }
}

// Model Trends
@JsonSerializable()
class ModelTrends {
  @JsonKey(name: 'accuracyTrend')
  final String accuracyTrend;
  
  @JsonKey(name: 'latencyTrend')
  final String latencyTrend;

  const ModelTrends({
    required this.accuracyTrend,
    required this.latencyTrend,
  });

  factory ModelTrends.fromJson(Map<String, dynamic> json) =>
      _$ModelTrendsFromJson(json);

  Map<String, dynamic> toJson() => _$ModelTrendsToJson(this);
}

// Model Alert
@JsonSerializable()
class ModelAlert {
  @JsonKey(name: 'alertId')
  final String alertId;
  
  @JsonKey(name: 'modelId')
  final String modelId;
  
  @JsonKey(name: 'level')
  final String level;
  
  @JsonKey(name: 'title')
  final String title;
  
  @JsonKey(name: 'message')
  final String message;
  
  @JsonKey(name: 'metricName')
  final String metricName;
  
  @JsonKey(name: 'currentValue')
  final double currentValue;
  
  @JsonKey(name: 'thresholdValue')
  final double thresholdValue;
  
  @JsonKey(name: 'timestamp')
  final DateTime timestamp;
  
  @JsonKey(name: 'acknowledged')
  final bool acknowledged;
  
  @JsonKey(name: 'resolved')
  final bool resolved;
  
  @JsonKey(name: 'metadata')
  final Map<String, dynamic> metadata;

  const ModelAlert({
    required this.alertId,
    required this.modelId,
    required this.level,
    required this.title,
    required this.message,
    required this.metricName,
    required this.currentValue,
    required this.thresholdValue,
    required this.timestamp,
    this.acknowledged = false,
    this.resolved = false,
    this.metadata = const {},
  });

  factory ModelAlert.fromJson(Map<String, dynamic> json) =>
      _$ModelAlertFromJson(json);

  Map<String, dynamic> toJson() => _$ModelAlertToJson(this);

  ModelAlert copyWith({
    String? alertId,
    String? modelId,
    String? level,
    String? title,
    String? message,
    String? metricName,
    double? currentValue,
    double? thresholdValue,
    DateTime? timestamp,
    bool? acknowledged,
    bool? resolved,
    Map<String, dynamic>? metadata,
  }) {
    return ModelAlert(
      alertId: alertId ?? this.alertId,
      modelId: modelId ?? this.modelId,
      level: level ?? this.level,
      title: title ?? this.title,
      message: message ?? this.message,
      metricName: metricName ?? this.metricName,
      currentValue: currentValue ?? this.currentValue,
      thresholdValue: thresholdValue ?? this.thresholdValue,
      timestamp: timestamp ?? this.timestamp,
      acknowledged: acknowledged ?? this.acknowledged,
      resolved: resolved ?? this.resolved,
      metadata: metadata ?? this.metadata,
    );
  }
}

// Model Version
@JsonSerializable()
class ModelVersion {
  @JsonKey(name: 'versionId')
  final String versionId;
  
  @JsonKey(name: 'modelId')
  final String modelId;
  
  @JsonKey(name: 'versionNumber')
  final String versionNumber;
  
  @JsonKey(name: 'creationTime')
  final DateTime creationTime;
  
  @JsonKey(name: 'accuracy')
  final double accuracy;
  
  @JsonKey(name: 'f1Score')
  final double f1Score;
  
  @JsonKey(name: 'predictionLatencyMs')
  final double predictionLatencyMs;
  
  @JsonKey(name: 'trainingDataHash')
  final String trainingDataHash;
  
  @JsonKey(name: 'modelFilePath')
  final String modelFilePath;
  
  @JsonKey(name: 'isActive')
  final bool isActive;
  
  @JsonKey(name: 'notes')
  final String notes;

  const ModelVersion({
    required this.versionId,
    required this.modelId,
    required this.versionNumber,
    required this.creationTime,
    required this.accuracy,
    required this.f1Score,
    required this.predictionLatencyMs,
    required this.trainingDataHash,
    required this.modelFilePath,
    required this.isActive,
    this.notes = '',
  });

  factory ModelVersion.fromJson(Map<String, dynamic> json) =>
      _$ModelVersionFromJson(json);

  Map<String, dynamic> toJson() => _$ModelVersionToJson(this);

  ModelVersion copyWith({
    String? versionId,
    String? modelId,
    String? versionNumber,
    DateTime? creationTime,
    double? accuracy,
    double? f1Score,
    double? predictionLatencyMs,
    String? trainingDataHash,
    String? modelFilePath,
    bool? isActive,
    String? notes,
  }) {
    return ModelVersion(
      versionId: versionId ?? this.versionId,
      modelId: modelId ?? this.modelId,
      versionNumber: versionNumber ?? this.versionNumber,
      creationTime: creationTime ?? this.creationTime,
      accuracy: accuracy ?? this.accuracy,
      f1Score: f1Score ?? this.f1Score,
      predictionLatencyMs: predictionLatencyMs ?? this.predictionLatencyMs,
      trainingDataHash: trainingDataHash ?? this.trainingDataHash,
      modelFilePath: modelFilePath ?? this.modelFilePath,
      isActive: isActive ?? this.isActive,
      notes: notes ?? this.notes,
    );
  }
}

// Retraining Request
@JsonSerializable()
class RetrainingRequest {
  @JsonKey(name: 'requestId')
  final String requestId;
  
  @JsonKey(name: 'modelId')
  final String modelId;
  
  @JsonKey(name: 'triggerType')
  final String triggerType;
  
  @JsonKey(name: 'triggerReason')
  final String triggerReason;
  
  @JsonKey(name: 'requestedBy')
  final String requestedBy;
  
  @JsonKey(name: 'priority')
  final int priority;
  
  @JsonKey(name: 'status')
  final String status;
  
  @JsonKey(name: 'createdAt')
  final DateTime createdAt;
  
  @JsonKey(name: 'progressPercent')
  final double progressPercent;
  
  @JsonKey(name: 'estimatedCompletion')
  final DateTime? estimatedCompletion;

  const RetrainingRequest({
    required this.requestId,
    required this.modelId,
    required this.triggerType,
    required this.triggerReason,
    required this.requestedBy,
    required this.priority,
    required this.status,
    required this.createdAt,
    required this.progressPercent,
    this.estimatedCompletion,
  });

  factory RetrainingRequest.fromJson(Map<String, dynamic> json) =>
      _$RetrainingRequestFromJson(json);

  Map<String, dynamic> toJson() => _$RetrainingRequestToJson(this);
}

// Performance History
@JsonSerializable()
class PerformanceHistoryPoint {
  @JsonKey(name: 'timestamp')
  final DateTime timestamp;
  
  @JsonKey(name: 'accuracy')
  final double accuracy;
  
  @JsonKey(name: 'precision')
  final double precision;
  
  @JsonKey(name: 'recall')
  final double recall;
  
  @JsonKey(name: 'f1Score')
  final double f1Score;
  
  @JsonKey(name: 'latencyMs')
  final double latencyMs;
  
  @JsonKey(name: 'errorRate')
  final double errorRate;

  const PerformanceHistoryPoint({
    required this.timestamp,
    required this.accuracy,
    required this.precision,
    required this.recall,
    required this.f1Score,
    required this.latencyMs,
    required this.errorRate,
  });

  factory PerformanceHistoryPoint.fromJson(Map<String, dynamic> json) =>
      _$PerformanceHistoryPointFromJson(json);

  Map<String, dynamic> toJson() => _$PerformanceHistoryPointToJson(this);
}

// Model Health Score
@JsonSerializable()
class ModelHealthScore {
  @JsonKey(name: 'overallScore')
  final double overallScore;
  
  @JsonKey(name: 'healthCategory')
  final String healthCategory;
  
  @JsonKey(name: 'componentScores')
  final ComponentScores componentScores;
  
  @JsonKey(name: 'recommendations')
  final List<String> recommendations;

  const ModelHealthScore({
    required this.overallScore,
    required this.healthCategory,
    required this.componentScores,
    required this.recommendations,
  });

  factory ModelHealthScore.fromJson(Map<String, dynamic> json) =>
      _$ModelHealthScoreFromJson(json);

  Map<String, dynamic> toJson() => _$ModelHealthScoreToJson(this);
}

@JsonSerializable()
class ComponentScores {
  @JsonKey(name: 'accuracyScore')
  final double accuracyScore;
  
  @JsonKey(name: 'latencyScore')
  final double latencyScore;
  
  @JsonKey(name: 'errorScore')
  final double errorScore;
  
  @JsonKey(name: 'driftScore')
  final double driftScore;

  const ComponentScores({
    required this.accuracyScore,
    required this.latencyScore,
    required this.errorScore,
    required this.driftScore,
  });

  factory ComponentScores.fromJson(Map<String, dynamic> json) =>
      _$ComponentScoresFromJson(json);

  Map<String, dynamic> toJson() => _$ComponentScoresToJson(this);
}

// Data Drift Detection Result
@JsonSerializable()
class DataDriftResult {
  @JsonKey(name: 'driftDetected')
  final bool driftDetected;
  
  @JsonKey(name: 'driftScore')
  final double driftScore;
  
  @JsonKey(name: 'features')
  final List<String> features;
  
  @JsonKey(name: 'featureDriftScores')
  final Map<String, double> featureDriftScores;
  
  @JsonKey(name: 'timestamp')
  final DateTime timestamp;

  const DataDriftResult({
    required this.driftDetected,
    required this.driftScore,
    required this.features,
    required this.featureDriftScores,
    required this.timestamp,
  });

  factory DataDriftResult.fromJson(Map<String, dynamic> json) =>
      _$DataDriftResultFromJson(json);

  Map<String, dynamic> toJson() => _$DataDriftResultToJson(this);
}

// Model Performance Monitor Stats
@JsonSerializable()
class MonitorStats {
  @JsonKey(name: 'monitoringStatus')
  final String monitoringStatus;
  
  @JsonKey(name: 'totalModels')
  final int totalModels;
  
  @JsonKey(name: 'modelStatusBreakdown')
  final Map<String, int> modelStatusBreakdown;
  
  @JsonKey(name: 'statistics')
  final MonitorStatistics statistics;

  const MonitorStats({
    required this.monitoringStatus,
    required this.totalModels,
    required this.modelStatusBreakdown,
    required this.statistics,
  });

  factory MonitorStats.fromJson(Map<String, dynamic> json) =>
      _$MonitorStatsFromJson(json);

  Map<String, dynamic> toJson() => _$MonitorStatsToJson(this);
}

@JsonSerializable()
class MonitorStatistics {
  @JsonKey(name: 'totalAlertsGenerated')
  final int totalAlertsGenerated;
  
  @JsonKey(name: 'totalRetrainingTriggers')
  final int totalRetrainingTriggers;
  
  @JsonKey(name: 'averageModelAccuracy')
  final double averageModelAccuracy;

  const MonitorStatistics({
    required this.totalAlertsGenerated,
    required this.totalRetrainingTriggers,
    required this.averageModelAccuracy,
  });

  factory MonitorStatistics.fromJson(Map<String, dynamic> json) =>
      _$MonitorStatisticsFromJson(json);

  Map<String, dynamic> toJson() => _$MonitorStatisticsToJson(this);
}

// Enums for better type safety
enum ModelStatus {
  healthy,
  degraded,
  critical,
  retraining,
  offline,
}

enum AlertLevel {
  info,
  warning,
  critical,
  emergency,
}

enum RetrainingTrigger {
  manual,
  performanceDegradation,
  dataDrift,
  scheduled,
  errorRateSpike,
  accuracyDrop,
  predictionConfidenceDrop,
}

enum RetrainingStatus {
  idle,
  preparingData,
  training,
  validating,
  deploying,
  completed,
  failed,
  cancelled,
}

enum HealthCategory {
  excellent,
  good,
  fair,
  poor,
}

enum TrendDirection {
  improving,
  declining,
  stable,
}