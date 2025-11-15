import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../domain/entities/order_history.dart';
import '../../../../domain/repositories/order_history_repository.dart';
import '../../../../infrastructure/repositories/order_history_repository_impl.dart';

part 'order_history_provider.g.dart';

/// 订单历史仓库提供器
@Riverpod(keepAlive: true)
OrderHistoryRepository orderHistoryRepository(OrderHistoryRepositoryRef ref) {
  return OrderHistoryRepositoryImpl();
}

/// 订单历史状态
class OrderHistoryState {
  final List<OrderHistory> orderHistory;
  final OrderHistoryStats? stats;
  final List<RealTimeExecutionStatus> realTimeStatus;
  final List<ExecutionStatusLog> statusLogs;
  final bool isLoading;
  final bool isLoadingStats;
  final bool isLoadingRealTime;
  final String? errorMessage;
  final String filterStatus;
  final String searchQuery;
  final String sortBy;
  final String sortOrder;
  final DateTime? startDate;
  final DateTime? endDate;
  final bool showOnlyToday;
  final bool showOnlyThisWeek;
  final bool showOnlyThisMonth;

  const OrderHistoryState({
    this.orderHistory = const [],
    this.stats,
    this.realTimeStatus = const [],
    this.statusLogs = const [],
    this.isLoading = false,
    this.isLoadingStats = false,
    this.isLoadingRealTime = false,
    this.errorMessage,
    this.filterStatus = 'all',
    this.searchQuery = '',
    this.sortBy = 'execution_start_time',
    this.sortOrder = 'desc',
    this.startDate,
    this.endDate,
    this.showOnlyToday = false,
    this.showOnlyThisWeek = false,
    this.showOnlyThisMonth = false,
  });

  OrderHistoryState copyWith({
    List<OrderHistory>? orderHistory,
    OrderHistoryStats? stats,
    List<RealTimeExecutionStatus>? realTimeStatus,
    List<ExecutionStatusLog>? statusLogs,
    bool? isLoading,
    bool? isLoadingStats,
    bool? isLoadingRealTime,
    String? errorMessage,
    String? filterStatus,
    String? searchQuery,
    String? sortBy,
    String? sortOrder,
    DateTime? startDate,
    DateTime? endDate,
    bool? showOnlyToday,
    bool? showOnlyThisWeek,
    bool? showOnlyThisMonth,
  }) {
    return OrderHistoryState(
      orderHistory: orderHistory ?? this.orderHistory,
      stats: stats ?? this.stats,
      realTimeStatus: realTimeStatus ?? this.realTimeStatus,
      statusLogs: statusLogs ?? this.statusLogs,
      isLoading: isLoading ?? this.isLoading,
      isLoadingStats: isLoadingStats ?? this.isLoadingStats,
      isLoadingRealTime: isLoadingRealTime ?? this.isLoadingRealTime,
      errorMessage: errorMessage ?? this.errorMessage,
      filterStatus: filterStatus ?? this.filterStatus,
      searchQuery: searchQuery ?? this.searchQuery,
      sortBy: sortBy ?? this.sortBy,
      sortOrder: sortOrder ?? this.sortOrder,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      showOnlyToday: showOnlyToday ?? this.showOnlyToday,
      showOnlyThisWeek: showOnlyThisWeek ?? this.showOnlyThisWeek,
      showOnlyThisMonth: showOnlyThisMonth ?? this.showOnlyThisMonth,
    );
  }

  /// 获取过滤后的订单历史
  List<OrderHistory> get filteredOrderHistory {
    var filtered = orderHistory;

    // 按状态过滤
    if (filterStatus != 'all') {
      switch (filterStatus) {
        case 'successful':
          filtered = filtered.where((order) => order.isSuccessful).toList();
          break;
        case 'failed':
          filtered = filtered.where((order) => order.isFailed).toList();
          break;
        case 'executing':
          filtered = filtered.where((order) => order.isExecuting).toList();
          break;
        case 'completed':
          filtered = filtered.where((order) => order.isCompleted).toList();
          break;
        case 'pending':
          filtered = filtered.where((order) => order.executionStatus == ExecutionStatus.pending).toList();
          break;
      }
    }

    // 按搜索查询过滤
    if (searchQuery.isNotEmpty) {
      final query = searchQuery.toLowerCase();
      filtered = filtered.where((order) {
        return order.symbol.toLowerCase().contains(query) ||
               order.exchange.toLowerCase().contains(query) ||
               (order.autoOrderStrategyName?.toLowerCase().contains(query) ?? false) ||
               (order.accountName?.toLowerCase().contains(query) ?? false);
      }).toList();
    }

    // 按时间过滤
    if (showOnlyToday) {
      final today = DateTime.now();
      final todayStart = DateTime(today.year, today.month, today.day);
      filtered = filtered.where((order) => 
          order.executionStartTime.isAfter(todayStart)).toList();
    } else if (showOnlyThisWeek) {
      final now = DateTime.now();
      final weekStart = now.subtract(Duration(days: now.weekday - 1));
      final weekStartDate = DateTime(weekStart.year, weekStart.month, weekStart.day);
      filtered = filtered.where((order) => 
          order.executionStartTime.isAfter(weekStartDate)).toList();
    } else if (showOnlyThisMonth) {
      final now = DateTime.now();
      final monthStart = DateTime(now.year, now.month, 1);
      filtered = filtered.where((order) => 
          order.executionStartTime.isAfter(monthStart)).toList();
    } else if (startDate != null || endDate != null) {
      filtered = filtered.where((order) {
        final orderTime = order.executionStartTime;
        if (startDate != null && orderTime.isBefore(startDate!)) return false;
        if (endDate != null && orderTime.isAfter(endDate!)) return false;
        return true;
      }).toList();
    }

    return filtered;
  }

  /// 获取正在执行的订单数量
  int get executingOrdersCount => realTimeStatus.where((status) => 
      status.currentStatus == ExecutionStatus.executing || 
      status.currentStatus == ExecutionStatus.retrying).length;

  /// 获取待处理订单数量
  int get pendingOrdersCount => realTimeStatus.where((status) => 
      status.currentStatus == ExecutionStatus.pending).length;

  /// 获取统计数据概览
  Map<String, dynamic> get statsOverview {
    final total = orderHistory.length;
    final successful = orderHistory.where((o) => o.isSuccessful).length;
    final failed = orderHistory.where((o) => o.isFailed).length;
    final executing = orderHistory.where((o) => o.isExecuting).length;
    
    return {
      'total': total,
      'successful': successful,
      'failed': failed,
      'executing': executing,
      'success_rate': total > 0 ? (successful / total * 100) : 0.0,
      'failure_rate': total > 0 ? (failed / total * 100) : 0.0,
    };
  }
}

/// 订单历史状态提供器
@RiverpodNotifier
class OrderHistoryNotifier extends _$OrderHistoryNotifier {
  @override
  OrderHistoryState build() {
    return const OrderHistoryState();
  }

  /// 加载订单历史
  Future<void> loadOrderHistory({
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
    if (state.isLoading) return;

    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final repository = ref.read(orderHistoryRepositoryProvider);
      final orders = await repository.getOrderHistory(
        userId: userId,
        accountId: accountId,
        symbol: symbol,
        orderType: orderType,
        orderSide: orderSide,
        executionStatus: executionStatus,
        exchange: exchange,
        startDate: startDate ?? state.startDate,
        endDate: endDate ?? state.endDate,
        sortBy: sortBy,
        sortOrder: sortOrder,
        limit: limit,
        offset: offset,
      );
      
      state = state.copyWith(
        orderHistory: orders,
        isLoading: false,
        sortBy: sortBy,
        sortOrder: sortOrder,
        startDate: startDate ?? state.startDate,
        endDate: endDate ?? state.endDate,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// 加载统计信息
  Future<void> loadStats({
    int? userId,
    int? accountId,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    if (state.isLoadingStats) return;

    state = state.copyWith(isLoadingStats: true, errorMessage: null);

    try {
      final repository = ref.read(orderHistoryRepositoryProvider);
      final stats = await repository.getOrderHistoryStats(
        userId: userId,
        accountId: accountId,
        startDate: startDate ?? state.startDate,
        endDate: endDate ?? state.endDate,
      );
      
      state = state.copyWith(
        stats: stats,
        isLoadingStats: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingStats: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// 加载实时执行状态
  Future<void> loadRealTimeStatus({
    int? userId,
    int? accountId,
  }) async {
    if (state.isLoadingRealTime) return;

    state = state.copyWith(isLoadingRealTime: true, errorMessage: null);

    try {
      final repository = ref.read(orderHistoryRepositoryProvider);
      final statusList = await repository.getRealTimeExecutionStatus(
        userId: userId,
        accountId: accountId,
      );
      
      state = state.copyWith(
        realTimeStatus: statusList,
        isLoadingRealTime: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingRealTime: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// 加载执行状态日志
  Future<void> loadStatusLogs(int orderId, {int limit = 50}) async {
    try {
      final repository = ref.read(orderHistoryRepositoryProvider);
      final logs = await repository.getExecutionStatusLog(orderId, limit: limit);
      
      state = state.copyWith(statusLogs: logs);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  /// 获取订单历史详情
  Future<OrderHistory?> getOrderHistoryByOrderId(int orderId) async {
    try {
      final repository = ref.read(orderHistoryRepositoryProvider);
      return await repository.getOrderHistoryByOrderId(orderId);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return null;
    }
  }

  /// 设置状态过滤
  void setFilterStatus(String status) {
    state = state.copyWith(filterStatus: status);
  }

  /// 设置搜索查询
  void setSearchQuery(String query) {
    state = state.copyWith(searchQuery: query);
  }

  /// 设置排序
  void setSorting(String sortBy, String sortOrder) {
    state = state.copyWith(sortBy: sortBy, sortOrder: sortOrder);
    loadOrderHistory(
      sortBy: sortBy,
      sortOrder: sortOrder,
    );
  }

  /// 设置时间范围
  void setDateRange(DateTime? startDate, DateTime? endDate) {
    state = state.copyWith(
      startDate: startDate,
      endDate: endDate,
      showOnlyToday: false,
      showOnlyThisWeek: false,
      showOnlyThisMonth: false,
    );
    
    loadOrderHistory(
      startDate: startDate,
      endDate: endDate,
    );
    
    loadStats(
      startDate: startDate,
      endDate: endDate,
    );
  }

  /// 设置快速时间过滤
  void setQuickTimeFilter({
    bool showOnlyToday = false,
    bool showOnlyThisWeek = false,
    bool showOnlyThisMonth = false,
  }) {
    DateTime? startDate;
    DateTime? endDate;
    
    final now = DateTime.now();
    
    if (showOnlyToday) {
      startDate = DateTime(now.year, now.month, now.day);
      endDate = now;
    } else if (showOnlyThisWeek) {
      final weekStart = now.subtract(Duration(days: now.weekday - 1));
      startDate = DateTime(weekStart.year, weekStart.month, weekStart.day);
      endDate = now;
    } else if (showOnlyThisMonth) {
      startDate = DateTime(now.year, now.month, 1);
      endDate = now;
    }
    
    state = state.copyWith(
      startDate: startDate,
      endDate: endDate,
      showOnlyToday: showOnlyToday,
      showOnlyThisWeek: showOnlyThisWeek,
      showOnlyThisMonth: showOnlyThisMonth,
    );
    
    loadOrderHistory(
      startDate: startDate,
      endDate: endDate,
    );
    
    loadStats(
      startDate: startDate,
      endDate: endDate,
    );
  }

  /// 清除错误消息
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }

  /// 刷新数据
  Future<void> refresh() async {
    await loadOrderHistory();
    await loadStats();
    await loadRealTimeStatus();
  }

  /// 刷新实时状态
  Future<void> refreshRealTimeStatus() async {
    await loadRealTimeStatus();
  }

  /// 更新执行状态（手动）
  Future<void> updateExecutionStatus(
    int orderId,
    Map<String, dynamic> statusUpdate,
  ) async {
    try {
      final repository = ref.read(orderHistoryRepositoryProvider);
      await repository.updateExecutionStatus(orderId, statusUpdate);
      
      // 刷新相关数据
      await refresh();
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      rethrow;
    }
  }
}

/// 订单历史状态提供器别名
final orderHistoryProvider = StateNotifierProvider<OrderHistoryNotifier, OrderHistoryState>(
  (ref) => OrderHistoryNotifier(ref),
);

/// 实时状态监控提供者
final realTimeStatusProvider = StreamProvider<List<RealTimeExecutionStatus>>((ref) async* {
  final notifier = ref.read(orderHistoryProvider.notifier);
  
  // 初始加载
  await notifier.loadRealTimeStatus();
  
  // 监听状态变化并定期刷新
  Timer? timer;
  
  // 定期刷新实时状态
  timer = Timer.periodic(const Duration(seconds: 5), (timer) async {
    await notifier.refreshRealTimeStatus();
  });
  
  // 提供当前状态
  yield ref.watch(orderHistoryProvider).realTimeStatus;
  
  // 组件销毁时清理定时器
  ref.onDispose(() {
    timer?.cancel();
  });
});