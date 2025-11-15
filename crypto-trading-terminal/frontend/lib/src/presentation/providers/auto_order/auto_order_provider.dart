import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../../domain/entities/auto_order.dart';
import '../../../../domain/repositories/auto_order_repository.dart';
import '../../../../infrastructure/repositories/auto_order_repository_impl.dart';

part 'auto_order_provider.g.dart';

/// 自动订单仓库提供器
@Riverpod(keepAlive: true)
AutoOrderRepository autoOrderRepository(AutoOrderRepositoryRef ref) {
  return AutoOrderRepositoryImpl();
}

/// 自动订单状态
class AutoOrderState {
  final List<AutoOrder> autoOrders;
  final bool isLoading;
  final String? errorMessage;
  final String filterStatus;
  final String searchQuery;
  final bool isCreating;

  const AutoOrderState({
    this.autoOrders = const [],
    this.isLoading = false,
    this.errorMessage,
    this.filterStatus = 'all',
    this.searchQuery = '',
    this.isCreating = false,
  });

  AutoOrderState copyWith({
    List<AutoOrder>? autoOrders,
    bool? isLoading,
    String? errorMessage,
    String? filterStatus,
    String? searchQuery,
    bool? isCreating,
  }) {
    return AutoOrderState(
      autoOrders: autoOrders ?? this.autoOrders,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      filterStatus: filterStatus ?? this.filterStatus,
      searchQuery: searchQuery ?? this.searchQuery,
      isCreating: isCreating ?? this.isCreating,
    );
  }

  /// 获取过滤后的订单列表
  List<AutoOrder> get filteredOrders {
    var filtered = autoOrders;

    // 按状态过滤
    if (filterStatus != 'all') {
      switch (filterStatus) {
        case 'active':
          filtered = filtered.where((order) => order.isActive && !order.isPaused).toList();
          break;
        case 'paused':
          filtered = filtered.where((order) => order.isPaused).toList();
          break;
        case 'expired':
          filtered = filtered.where((order) => order.isExpired).toList();
          break;
      }
    }

    // 按搜索查询过滤
    if (searchQuery.isNotEmpty) {
      final query = searchQuery.toLowerCase();
      filtered = filtered.where((order) {
        return order.strategyName.toLowerCase().contains(query) ||
               order.symbol.toLowerCase().contains(query);
      }).toList();
    }

    return filtered;
  }

  /// 获取活跃订单数量
  int get activeOrdersCount => autoOrders.where((o) => o.isActive && !o.isPaused).length;

  /// 获取暂停订单数量
  int get pausedOrdersCount => autoOrders.where((o) => o.isPaused).length;

  /// 获取总执行次数
  int get totalExecutions => autoOrders.fold<int>(0, (sum, order) => sum + order.executionCount);

  /// 获取成功执行次数
  int get successfulExecutions => autoOrders.where((o) => o.isLastExecutionSuccessful == true).length;
}

/// 自动订单状态提供器
@RiverpodNotifier
class AutoOrderNotifier extends _$AutoOrderNotifier {
  @override
  AutoOrderState build() {
    return const AutoOrderState();
  }

  /// 加载自动订单列表
  Future<void> loadAutoOrders() async {
    if (state.isLoading) return;

    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      final orders = await repository.getAutoOrders();
      
      state = state.copyWith(
        autoOrders: orders,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// 创建自动订单
  Future<void> createAutoOrder(CreateAutoOrderRequest request) async {
    state = state.copyWith(isCreating: true, errorMessage: null);

    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      await repository.createAutoOrder(request);
      
      // 重新加载订单列表
      await loadAutoOrders();
      
      state = state.copyWith(isCreating: false);
    } catch (e) {
      state = state.copyWith(
        isCreating: false,
        errorMessage: e.toString(),
      );
      rethrow;
    }
  }

  /// 切换订单状态
  Future<void> toggleOrderStatus(int orderId, bool isActive) async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      await repository.toggleAutoOrderStatus(orderId, isActive);
      
      // 更新本地状态
      final updatedOrders = state.autoOrders.map((order) {
        if (order.id == orderId) {
          return order.copyWith(isActive: isActive);
        }
        return order;
      }).toList();
      
      state = state.copyWith(autoOrders: updatedOrders);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      rethrow;
    }
  }

  /// 暂停订单
  Future<void> pauseOrder(int orderId) async {
    return toggleOrderStatus(orderId, false);
  }

  /// 恢复订单
  Future<void> resumeOrder(int orderId) async {
    return toggleOrderStatus(orderId, true);
  }

  /// 切换订单暂停状态
  Future<void> toggleOrderPauseStatus(int orderId, bool isPaused) async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      await repository.toggleAutoOrderPauseStatus(orderId, isPaused);
      
      // 更新本地状态
      final updatedOrders = state.autoOrders.map((order) {
        if (order.id == orderId) {
          return order.copyWith(isPaused: isPaused);
        }
        return order;
      }).toList();
      
      state = state.copyWith(autoOrders: updatedOrders);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      rethrow;
    }
  }

  /// 删除自动订单
  Future<void> deleteAutoOrder(int orderId) async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      await repository.deleteAutoOrder(orderId);
      
      // 从本地状态中移除
      final updatedOrders = state.autoOrders.where((order) => order.id != orderId).toList();
      
      state = state.copyWith(autoOrders: updatedOrders);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      rethrow;
    }
  }

  /// 手动触发订单执行
  Future<void> triggerOrderExecution(int orderId) async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      await repository.triggerAutoOrderExecution(orderId);
      
      // 重新加载订单状态
      await loadAutoOrders();
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      rethrow;
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

  /// 清除错误消息
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }

  /// 获取单个订单详情
  Future<AutoOrder?> getOrderById(int orderId) async {
    try {
      // 先从本地缓存查找
      final localOrder = state.autoOrders.firstWhere(
        (order) => order.id == orderId,
        orElse: () => throw StateError('Order not found'),
      );
      
      return localOrder;
    } catch (e) {
      // 如果本地没有，则从服务器获取
      try {
        final repository = ref.read(autoOrderRepositoryProvider);
        final order = await repository.getAutoOrderById(orderId);
        
        // 更新本地缓存
        final existingOrders = List<AutoOrder>.from(state.autoOrders);
        final existingIndex = existingOrders.indexWhere((o) => o.id == orderId);
        
        if (existingIndex >= 0) {
          existingOrders[existingIndex] = order;
        } else {
          existingOrders.add(order);
        }
        
        state = state.copyWith(autoOrders: existingOrders);
        
        return order;
      } catch (serverError) {
        state = state.copyWith(errorMessage: serverError.toString());
        return null;
      }
    }
  }

  /// 获取订单执行历史
  Future<List<Map<String, dynamic>>> getOrderExecutionHistory(int orderId) async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      return await repository.getOrderExecutionHistory(orderId);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return [];
    }
  }

  /// 获取订单统计信息
  Future<Map<String, dynamic>> getOrderStatistics() async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      return await repository.getOrderStatistics();
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return {};
    }
  }

  /// 批量操作订单
  Future<void> batchToggleOrdersStatus(List<int> orderIds, bool isActive) async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      
      // 执行批量操作
      for (final orderId in orderIds) {
        await repository.toggleAutoOrderStatus(orderId, isActive);
      }
      
      // 更新本地状态
      final updatedOrders = state.autoOrders.map((order) {
        if (orderIds.contains(order.id)) {
          return order.copyWith(isActive: isActive);
        }
        return order;
      }).toList();
      
      state = state.copyWith(autoOrders: updatedOrders);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      rethrow;
    }
  }

  /// 验证订单参数
  Future<RiskCheckResult?> validateOrderParameters(CreateAutoOrderRequest request) async {
    try {
      final repository = ref.read(autoOrderRepositoryProvider);
      return await repository.validateOrderParameters(request);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return null;
    }
  }
}

/// 自动订单状态提供器别名
final autoOrderProvider = StateNotifierProvider<AutoOrderNotifier, AutoOrderState>(
  (ref) => AutoOrderNotifier(ref),
);