import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../domain/entities/risk_control.dart';

part 'risk_control_provider.g.dart';

@Riverpod(keepAlive: true)
class RiskControlNotifier extends _$RiskControlNotifier {
  static const String baseUrl = 'http://localhost:8000/api/v1';

  @override
  RiskControlState build(int userId) {
    return const RiskControlState();
  }

  /// 加载仪表板数据
  Future<void> loadDashboardData(int userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/risk/dashboard/$userId'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        final dashboardData = RiskDashboardData.fromJson(jsonData['data']);
        
        state = state.copyWith(
          dashboardData: dashboardData,
          lastUpdateTime: DateTime.now(),
          error: null,
        );
      } else {
        throw Exception('加载仪表板数据失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '加载仪表板数据失败: $e',
        isLoading: false,
      );
    }
  }

  /// 加载仓位风险数据
  Future<void> loadPositions(int userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/risk/positions/$userId'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        final positionsJson = jsonData['positions'] as List;
        final positions = positionsJson
            .map((json) => PositionRisk.fromJson(json as Map<String, dynamic>))
            .toList();
        
        state = state.copyWith(
          positions: positions,
          error: null,
        );
      } else {
        throw Exception('加载仓位数据失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '加载仓位数据失败: $e',
      );
    }
  }

  /// 加载风险警告
  Future<void> loadAlerts(int userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/risk/alerts/$userId?limit=100'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        final alertsJson = jsonData['alerts'] as List;
        final alerts = alertsJson
            .map((json) => RiskAlert.fromJson(json as Map<String, dynamic>))
            .toList();
        
        state = state.copyWith(
          alerts: alerts,
          error: null,
        );
      } else {
        throw Exception('加载风险警告失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '加载风险警告失败: $e',
      );
    }
  }

  /// 加载风险指标
  Future<void> loadMetrics(int userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/risk/metrics/$userId?period_hours=24'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        final metricsData = RiskMetrics.fromJson(jsonData['metrics']);
        
        state = state.copyWith(
          metrics: metricsData,
          error: null,
        );
      } else {
        throw Exception('加载风险指标失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '加载风险指标失败: $e',
      );
    }
  }

  /// 加载风险配置
  Future<void> loadConfigs(int userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/risk/config/$userId'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        final configsJson = jsonData['configs'] as List;
        final configs = configsJson
            .map((json) => RiskConfig.fromJson(json as Map<String, dynamic>))
            .toList();
        
        state = state.copyWith(
          configs: configs,
          error: null,
        );
      } else {
        throw Exception('加载风险配置失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '加载风险配置失败: $e',
      );
    }
  }

  /// 确认风险警告
  Future<void> acknowledgeAlert(int userId, int alertId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/risk/alerts/$alertId/acknowledge'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'user_id': userId}),
      );

      if (response.statusCode == 200) {
        // 更新本地状态
        final updatedAlerts = state.alerts.map((alert) {
          if (alert.alertId == alertId) {
            return alert.copyWith(
              isAcknowledged: true,
              acknowledgedAt: DateTime.now(),
            );
          }
          return alert;
        }).toList();

        state = state.copyWith(alerts: updatedAlerts);
      } else {
        throw Exception('确认警告失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '确认警告失败: $e',
      );
    }
  }

  /// 紧急停止交易
  Future<void> emergencyStop(int userId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/risk/emergency_stop/$userId'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        // 清除错误状态并重新加载数据
        state = state.copyWith(
          error: null,
          lastUpdateTime: DateTime.now(),
        );
        
        // 重新加载自动订单状态
        await loadDashboardData(userId);
      } else {
        throw Exception('紧急停止失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '紧急停止失败: $e',
      );
    }
  }

  /// 更新风险配置
  Future<void> updateRiskConfig(int userId, int configId, Map<String, dynamic> config) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/risk/config/$configId'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(config),
      );

      if (response.statusCode == 200) {
        // 重新加载配置
        await loadConfigs(userId);
      } else {
        throw Exception('更新配置失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        error: '更新配置失败: $e',
      );
    }
  }

  /// 清除错误
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// 风险控制状态
class RiskControlState {
  final RiskDashboardData? dashboardData;
  final List<PositionRisk> positions;
  final List<RiskAlert> alerts;
  final RiskMetrics? metrics;
  final List<RiskConfig> configs;
  final bool isLoading;
  final String? error;
  final DateTime? lastUpdateTime;

  const RiskControlState({
    this.dashboardData,
    this.positions = const [],
    this.alerts = const [],
    this.metrics,
    this.configs = const [],
    this.isLoading = false,
    this.error,
    this.lastUpdateTime,
  });

  RiskControlState copyWith({
    RiskDashboardData? dashboardData,
    List<PositionRisk>? positions,
    List<RiskAlert>? alerts,
    RiskMetrics? metrics,
    List<RiskConfig>? configs,
    bool? isLoading,
    String? error,
    DateTime? lastUpdateTime,
  }) {
    return RiskControlState(
      dashboardData: dashboardData ?? this.dashboardData,
      positions: positions ?? this.positions,
      alerts: alerts ?? this.alerts,
      metrics: metrics ?? this.metrics,
      configs: configs ?? this.configs,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      lastUpdateTime: lastUpdateTime ?? this.lastUpdateTime,
    );
  }
}

/// 风险控制提供器
final riskControlProvider = StateNotifierProvider.family<RiskControlNotifier, RiskControlState, int>(
  (ref, userId) => RiskControlNotifier(),
);
