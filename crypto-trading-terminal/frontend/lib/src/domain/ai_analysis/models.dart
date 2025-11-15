import 'package:json_annotation/json_annotation.dart';

part 'models.g.dart';

/// 市场趋势方向枚举
enum TrendDirection {
  @JsonValue('strong_bullish')
  strongBullish,
  @JsonValue('bullish')
  bullish,
  @JsonValue('neutral')
  neutral,
  @JsonValue('bearish')
  bearish,
  @JsonValue('strong_bearish')
  strongBearish,
}

/// 市场状态枚举
enum MarketRegime {
  @JsonValue('bull_market')
  bullMarket,
  @JsonValue('bear_market')
  bearMarket,
  @JsonValue('sideways')
  sideways,
  @JsonValue('high_volatility')
  highVolatility,
  @JsonValue('low_volatility')
  lowVolatility,
}

/// 信号类型枚举
enum SignalType {
  @JsonValue('buy')
  buy,
  @JsonValue('sell')
  sell,
  @JsonValue('hold')
  hold,
  @JsonValue('weak_buy')
  weakBuy,
  @JsonValue('weak_sell')
  weakSell,
}

/// 信号强度枚举
enum SignalStrength {
  @JsonValue('very_strong')
  veryStrong,
  @JsonValue('strong')
  strong,
  @JsonValue('moderate')
  moderate,
  @JsonValue('weak')
  weak,
  @JsonValue('very_weak')
  veryWeak,
}

/// 信号质量枚举
enum SignalQuality {
  @JsonValue('excellent')
  excellent,
  @JsonValue('good')
  good,
  @JsonValue('fair')
  fair,
  @JsonValue('poor')
  poor,
  @JsonValue('invalid')
  invalid,
}

/// 洞察类型枚举
enum InsightType {
  @JsonValue('market_trend')
  marketTrend,
  @JsonValue('trading_signal')
  tradingSignal,
  @JsonValue('risk_alert')
  riskAlert,
  @JsonValue('opportunity')
  opportunity,
  @JsonValue('performance')
  performance,
  @JsonValue('strategy')
  strategy,
  @JsonValue('system')
  system,
}

/// 洞察优先级枚举
enum InsightPriority {
  @JsonValue('critical')
  critical,
  @JsonValue('high')
  high,
  @JsonValue('medium')
  medium,
  @JsonValue('low')
  low,
  @JsonValue('info')
  info,
}

/// 市场分析洞察数据
@JsonSerializable()
class MarketInsight {
  final String symbol;
  final TrendDirection trendDirection;
  @JsonKey(fromJson: _doubleFromString)
  final double confidence;
  final List<String> keyFactors;
  final Map<String, dynamic> prediction;
  final DateTime timestamp;
  final String timeframe;
  final MarketRegime regime;

  const MarketInsight({
    required this.symbol,
    required this.trendDirection,
    required this.confidence,
    required this.keyFactors,
    required this.prediction,
    required this.timestamp,
    required this.timeframe,
    required this.regime,
  });

  factory MarketInsight.fromJson(Map<String, dynamic> json) =>
      _$MarketInsightFromJson(json);

  Map<String, dynamic> toJson() => _$MarketInsightToJson(this);
}

/// 信号分析洞察数据
@JsonSerializable()
class SignalInsight {
  final String symbol;
  final SignalType primarySignal;
  final SignalStrength signalStrength;
  final SignalQuality quality;
  @JsonKey(fromJson: _doubleFromString)
  final double confidence;
  final List<String> supportingIndicators;
  final List<String> conflictingIndicators;
  final Map<String, double> entryPoints;
  final Map<String, double> exitPoints;
  final List<String> riskFactors;
  final DateTime timestamp;
  final String timeframe;

  const SignalInsight({
    required this.symbol,
    required this.primarySignal,
    required this.signalStrength,
    required this.quality,
    required this.confidence,
    required this.supportingIndicators,
    required this.conflictingIndicators,
    required this.entryPoints,
    required this.exitPoints,
    required this.riskFactors,
    required this.timestamp,
    required this.timeframe,
  });

  factory SignalInsight.fromJson(Map<String, dynamic> json) =>
      _$SignalInsightFromJson(json);

  Map<String, dynamic> toJson() => _$SignalInsightToJson(this);
}

/// AI洞察数据
@JsonSerializable()
class AIInsight {
  final String insightId;
  final InsightType insightType;
  final InsightPriority priority;
  final String title;
  final String description;
  final String summary;
  final List<String> recommendations;
  final Map<String, dynamic> supportingData;
  @JsonKey(fromJson: _doubleFromString)
  final double confidence;
  final DateTime timestamp;
  final String entityId;
  final DateTime? expiresAt;
  final List<String> tags;

  const AIInsight({
    required this.insightId,
    required this.insightType,
    required this.priority,
    required this.title,
    required this.description,
    required this.summary,
    required this.recommendations,
    required this.supportingData,
    required this.confidence,
    required this.timestamp,
    required this.entityId,
    this.expiresAt,
    required this.tags,
  });

  factory AIInsight.fromJson(Map<String, dynamic> json) =>
      _$AIInsightFromJson(json);

  Map<String, dynamic> toJson() => _$AIInsightToJson(this);
}

/// 性能数据点
@JsonSerializable()
class PerformanceDataPoint {
  final DateTime timestamp;
  @JsonKey(fromJson: _doubleFromString)
  final double confidence;

  const PerformanceDataPoint({
    required this.timestamp,
    required this.confidence,
  });

  factory PerformanceDataPoint.fromJson(Map<String, dynamic> json) =>
      _$PerformanceDataPointFromJson(json);

  Map<String, dynamic> toJson() => _$PerformanceDataPointToJson(this);
}

/// 综合AI分析结果
@JsonSerializable()
class AIAnalysis {
  final String symbol;
  final MarketInsight marketInsight;
  final SignalInsight signalInsight;
  final List<AIInsight> insights;
  final DateTime timestamp;
  final List<PerformanceDataPoint>? performanceData;

  const AIAnalysis({
    required this.symbol,
    required this.marketInsight,
    required this.signalInsight,
    required this.insights,
    required this.timestamp,
    this.performanceData,
  });

  factory AIAnalysis.fromJson(Map<String, dynamic> json) =>
      _$AIAnalysisFromJson(json);

  Map<String, dynamic> toJson() => _$AIAnalysisToJson(this);
}

/// 分析引擎状态
enum AnalysisStatus {
  stopped,
  running,
  paused,
  error,
}

/// 分析配置
@JsonSerializable()
class AnalysisConfig {
  final int analysisIntervalSeconds;
  final int maxConcurrentAnalyses;
  final bool enableRealTime;
  final bool enableInsights;
  final int cacheExpiryMinutes;
  final bool performanceTrackingEnabled;
  final Map<String, double> alertThresholds;

  const AnalysisConfig({
    required this.analysisIntervalSeconds,
    required this.maxConcurrentAnalyses,
    required this.enableRealTime,
    required this.enableInsights,
    required this.cacheExpiryMinutes,
    required this.performanceTrackingEnabled,
    required this.alertThresholds,
  });

  factory AnalysisConfig.fromJson(Map<String, dynamic> json) =>
      _$AnalysisConfigFromJson(json);

  Map<String, dynamic> toJson() => _$AnalysisConfigToJson(this);
}

/// 分析引擎统计信息
@JsonSerializable()
class AnalysisStats {
  final int totalAnalyses;
  final int successfulAnalyses;
  final int failedAnalyses;
  @JsonKey(fromJson: _doubleFromString)
  final double averageConfidence;
  final DateTime? lastAnalysisTime;
  @JsonKey(fromJson: _doubleFromString)
  final double averageProcessingTime;

  const AnalysisStats({
    required this.totalAnalyses,
    required this.successfulAnalyses,
    required this.failedAnalyses,
    required this.averageConfidence,
    this.lastAnalysisTime,
    required this.averageProcessingTime,
  });

  factory AnalysisStats.fromJson(Map<String, dynamic> json) =>
      _$AnalysisStatsFromJson(json);

  Map<String, dynamic> toJson() => _$AnalysisStatsToJson(this);
}

/// 分析引擎信息
@JsonSerializable()
class AnalysisEngineInfo {
  final String status;
  final bool isRealTimeEnabled;
  final AnalysisStats stats;
  final Map<String, dynamic> cacheInfo;

  const AnalysisEngineInfo({
    required this.status,
    required this.isRealTimeEnabled,
    required this.stats,
    required this.cacheInfo,
  });

  factory AnalysisEngineInfo.fromJson(Map<String, dynamic> json) =>
      _$AnalysisEngineInfoFromJson(json);

  Map<String, dynamic> toJson() => _$AnalysisEngineInfoToJson(this);
}

/// JSON转换辅助函数
double _doubleFromString(dynamic value) {
  if (value is num) {
    return value.toDouble();
  } else if (value is String) {
    return double.tryParse(value) ?? 0.0;
  }
  return 0.0;
}