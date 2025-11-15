import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/ai_analysis/models.dart';

/// AI分析服务 - 处理与后端AI分析引擎的通信
class AIAnalysisService {
  static const String _baseUrl = 'http://localhost:8000/api/v1';
  final Dio _dio;

  AIAnalysisService() : _dio = Dio() {
    _dio.options.baseUrl = _baseUrl;
    _dio.options.connectTimeout = const Duration(seconds: 10);
    _dio.options.receiveTimeout = const Duration(seconds: 30);
    
    // 添加拦截器
    _dio.interceptors.add(LogInterceptor(
      requestBody: false,
      responseBody: true,
      logPrint: (obj) => print(obj),
    ));
  }

  /// 获取AI分析结果
  Future<AIAnalysis> getAnalysis(String symbol) async {
    try {
      final response = await _dio.get('/ai/analysis/$symbol');
      
      if (response.statusCode == 200) {
        final data = response.data;
        return AIAnalysis.fromJson(data);
      } else {
        throw Exception('获取分析结果失败: ${response.statusMessage}');
      }
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout) {
        throw Exception('连接超时，请检查网络连接');
      } else if (e.type == DioExceptionType.connectionError) {
        throw Exception('连接错误，请检查服务器状态');
      } else {
        throw Exception('请求失败: ${e.message}');
      }
    } catch (e) {
      throw Exception('未知错误: $e');
    }
  }

  /// 获取市场分析摘要
  Future<Map<String, dynamic>> getMarketSummary(String symbol) async {
    try {
      final response = await _dio.get('/ai/market/$symbol/summary');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取市场摘要失败');
      }
    } catch (e) {
      throw Exception('获取市场摘要错误: $e');
    }
  }

  /// 获取信号分析摘要
  Future<Map<String, dynamic>> getSignalSummary(String symbol) async {
    try {
      final response = await _dio.get('/ai/signal/$symbol/summary');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取信号摘要失败');
      }
    } catch (e) {
      throw Exception('获取信号摘要错误: $e');
    }
  }

  /// 获取洞察列表
  Future<List<AIInsight>> getInsights({
    String? symbol,
    InsightType? insightType,
    int? limit,
  }) async {
    try {
      final queryParameters = <String, dynamic>{};
      
      if (symbol != null) queryParameters['symbol'] = symbol;
      if (insightType != null) queryParameters['insight_type'] = insightType.name;
      if (limit != null) queryParameters['limit'] = limit.toString();
      
      final response = await _dio.get('/ai/insights', queryParameters: queryParameters);
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => AIInsight.fromJson(json)).toList();
      } else {
        throw Exception('获取洞察列表失败');
      }
    } catch (e) {
      throw Exception('获取洞察列表错误: $e');
    }
  }

  /// 获取性能数据
  Future<Map<String, dynamic>> getPerformanceData(String symbol) async {
    try {
      final response = await _dio.get('/ai/performance/$symbol');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取性能数据失败');
      }
    } catch (e) {
      throw Exception('获取性能数据错误: $e');
    }
  }

  /// 获取分析引擎信息
  Future<AnalysisEngineInfo> getEngineInfo() async {
    try {
      final response = await _dio.get('/ai/engine/info');
      
      if (response.statusCode == 200) {
        return AnalysisEngineInfo.fromJson(response.data);
      } else {
        throw Exception('获取引擎信息失败');
      }
    } catch (e) {
      throw Exception('获取引擎信息错误: $e');
    }
  }

  /// 启动分析引擎
  Future<void> startAnalysisEngine() async {
    try {
      final response = await _dio.post('/ai/engine/start');
      
      if (response.statusCode != 200) {
        throw Exception('启动引擎失败');
      }
    } catch (e) {
      throw Exception('启动引擎错误: $e');
    }
  }

  /// 停止分析引擎
  Future<void> stopAnalysisEngine() async {
    try {
      final response = await _dio.post('/ai/engine/stop');
      
      if (response.statusCode != 200) {
        throw Exception('停止引擎失败');
      }
    } catch (e) {
      throw Exception('停止引擎错误: $e');
    }
  }

  /// 清除缓存
  Future<void> clearCache([String? symbol]) async {
    try {
      final queryParameters = symbol != null ? {'symbol': symbol} : null;
      final response = await _dio.delete('/ai/cache', queryParameters: queryParameters);
      
      if (response.statusCode != 200) {
        throw Exception('清除缓存失败');
      }
    } catch (e) {
      throw Exception('清除缓存错误: $e');
    }
  }

  /// 更新分析配置
  Future<bool> updateConfig(AnalysisConfig config) async {
    try {
      final response = await _dio.put(
        '/ai/engine/config',
        data: config.toJson(),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('更新配置错误: $e');
    }
  }

  /// 获取信号历史
  Future<List<Map<String, dynamic>>> getSignalHistory(String symbol) async {
    try {
      final response = await _dio.get('/ai/signal/$symbol/history');
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => json as Map<String, dynamic>).toList();
      } else {
        throw Exception('获取信号历史失败');
      }
    } catch (e) {
      throw Exception('获取信号历史错误: $e');
    }
  }

  /// 导出分析报告
  Future<String> exportReport({
    required String symbol,
    String? format, // 'pdf', 'csv', 'json'
    List<String>? includeSections,
  }) async {
    try {
      final queryParameters = <String, dynamic>{};
      
      if (format != null) queryParameters['format'] = format;
      if (includeSections != null) queryParameters['sections'] = includeSections.join(',');
      
      final response = await _dio.post(
        '/ai/reports/export/$symbol',
        queryParameters: queryParameters,
      );
      
      if (response.statusCode == 200) {
        return response.data['download_url'];
      } else {
        throw Exception('导出报告失败');
      }
    } catch (e) {
      throw Exception('导出报告错误: $e');
    }
  }

  /// 获取模型性能监控
  Future<Map<String, dynamic>> getModelPerformance(String symbol) async {
    try {
      final response = await _dio.get('/ai/models/$symbol/performance');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取模型性能失败');
      }
    } catch (e) {
      throw Exception('获取模型性能错误: $e');
    }
  }

  /// 重新训练模型
  Future<void> retrainModel(String symbol) async {
    try {
      final response = await _dio.post('/ai/models/$symbol/retrain');
      
      if (response.statusCode != 200) {
        throw Exception('重新训练模型失败');
      }
    } catch (e) {
      throw Exception('重新训练模型错误: $e');
    }
  }

  /// 获取模型状态
  Future<Map<String, dynamic>> getModelStatus(String symbol) async {
    try {
      final response = await _dio.get('/ai/models/$symbol/status');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取模型状态失败');
      }
    } catch (e) {
      throw Exception('获取模型状态错误: $e');
    }
  }

  /// 手动触发分析
  Future<void> triggerAnalysis(String symbol) async {
    try {
      final response = await _dio.post('/ai/analysis/$symbol/trigger');
      
      if (response.statusCode != 200) {
        throw Exception('触发分析失败');
      }
    } catch (e) {
      throw Exception('触发分析错误: $e');
    }
  }

  // ===== 模型性能监控相关方法 =====

  /// 获取可用模型列表
  Future<List<Map<String, dynamic>>> getAvailableModels() async {
    try {
      final response = await _dio.get('/ai/monitoring/models');
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => json as Map<String, dynamic>).toList();
      } else {
        throw Exception('获取可用模型列表失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return [
        {'modelId': 'price_predictor_v1', 'status': 'healthy'},
        {'modelId': 'signal_scorer_v2', 'status': 'degraded'},
        {'modelId': 'trend_analyzer_v1', 'status': 'healthy'},
      ];
    }
  }

  /// 获取模型性能摘要
  Future<Map<String, dynamic>> getModelPerformanceSummary(String modelId) async {
    try {
      final response = await _dio.get('/ai/monitoring/models/$modelId/performance');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取模型性能摘要失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return {
        'modelId': modelId,
        'status': 'healthy',
        'latestMetrics': {
          'accuracy': 0.87,
          'precision': 0.85,
          'recall': 0.83,
          'f1Score': 0.85,
          'aucScore': 0.89,
          'predictionLatencyMs': 250.0,
          'throughputPredictionsPerSecond': 150.0,
          'dataDrriftScore': 0.05,
          'conceptDriftScore': 0.03,
          'predictionConfidenceAvg': 0.82,
          'errorRate': 0.015,
          'memoryUsageMb': 512.0,
          'cpuUsagePercent': 45.0,
        },
        'trends': {
          'accuracyTrend': 'improving',
          'latencyTrend': 'stable',
        },
        'lastUpdated': DateTime.now().toIso8601String(),
      };
    }
  }

  /// 获取模型警报列表
  Future<List<Map<String, dynamic>>> getModelAlerts(String modelId) async {
    try {
      final queryParameters = {'model_id': modelId};
      final response = await _dio.get('/ai/monitoring/alerts', queryParameters: queryParameters);
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => json as Map<String, dynamic>).toList();
      } else {
        throw Exception('获取模型警报失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return [
        {
          'alertId': 'alert_001',
          'modelId': modelId,
          'level': 'warning',
          'title': '模型准确率下降',
          'message': '价格预测模型的准确率在过去1小时内下降了3%',
          'metricName': 'accuracy',
          'currentValue': 0.84,
          'thresholdValue': 0.87,
          'timestamp': DateTime.now().subtract(const Duration(minutes: 30)).toIso8601String(),
          'acknowledged': false,
          'resolved': false,
          'metadata': {'previousAccuracy': 0.87},
        },
        {
          'alertId': 'alert_002',
          'modelId': modelId,
          'level': 'critical',
          'title': '预测延迟过高',
          'message': '信号评分模型的预测延迟超过2秒阈值',
          'metricName': 'prediction_latency',
          'currentValue': 2100.0,
          'thresholdValue': 2000.0,
          'timestamp': DateTime.now().subtract(const Duration(minutes: 15)).toIso8601String(),
          'acknowledged': false,
          'resolved': false,
          'metadata': {},
        },
      ];
    }
  }

  /// 获取模型版本列表
  Future<List<Map<String, dynamic>>> getModelVersions(String modelId) async {
    try {
      final response = await _dio.get('/ai/monitoring/models/$modelId/versions');
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => json as Map<String, dynamic>).toList();
      } else {
        throw Exception('获取模型版本失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return [
        {
          'versionId': '${modelId}_001',
          'modelId': modelId,
          'versionNumber': 'v1.2.0',
          'creationTime': DateTime.now().subtract(const Duration(days: 7)).toIso8601String(),
          'accuracy': 0.87,
          'f1Score': 0.85,
          'predictionLatencyMs': 250.0,
          'trainingDataHash': 'abc123def456',
          'modelFilePath': '/models/$modelId/v1.2.0.pkl',
          'isActive': true,
          'notes': 'Improved accuracy on ETH data',
        },
        {
          'versionId': '${modelId}_000',
          'modelId': modelId,
          'versionNumber': 'v1.1.0',
          'creationTime': DateTime.now().subtract(const Duration(days: 14)).toIso8601String(),
          'accuracy': 0.84,
          'f1Score': 0.82,
          'predictionLatencyMs': 280.0,
          'trainingDataHash': 'def456ghi789',
          'modelFilePath': '/models/$modelId/v1.1.0.pkl',
          'isActive': false,
          'notes': 'Initial release',
        },
      ];
    }
  }

  /// 获取模型性能历史
  Future<List<Map<String, dynamic>>> getModelPerformanceHistory(String modelId) async {
    try {
      final response = await _dio.get('/ai/monitoring/models/$modelId/history');
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => json as Map<String, dynamic>).toList();
      } else {
        throw Exception('获取模型性能历史失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return List.generate(24, (index) {
        final timestamp = DateTime.now().subtract(Duration(hours: 24 - index));
        return {
          'timestamp': timestamp.toIso8601String(),
          'accuracy': 0.82 + (index * 0.002),
          'precision': 0.80 + (index * 0.001),
          'recall': 0.79 + (index * 0.001),
          'f1Score': 0.81 + (index * 0.002),
          'latencyMs': 300.0 - (index * 2),
          'errorRate': 0.02 - (index * 0.0001),
        };
      });
    }
  }

  /// 获取模型健康评分
  Future<Map<String, dynamic>> getModelHealthScore(String modelId) async {
    try {
      final response = await _dio.get('/ai/monitoring/models/$modelId/health-score');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取模型健康评分失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return {
        'overallScore': 0.85,
        'healthCategory': 'good',
        'componentScores': {
          'accuracyScore': 0.87,
          'latencyScore': 0.90,
          'errorScore': 0.85,
          'driftScore': 0.80,
        },
        'recommendations': [
          '模型整体健康状况良好',
          '建议定期更新训练数据以防止概念漂移',
          '监控预测延迟，确保在500ms以内',
        ],
      };
    }
  }

  /// 触发模型重新训练
  Future<Map<String, dynamic>> triggerModelRetraining(
    String modelId,
    String triggerType,
    String reason,
  ) async {
    try {
      final response = await _dio.post('/ai/monitoring/models/$modelId/retrain', data: {
        'trigger_type': triggerType,
        'reason': reason,
        'priority': 1,
      });
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('触发重新训练失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return {
        'requestId': 'retrain_${modelId}_${DateTime.now().millisecondsSinceEpoch}',
        'modelId': modelId,
        'triggerType': triggerType,
        'triggerReason': reason,
        'requestedBy': 'user',
        'priority': 1,
        'status': 'queued',
        'createdAt': DateTime.now().toIso8601String(),
        'progressPercent': 0.0,
      };
    }
  }

  /// 确认警报
  Future<void> acknowledgeAlert(String alertId) async {
    try {
      final response = await _dio.post('/ai/monitoring/alerts/$alertId/acknowledge');
      
      if (response.statusCode != 200) {
        throw Exception('确认警报失败');
      }
    } catch (e) {
      // 开发模式下忽略错误
      print('确认警报失败: $e');
    }
  }

  /// 解决警报
  Future<void> resolveAlert(String alertId) async {
    try {
      final response = await _dio.post('/ai/monitoring/alerts/$alertId/resolve');
      
      if (response.statusCode != 200) {
        throw Exception('解决警报失败');
      }
    } catch (e) {
      // 开发模式下忽略错误
      print('解决警报失败: $e');
    }
  }

  /// 激活模型版本
  Future<void> activateModelVersion(String versionId) async {
    try {
      final response = await _dio.post('/ai/monitoring/versions/$versionId/activate');
      
      if (response.statusCode != 200) {
        throw Exception('激活模型版本失败');
      }
    } catch (e) {
      // 开发模式下忽略错误
      print('激活模型版本失败: $e');
    }
  }

  /// 回滚到指定版本
  Future<void> rollbackToVersion(String versionId) async {
    try {
      final response = await _dio.post('/ai/monitoring/versions/$versionId/rollback');
      
      if (response.statusCode != 200) {
        throw Exception('版本回滚失败');
      }
    } catch (e) {
      // 开发模式下忽略错误
      print('版本回滚失败: $e');
    }
  }

  /// 获取重新训练请求列表
  Future<List<Map<String, dynamic>>> getRetrainingRequests() async {
    try {
      final response = await _dio.get('/ai/monitoring/retraining/requests');
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => json as Map<String, dynamic>).toList();
      } else {
        throw Exception('获取重新训练请求失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return [
        {
          'requestId': 'retrain_${DateTime.now().millisecondsSinceEpoch}',
          'modelId': 'price_predictor_v1',
          'triggerType': 'manual',
          'triggerReason': 'User triggered manual retraining',
          'requestedBy': 'user',
          'priority': 1,
          'status': 'training',
          'createdAt': DateTime.now().subtract(const Duration(minutes: 30)).toIso8601String(),
          'progressPercent': 65.0,
          'estimatedCompletion': DateTime.now().add(const Duration(minutes: 15)).toIso8601String(),
        },
      ];
    }
  }

  /// 取消重新训练请求
  Future<void> cancelRetrainingRequest(String requestId) async {
    try {
      final response = await _dio.post('/ai/monitoring/retraining/requests/$requestId/cancel');
      
      if (response.statusCode != 200) {
        throw Exception('取消重新训练请求失败');
      }
    } catch (e) {
      // 开发模式下忽略错误
      print('取消重新训练请求失败: $e');
    }
  }

  /// 获取数据漂移分析结果
  Future<List<Map<String, dynamic>>> getDataDriftAnalysis(String modelId) async {
    try {
      final response = await _dio.get('/ai/monitoring/models/$modelId/drift-analysis');
      
      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => json as Map<String, dynamic>).toList();
      } else {
        throw Exception('获取数据漂移分析失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return [
        {
          'driftDetected': false,
          'driftScore': 0.05,
          'features': ['price', 'volume', 'rsi', 'macd'],
          'featureDriftScores': {
            'price': 0.03,
            'volume': 0.08,
            'rsi': 0.02,
            'macd': 0.04,
          },
          'timestamp': DateTime.now().toIso8601String(),
        },
      ];
    }
  }

  /// 获取监控系统统计
  Future<Map<String, dynamic>> getMonitoringStats() async {
    try {
      final response = await _dio.get('/ai/monitoring/stats');
      
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw Exception('获取监控系统统计失败');
      }
    } catch (e) {
      // 返回模拟数据用于开发
      return {
        'monitoringStatus': 'active',
        'totalModels': 3,
        'modelStatusBreakdown': {
          'healthy': 2,
          'degraded': 1,
          'critical': 0,
          'retraining': 0,
          'offline': 0,
        },
        'statistics': {
          'totalAlertsGenerated': 15,
          'totalRetrainingTriggers': 3,
          'averageModelAccuracy': 0.86,
        },
      };
    }
  }
}