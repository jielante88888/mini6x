import 'dart:convert';
import 'package:http/http.dart' as http;

import '../../domain/entities/auto_order.dart';
import '../../domain/repositories/auto_order_repository.dart';

/// 自动订单仓库实现
class AutoOrderRepositoryImpl implements AutoOrderRepository {
  static const String baseUrl = 'http://localhost:8000/api/v1';

  @override
  Future<List<AutoOrder>> getAutoOrders({
    String? filter,
    String? search,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/auto-orders').replace(
        queryParameters: {
          if (filter != null) 'filter': filter,
          if (search != null) 'search': search,
        },
      );

      final response = await http.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as List;
        return jsonData
            .map((json) => AutoOrder.fromJson(json as Map<String, dynamic>))
            .toList();
      } else {
        throw Exception('获取自动订单失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<AutoOrder?> getAutoOrderById(int id) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/auto-orders/$id'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        return AutoOrder.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        return null;
      } else {
        throw Exception('获取自动订单详情失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<AutoOrder> createAutoOrder(CreateAutoOrderRequest request) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auto-orders'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(request.toJson()),
      );

      if (response.statusCode == 201) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        return AutoOrder.fromJson(jsonData);
      } else if (response.statusCode == 400) {
        final error = json.decode(response.body) as Map<String, dynamic>;
        throw Exception('创建失败: ${error['detail'] ?? '未知错误'}');
      } else {
        throw Exception('创建自动订单失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<AutoOrder> updateAutoOrder(int id, UpdateAutoOrderRequest request) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/auto-orders/$id'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(request.toJson()),
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        return AutoOrder.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        throw Exception('自动订单不存在');
      } else if (response.statusCode == 400) {
        final error = json.decode(response.body) as Map<String, dynamic>;
        throw Exception('更新失败: ${error['detail'] ?? '未知错误'}');
      } else {
        throw Exception('更新自动订单失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<void> deleteAutoOrder(int id) async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/auto-orders/$id'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 204) {
        return; // 删除成功，无内容返回
      } else if (response.statusCode == 404) {
        throw Exception('自动订单不存在');
      } else {
        throw Exception('删除自动订单失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<AutoOrder> toggleOrderStatus(int id, bool isActive) async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/auto-orders/$id/status'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'is_active': isActive}),
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        return AutoOrder.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        throw Exception('自动订单不存在');
      } else {
        throw Exception('切换状态失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<AutoOrder> retryOrder(int id) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auto-orders/$id/retry'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        return AutoOrder.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        throw Exception('自动订单不存在');
      } else {
        throw Exception('重试失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<List<OrderExecution>> getExecutionHistory(int autoOrderId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/auto-orders/$autoOrderId/executions'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as List;
        return jsonData
            .map((json) => OrderExecution.fromJson(json as Map<String, dynamic>))
            .toList();
      } else if (response.statusCode == 404) {
        return []; // 没有执行历史记录
      } else {
        throw Exception('获取执行历史失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }

  @override
  Future<AutoOrderStatistics> getStatistics() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/auto-orders/statistics'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        return AutoOrderStatistics.fromJson(jsonData);
      } else {
        throw Exception('获取统计信息失败: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('网络错误: $e');
    }
  }
}