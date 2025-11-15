import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../domain/entities/auto_order.dart';
import '../../../domain/entities/trading_pair.dart';
import '../../../presentation/providers/auto_order/auto_order_provider.dart';
import '../../../presentation/providers/market/market_data_provider.dart';
import '../../../presentation/widgets/common/custom_card.dart';
import '../../../presentation/widgets/common/loading_overlay.dart';
import '../../../presentation/widgets/common/error_message.dart';
import '../../../presentation/widgets/auto_order/auto_order_form_widget.dart';
import '../../../presentation/widgets/auto_order/auto_order_list_widget.dart';
import '../../../presentation/widgets/auto_order/auto_order_detail_dialog.dart';

class AutoOrderConfigPage extends ConsumerStatefulWidget {
  const AutoOrderConfigPage({super.key});

  @override
  ConsumerState<AutoOrderConfigPage> createState() => _AutoOrderConfigPageState();
}

class _AutoOrderConfigPageState extends ConsumerState<AutoOrderConfigPage>
    with TickerProviderStateMixin {
  late TabController _tabController;
  bool _isCreatingOrder = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    
    // 加载初始数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(autoOrderProvider.notifier).loadAutoOrders();
      ref.read(tradingPairProvider.notifier).loadTradingPairs();
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
    final autoOrderState = ref.watch(autoOrderProvider);
    final tradingPairState = ref.watch(tradingPairProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('自动订单配置'),
        elevation: 0,
        backgroundColor: theme.colorScheme.surface,
        foregroundColor: theme.colorScheme.onSurface,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.list), text: '订单列表'),
            Tab(icon: Icon(Icons.add_circle_outline), text: '创建订单'),
            Tab(icon: Icon(Icons.analytics), text: '统计分析'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(autoOrderProvider.notifier).loadAutoOrders();
              ref.read(tradingPairProvider.notifier).loadTradingPairs();
            },
            tooltip: '刷新数据',
          ),
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: _showHelpDialog,
            tooltip: '帮助',
          ),
        ],
      ),
      body: LoadingOverlay(
        isLoading: autoOrderState.isLoading || tradingPairState.isLoading,
        child: Column(
          children: [
            // 快速统计卡片
            _buildQuickStats(theme, autoOrderState),
            
            // 主要内容区域
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // 订单列表标签页
                  _buildOrderListTab(theme, autoOrderState),
                  
                  // 创建订单标签页
                  _buildCreateOrderTab(theme, tradingPairState),
                  
                  // 统计分析标签页
                  _buildAnalyticsTab(theme, autoOrderState),
                ],
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: _isCreatingOrder
          ? FloatingActionButton(
              onPressed: () {
                setState(() {
                  _isCreatingOrder = false;
                });
              },
              child: const Icon(Icons.close),
            )
          : null,
    );
  }

  Widget _buildQuickStats(ThemeData theme, AutoOrderState autoOrderState) {
    final totalOrders = autoOrderState.autoOrders.length;
    final activeOrders = autoOrderState.autoOrders.where((o) => o.isActive).length;
    final pausedOrders = autoOrderState.autoOrders.where((o) => o.isPaused).length;
    final successfulExecutions = autoOrderState.autoOrders
        .where((o) => o.executionCount > 0)
        .length;

    return Container(
      margin: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: _buildStatCard(
              theme,
              '总订单数',
              totalOrders.toString(),
              Icons.list_alt,
              theme.colorScheme.primary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              theme,
              '活跃订单',
              activeOrders.toString(),
              Icons.play_circle,
              Colors.green,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              theme,
              '暂停订单',
              pausedOrders.toString(),
              Icons.pause_circle,
              Colors.orange,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              theme,
              '已执行',
              successfulExecutions.toString(),
              Icons.check_circle,
              Colors.blue,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(ThemeData theme, String title, String value, IconData icon, Color color) {
    return CustomCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Icon(icon, color: color, size: 24),
              Text(
                value,
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            title,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrderListTab(ThemeData theme, AutoOrderState autoOrderState) {
    return Column(
      children: [
        // 过滤器栏
        _buildFilterBar(theme),
        
        // 订单列表
        Expanded(
          child: autoOrderState.errorMessage != null
              ? ErrorMessage(
                  message: autoOrderState.errorMessage!,
                  onRetry: () => ref.read(autoOrderProvider.notifier).loadAutoOrders(),
                )
              : const AutoOrderListWidget(),
                  onOrderStatusChanged: _handleOrderStatusChanged,
                  onOrderDeleted: _handleOrderDeleted,
                ),
        ),
      ],
    );
  }

  Widget _buildCreateOrderTab(ThemeData theme, TradingPairState tradingPairState) {
    if (_isCreatingOrder) {
      return AutoOrderFormWidget(
        tradingPairs: tradingPairState.tradingPairs,
        onSubmit: _handleCreateOrder,
        onCancel: () => setState(() => _isCreatingOrder = false),
      );
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.add_circle_outline,
            size: 80,
            color: theme.colorScheme.onSurface.withOpacity(0.5),
          ),
          const SizedBox(height: 24),
          Text(
            '创建自动订单',
            style: theme.textTheme.headlineMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '配置自动交易策略，设置触发条件和风险控制参数',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.5),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            onPressed: () => setState(() => _isCreatingOrder = true),
            icon: const Icon(Icons.add),
            label: const Text('开始创建'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalyticsTab(ThemeData theme, AutoOrderState autoOrderState) {
    final totalOrders = autoOrderState.autoOrders.length;
    final activeOrders = autoOrderState.autoOrders.where((o) => o.isActive).length;
    final totalExecutions = autoOrderState.autoOrders.fold<int>(
        0, (sum, order) => sum + order.executionCount);
    final successfulOrders = autoOrderState.autoOrders
        .where((o) => o.lastExecutionResult?['success'] == true)
        .length;
    final successRate = totalOrders > 0 ? (successfulOrders / totalOrders * 100) : 0.0;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 概览卡片
          CustomCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '执行概况',
                  style: theme.textTheme.headlineSmall,
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _buildMetricItem(
                        theme,
                        '总执行次数',
                        totalExecutions.toString(),
                      ),
                    ),
                    Expanded(
                      child: _buildMetricItem(
                        theme,
                        '成功率',
                        '${successRate.toStringAsFixed(1)}%',
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          
          // 按策略分组统计
          CustomCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '按策略统计',
                  style: theme.textTheme.headlineSmall,
                ),
                const SizedBox(height: 16),
                ..._buildStrategyStats(theme, autoOrderState.autoOrders),
              ],
            ),
          ),
          const SizedBox(height: 16),
          
          // 按交易对分组统计
          CustomCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '按交易对统计',
                  style: theme.textTheme.headlineSmall,
                ),
                const SizedBox(height: 16),
                ..._buildSymbolStats(theme, autoOrderState.autoOrders),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: '状态筛选',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'all', child: Text('全部')),
                DropdownMenuItem(value: 'active', child: Text('活跃')),
                DropdownMenuItem(value: 'paused', child: Text('暂停')),
                DropdownMenuItem(value: 'expired', child: Text('已过期')),
              ],
              onChanged: (value) {
                ref.read(autoOrderProvider.notifier).setFilterStatus(value ?? 'all');
              },
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: TextFormField(
              decoration: const InputDecoration(
                labelText: '搜索策略或交易对',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.search),
              ),
              onChanged: (value) {
                ref.read(autoOrderProvider.notifier).setSearchQuery(value);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricItem(ThemeData theme, String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: theme.textTheme.headlineMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: Theme.of(context).colorScheme.primary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
      ],
    );
  }

  List<Widget> _buildStrategyStats(ThemeData theme, List<AutoOrder> autoOrders) {
    final strategyGroups = <String, List<AutoOrder>>{};
    
    for (final order in autoOrders) {
      strategyGroups.putIfAbsent(order.strategyName, () => []).add(order);
    }

    return strategyGroups.entries.map((entry) {
      final strategyName = entry.key;
      final orders = entry.value;
      final executions = orders.fold<int>(0, (sum, o) => sum + o.executionCount);
      final successCount = orders.where((o) => o.lastExecutionResult?['success'] == true).length;
      final successRate = orders.isNotEmpty ? (successCount / orders.length * 100) : 0.0;

      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            Icon(
              Icons.account_tree,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    strategyName,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Text(
                    '${orders.length}个订单 • ${executions}次执行 • ${successRate.toStringAsFixed(1)}%成功率',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }).toList();
  }

  List<Widget> _buildSymbolStats(ThemeData theme, List<AutoOrder> autoOrders) {
    final symbolGroups = <String, List<AutoOrder>>{};
    
    for (final order in autoOrders) {
      symbolGroups.putIfAbsent(order.symbol, () => []).add(order);
    }

    return symbolGroups.entries.map((entry) {
      final symbol = entry.key;
      final orders = entry.value;
      final executions = orders.fold<int>(0, (sum, o) => sum + o.executionCount);

      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            Icon(
              Icons.currency_bitcoin,
              color: theme.colorScheme.secondary,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    symbol,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Text(
                    '${orders.length}个订单 • ${executions}次执行',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }).toList();
  }

  void _showOrderDetail(AutoOrder order) {
    showDialog(
      context: context,
      builder: (context) => AutoOrderDetailDialog(order: order),
    );
  }

  void _handleOrderStatusChanged(AutoOrder order, bool isActive) {
    ref.read(autoOrderProvider.notifier).toggleOrderStatus(order.id, isActive);
  }

  void _handleOrderDeleted(AutoOrder order) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除'),
        content: Text('确定要删除自动订单 "${order.strategyName}" 吗？此操作不可撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              ref.read(autoOrderProvider.notifier).deleteAutoOrder(order.id);
            },
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  void _handleCreateOrder(CreateAutoOrderRequest request) async {
    try {
      await ref.read(autoOrderProvider.notifier).createAutoOrder(request);
      setState(() => _isCreatingOrder = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('自动订单创建成功'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('创建失败: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showHelpDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('自动订单帮助'),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('自动订单允许您：'),
              SizedBox(height: 8),
              Text('• 设置条件触发自动交易'),
              Text('• 配置止损止盈风险控制'),
              Text('• 监控订单执行状态'),
              Text('• 查看交易统计分析'),
              SizedBox(height: 16),
              Text('注意事项：'),
              SizedBox(height: 8),
              Text('• 请确保已配置风险管理参数'),
              Text('• 定期检查订单执行情况'),
              Text('• 谨慎设置交易数量和风险参数'),
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