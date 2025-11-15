import '../../domain/entities/order_history.dart';

/// 订单历史仓库接口
abstract class OrderHistoryRepository {
  /// 获取订单历史记录
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
    String sortBy,
    String sortOrder,
    int limit,
    int offset,
  });

  /// 获取订单历史统计信息
  Future<OrderHistoryStats> getOrderHistoryStats({
    int? userId,
    int? accountId,
    DateTime? startDate,
    DateTime? endDate,
  });

  /// 获取实时执行状态
  Future<List<RealTimeExecutionStatus>> getRealTimeExecutionStatus({
    int? userId,
    int? accountId,
  });

  /// 获取执行状态变更日志
  Future<List<ExecutionStatusLog>> getExecutionStatusLog(int orderId, {int limit});

  /// 根据订单ID获取订单历史
  Future<OrderHistory?> getOrderHistoryByOrderId(int orderId);

  /// 更新执行状态
  Future<void> updateExecutionStatus(int orderId, Map<String, dynamic> statusUpdate);
}