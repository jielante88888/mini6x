import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../domain/entities/order_history.dart';
import '../../../presentation/providers/order_history/order_history_provider.dart';
import '../../../presentation/widgets/common/loading_overlay.dart';
import '../../../presentation/widgets/common/error_message.dart';
import '../../../presentation/widgets/order_history/order_history_list_widget.dart';
import '../../../presentation/widgets/order_history/order_history_stats_widget.dart';
import '../../../presentation/widgets/order_history/real_time_status_widget.dart';

class OrderHistoryPage extends ConsumerStatefulWidget {
  const OrderHistoryPage({super.key});

  @override
  ConsumerState<OrderHistoryPage> createState() => _OrderHistoryPageState();
}

class _OrderHistoryPageState extends ConsumerState<OrderHistoryPage>
    with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    
    // 加载初始数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(orderHistoryProvider.notifier).loadOrderHistory();
      ref.read(orderHistoryProvider.notifier).loadStats();
      ref.read(orderHistoryProvider.notifier).loadRealTimeStatus();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final orderHistoryState = ref.watch(orderHistoryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('订单历史与执行跟踪'),
        elevation: 0,
        backgroundColor: theme.colorScheme.surface,
        foregroundColor: theme.colorScheme.onSurface,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(
              icon: Icon(Icons.history),
              text: '订单历史',
            ),
            Tab(
              icon: Icon(Icons.analytics),
              text: '统计分析',
            ),
            Tab(
              icon: Icon(Icons.speed),
              text: '实时状态',
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(orderHistoryProvider.notifier).refresh(),
            tooltip: '刷新数据',
          ),
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
            tooltip: '筛选和搜索',
          ),
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: _showHelpDialog,
            tooltip: '帮助',
          ),
        ],
      ),
      body: LoadingOverlay(
        isLoading: orderHistoryState.isLoading || 
                  orderHistoryState.isLoadingStats ||
                  orderHistoryState.isLoadingRealTime,
        child: Column(
          children: [
            // 快速统计栏
            _buildQuickStats(theme, orderHistoryState),
            
            // 主要内容区域
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // 订单历史标签页
                  _buildOrderHistoryTab(theme, orderHistoryState),
                  
                  // 统计分析标签页
                  _buildStatsTab(theme, orderHistoryState),
                  
                  // 实时状态标签页
                  _buildRealTimeTab(theme, orderHistoryState),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickStats(ThemeData theme, OrderHistoryState state) {
    final stats = state.statsOverview;
    
    return Container(
      margin: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: _buildQuickStatCard(
              theme,
              '总订单',
              '${stats['total']}',
              Icons.list_alt,
              theme.colorScheme.primary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildQuickStatCard(
              theme,
              '成功',
              '${stats['successful']}',
              Icons.check_circle,
              Colors.green,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildQuickStatCard(
              theme,
              '失败',
              '${stats['failed']}',
              Icons.error,
              Colors.red,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildQuickStatCard(
              theme,
              '执行中',
              '${stats['executing']}',
              Icons.pending,
              Colors.orange,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildQuickStatCard(
              theme,
              '成功率',
              '${stats['success_rate'].toStringAsFixed(1)}%',
              Icons.trending_up,
              Colors.blue,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickStatCard(ThemeData theme, String title, String value, 
      IconData icon, Color color) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(
              value,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              title,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOrderHistoryTab(ThemeData theme, OrderHistoryState state) {
    return Column(
      children: [
        // 搜索和筛选栏
        _buildSearchAndFilterBar(theme, state),
        
        // 订单历史列表
        Expanded(
          child: state.errorMessage != null
              ? ErrorMessage(
                  message: state.errorMessage!,
                  onRetry: () => ref.read(orderHistoryProvider.notifier).loadOrderHistory(),
                )
              : OrderHistoryListWidget(
                  orderHistory: state.filteredOrderHistory,
                  onOrderTap: _showOrderDetail,
                ),
        ),
      ],
    );
  }

  Widget _buildStatsTab(ThemeData theme, OrderHistoryState state) {
    return state.stats != null
        ? OrderHistoryStatsWidget(stats: state.stats!)
        : const Center(child: CircularProgressIndicator());
  }

  Widget _buildRealTimeTab(ThemeData theme, OrderHistoryState state) {
    return RealTimeStatusWidget(
      realTimeStatus: state.realTimeStatus,
      onStatusTap: _showStatusDetail,
    );
  }

  Widget _buildSearchAndFilterBar(ThemeData theme, OrderHistoryState state) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 搜索框
          TextField(
            decoration: InputDecoration(
              labelText: '搜索订单',
              hintText: '输入交易对、交易所或策略名称',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              prefixIcon: const Icon(Icons.search),
            ),
            onChanged: (value) {
              ref.read(orderHistoryProvider.notifier).setSearchQuery(value);
            },
          ),
          const SizedBox(height: 12),
          
          // 快速筛选按钮
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildFilterChip(
                  '全部',
                  'all',
                  state.filterStatus,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  '成功',
                  'successful',
                  state.filterStatus,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  '失败',
                  'failed',
                  state.filterStatus,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  '执行中',
                  'executing',
                  state.filterStatus,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  '已完成',
                  'completed',
                  state.filterStatus,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  '待处理',
                  'pending',
                  state.filterStatus,
                  theme,
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          
          // 时间筛选
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildTimeFilterButton(
                  '今天',
                  () => ref.read(orderHistoryProvider.notifier).setQuickTimeFilter(showOnlyToday: true),
                  state.showOnlyToday,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildTimeFilterButton(
                  '本周',
                  () => ref.read(orderHistoryProvider.notifier).setQuickTimeFilter(showOnlyThisWeek: true),
                  state.showOnlyThisWeek,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildTimeFilterButton(
                  '本月',
                  () => ref.read(orderHistoryProvider.notifier).setQuickTimeFilter(showOnlyThisMonth: true),
                  state.showOnlyThisMonth,
                  theme,
                ),
                const SizedBox(width: 8),
                _buildTimeFilterButton(
                  '全部',
                  () => ref.read(orderHistoryProvider.notifier).setQuickTimeFilter(),
                  !(state.showOnlyToday || state.showOnlyThisWeek || state.showOnlyThisMonth),
                  theme,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, String value, String currentFilter, ThemeData theme) {
    final isSelected = currentFilter == value;
    
    return FilterChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          ref.read(orderHistoryProvider.notifier).setFilterStatus(value);
        }
      },
    );
  }

  Widget _buildTimeFilterButton(String label, VoidCallback onPressed, bool isSelected, ThemeData theme) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: isSelected ? theme.colorScheme.primary : theme.colorScheme.surface,
        foregroundColor: isSelected ? theme.colorScheme.onPrimary : theme.colorScheme.onSurface,
        elevation: isSelected ? 2 : 1,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      child: Text(label),
    );
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('高级筛选'),
        content: const Text('高级筛选功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showOrderDetail(OrderHistory order) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('订单详情 - ${order.symbol}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('订单ID: ${order.orderId}'),
              Text('交易对: ${order.symbol}'),
              Text('类型: ${order.orderType}'),
              Text('方向: ${order.orderSide}'),
              Text('数量: ${order.quantity}'),
              if (order.price != null) Text('价格: ${order.price}'),
              Text('执行状态: ${order.executionStatus.displayName}'),
              Text('成交数量: ${order.filledQuantity}'),
              if (order.averagePrice != null) Text('平均价格: ${order.averagePrice}'),
              if (order.commission != null) Text('手续费: ${order.commission}'),
              Text('开始时间: ${order.executionStartTime}'),
              if (order.executionEndTime != null) Text('结束时间: ${order.executionEndTime}'),
              if (order.executionDuration != null) Text('执行时长: ${order.formattedExecutionDuration}'),
              Text('交易所: ${order.exchange}'),
              if (order.accountName != null) Text('账户: ${order.accountName}'),
              if (order.autoOrderStrategyName != null) Text('策略: ${order.autoOrderStrategyName}'),
              if (order.errorMessage != null) Text('错误信息: ${order.errorMessage}'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showStatusDetail(RealTimeExecutionStatus status) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('执行状态 - 订单 ${status.orderId}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('当前状态: ${status.currentStatus.displayName}'),
              Text('执行进度: ${status.progressPercentage.toStringAsFixed(1)}%'),
              if (status.estimatedCompletionTime != null) 
                Text('预计完成: ${status.estimatedCompletionTime}'),
              Text('最后更新: ${status.lastUpdateTime}'),
              if (status.errorInfo != null) Text('错误信息: ${status.errorInfo}'),
              if (status.retryInfo != null) ...[
                const SizedBox(height: 8),
                Text('重试信息:'),
                Text('- 当前重试: ${status.retryInfo!['current_retry']}'),
                Text('- 最大重试: ${status.retryInfo!['max_retries']}'),
                Text('- 可以重试: ${status.retryInfo!['can_retry']}'),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showHelpDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('订单历史帮助'),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('订单历史功能说明：'),
              SizedBox(height: 8),
              Text('• 查看所有订单的执行历史记录'),
              Text('• 监控订单执行状态和进度'),
              Text('• 分析交易成功率和性能指标'),
              Text('• 实时跟踪正在执行的订单'),
              SizedBox(height: 16),
              Text('状态说明：'),
              SizedBox(height: 8),
              Text('• 待执行: 订单等待执行'),
              Text('• 执行中: 订单正在执行'),
              Text('• 成功: 订单执行成功'),
              Text('• 失败: 订单执行失败'),
              Text('• 部分成交: 订单部分成交'),
              Text('• 已取消: 订单被取消'),
              SizedBox(height: 16),
              Text('使用建议：'),
              SizedBox(height: 8),
              Text('• 定期检查执行失败的订单'),
              Text('• 关注执行时间过长的订单'),
              Text('• 查看统计信息了解整体表现'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('明白了'),
          ),
        ],
      ),
    );
  }
}