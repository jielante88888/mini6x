import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import '../../domain/entities/order_history.dart';
import '../../domain/repositories/order_history_repository.dart';
import '../api_client/api_client.dart';

/// 订单历史仓库实现
class OrderHistoryRepositoryImpl implements OrderHistoryRepository {
  final ApiClient _apiClient;

  OrderHistoryRepositoryImpl() : _apiClient = ApiClient();

  /// 获取订单历史记录
  @override
  Future<List<OrderHistory>> getOrderHistory({
    int? userId,
    int? accountId,
    String? symbol,
    String? orderType,
    String? orderSide,
    String? executionStatus,
    String? exchange,
    DateTime? startDate,
    DateTime? endDate,
    String sortBy = 'execution_start_time',
    String sortOrder = 'desc',
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        'offset': offset,
        'sort_by': sortBy,
        'sort_order': sortOrder,
      };

      if (userId != null) queryParams['user_id'] = userId;
      if (accountId != null) queryParams['account_id'] = accountId;
      if (symbol != null) queryParams['symbol'] = symbol;
      if (orderType != null) queryParams['order_type'] = orderType;
      if (orderSide != null) queryParams['order_side'] = orderSide;
      if (executionStatus != null) queryParams['execution_status'] = executionStatus;
      if (exchange != null) queryParams['exchange'] = exchange;
      if (startDate != null) queryParams['start_date'] = startDate!.toIso8601String();
      if (endDate != null) queryParams['end_date'] = endDate!.toIso8601String();

      final response = await _apiClient.get(
        '/api/v1/order-history/',
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonData = response.data;
        return jsonData.map((json) => OrderHistory.fromJson(json)).toList();
      } else {
        throw Exception('获取订单历史失败: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('未授权访问');
      } else if (e.response?.statusCode == 403) {
        throw Exception('访问被拒绝');
      } else if (e.response?.statusCode == 404) {
        return []; // 返回空列表而不是抛出异常
      } else {
        throw Exception('网络错误: ${e.message}');
      }
    } catch (e) {
      throw Exception('获取订单历史失败: $e');
    }
  }

  /// 获取订单历史统计信息
  @override
  Future<OrderHistoryStats> getOrderHistoryStats({
    int? userId,
    int? accountId,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final queryParams = <String, dynamic>{};

      if (userId != null) queryParams['user_id'] = userId;
      if (accountId != null) queryParams['account_id'] = accountId;
      if (startDate != null) queryParams['start_date'] = startDate!.toIso8601String();
      if (endDate != null) queryParams['end_date'] = endDate!.toIso8601String();

      final response = await _apiClient.get(
        '/api/v1/order-history/stats',
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        return OrderHistoryStats.fromJson(response.data);
      } else {
        throw Exception('获取统计信息失败: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('未授权访问');
      } else if (e.response?.statusCode == 403) {
        throw Exception('访问被拒绝');
      } else {
        throw Exception('网络错误: ${e.message}');
      }
    } catch (e) {
      throw Exception('获取统计信息失败: $e');
    }
  }

  /// 获取实时执行状态
  @override
  Future<List<RealTimeExecutionStatus>> getRealTimeExecutionStatus({
    int? userId,
    int? accountId,
  }) async {
    try {
      final queryParams = <String, dynamic>{};

      if (userId != null) queryParams['user_id'] = userId;
      if (accountId != null) queryParams['account_id'] = accountId;

      final response = await _apiClient.get(
        '/api/v1/order-history/real-time-status',
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonData = response.data;
        return jsonData.map((json) => RealTimeExecutionStatus.fromJson(json)).toList();
      } else {
        throw Exception('获取实时状态失败: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('未授权访问');
      } else if (e.response?.statusCode == 403) {
        throw Exception('访问被拒绝');
      } else {
        throw Exception('网络错误: ${e.message}');
      }
    } catch (e) {
      throw Exception('获取实时状态失败: $e');
    }
  }

  /// 获取执行状态变更日志
  @override
  Future<List<ExecutionStatusLog>> getExecutionStatusLog(int orderId, {int limit = 50}) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
      };

      final response = await _apiClient.get(
        '/api/v1/order-history/execution-status/$orderId',
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonData = response.data;
        return jsonData.map((json) => ExecutionStatusLog.fromJson(json)).toList();
      } else {
        throw Exception('获取状态日志失败: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('未授权访问');
      } else if (e.response?.statusCode == 403) {
        throw Exception('访问被拒绝');
      } else if (e.response?.statusCode == 404) {
        return []; // 返回空列表而不是抛出异常
      } else {
        throw Exception('网络错误: ${e.message}');
      }
    } catch (e) {
      throw Exception('获取状态日志失败: $e');
    }
  }

  /// 根据订单ID获取订单历史
  @override
  Future<OrderHistory?> getOrderHistoryByOrderId(int orderId) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/order-history/order/$orderId',
      );

      if (response.statusCode == 200) {
        return OrderHistory.fromJson(response.data);
      } else {
        throw Exception('获取订单历史失败: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('未授权访问');
      } else if (e.response?.statusCode == 403) {
        throw Exception('访问被拒绝');
      } else if (e.response?.statusCode == 404) {
        return null; // 返回null而不是抛出异常
      } else {
        throw Exception('网络错误: ${e.message}');
      }
    } catch (e) {
      throw Exception('获取订单历史失败: $e');
    }
  }

  /// 更新执行状态
  @override
  Future<void> updateExecutionStatus(int orderId, Map<String, dynamic> statusUpdate) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/order-history/order-history/$orderId/update-status',
        data: statusUpdate,
      );

      if (response.statusCode == 200) {
        return;
      } else {
        throw Exception('更新执行状态失败: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception('未授权访问');
      } else if (e.response?.statusCode == 403) {
        throw Exception('访问被拒绝');
      } else if (e.response?.statusCode == 404) {
        throw Exception('订单不存在');
      } else {
        throw Exception('网络错误: ${e.message}');
      }
    } catch (e) {
      throw Exception('更新执行状态失败: $e');
    }
  }
}