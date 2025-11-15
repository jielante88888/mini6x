import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../providers/strategy_provider.dart';
import '../../widgets/common/app_bar_widget.dart';
import '../../widgets/common/loading_widget.dart';
import '../../widgets/common/error_widget.dart' as custom_error;
import '../../widgets/common/floating_action_button_widget.dart';
import '../../widgets/strategies/performance_chart_widget.dart';
import '../../widgets/strategies/performance_report_widget.dart';

/// 现货策略页面
/// 提供策略的配置、管理、监控和性能分析功能
class SpotStrategyPage extends ConsumerStatefulWidget {
  const SpotStrategyPage({super.key});

  @override
  ConsumerState<SpotStrategyPage> createState() => _SpotStrategyPageState();
}

class _SpotStrategyPageState extends ConsumerState<SpotStrategyPage>
    with TickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  // 筛选状态
  String _selectedStrategyType = 'all';
  String _selectedStatus = 'all';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    
    // 监听搜索框变化
    _searchController.addListener(() {
      setState(() {});
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final strategyState = ref.watch(strategyProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('现货策略'),
        elevation: 0,
        backgroundColor: theme.colorScheme.surface,
        foregroundColor: theme.colorScheme.onSurface,
        actions: [
          // 刷新按钮
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: strategyState.apiState == ApiState.loading
                ? null
                : () => ref.read(strategyProvider.notifier).refreshStrategies(),
          ),
          // 设置按钮
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showGlobalSettings(),
          ),
          const SizedBox(width: 8),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          labelColor: theme.colorScheme.primary,
          unselectedLabelColor: theme.colorScheme.onSurfaceVariant,
          indicatorColor: theme.colorScheme.primary,
          tabs: const [
            Tab(text: '策略管理'),
            Tab(text: '性能监控'),
            Tab(text: '策略对比'),
          ],
        ),
      ),
      body: _buildBody(strategyState),
      floatingActionButton: _buildFloatingActionButton(),
    );
  }

  Widget _buildBody(StrategyState strategyState) {
    switch (strategyState.apiState) {
      case ApiState.loading:
        return const Center(child: LoadingWidget(message: '加载策略数据...'));
      case ApiState.error:
        return custom_error.ErrorWidget(
          message: strategyState.error ?? '加载策略失败',
          onRetry: () => ref.read(strategyProvider.notifier).refreshStrategies(),
        );
      case ApiState.success:
      case ApiState.initial:
        return TabBarView(
          controller: _tabController,
          children: [
            _buildStrategyManagementTab(),
            _buildPerformanceMonitorTab(),
            _buildStrategyComparisonTab(),
          ],
        );
    }
  }

  Widget _buildStrategyManagementTab() {
    final filteredStrategies = _getFilteredStrategies();
    
    return Column(
      children: [
        // 搜索和筛选栏
        _buildSearchAndFilterBar(),
        
        // 策略列表
        Expanded(
          child: filteredStrategies.isEmpty
              ? _buildEmptyState()
              : _buildStrategyList(filteredStrategies),
        ),
      ],
    );
  }

  Widget _buildSearchAndFilterBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      child: Column(
        children: [
          // 搜索框
          TextField(
            controller: _searchController,
            decoration: const InputDecoration(
              hintText: '搜索策略名称或交易对...',
              prefixIcon: Icon(Icons.search),
              border: OutlineInputBorder(),
              contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
          ),
          const SizedBox(height: 12),
          // 筛选选项
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _selectedStrategyType,
                  decoration: const InputDecoration(
                    labelText: '策略类型',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('全部')),
                    DropdownMenuItem(value: 'grid', child: Text('网格策略')),
                    DropdownMenuItem(value: 'martingale', child: Text('马丁格尔策略')),
                    DropdownMenuItem(value: 'arbitrage', child: Text('套利策略')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _selectedStrategyType = value ?? 'all';
                    });
                  },
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _selectedStatus,
                  decoration: const InputDecoration(
                    labelText: '状态',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('全部')),
                    DropdownMenuItem(value: 'inactive', child: Text('未启动')),
                    DropdownMenuItem(value: 'running', child: Text('运行中')),
                    DropdownMenuItem(value: 'paused', child: Text('已暂停')),
                    DropdownMenuItem(value: 'stopped', child: Text('已停止')),
                    DropdownMenuItem(value: 'error', child: Text('错误')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _selectedStatus = value ?? 'all';
                    });
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStrategyList(List<StrategyConfig> strategies) {
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16),
      itemCount: strategies.length,
      itemBuilder: (context, index) {
        final strategy = strategies[index];
        return _buildStrategyCard(strategy);
      },
    );
  }

  Widget _buildStrategyCard(StrategyConfig strategy) {
    final theme = Theme.of(context);
    final performance = ref.read(strategyProvider.notifier).getStrategyPerformance(strategy.id);
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _showStrategyDetails(strategy),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 策略头部信息
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          strategy.name,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${strategy.symbol} • ${strategy.exchange}',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  _buildStatusChip(strategy.status),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // 策略参数摘要
              Row(
                children: [
                  _buildInfoChip(
                    icon: Icons.account_balance_wallet,
                    label: '基础数量',
                    value: NumberFormat('#,###.##').format(strategy.baseQuantity),
                  ),
                  const SizedBox(width: 8),
                  _buildInfoChip(
                    icon: Icons.trending_up,
                    label: '盈利目标',
                    value: '${strategy.profitTarget}%',
                  ),
                  const SizedBox(width: 8),
                  _buildInfoChip(
                    icon: Icons.shield,
                    label: '止损',
                    value: '${strategy.stopLoss}%',
                  ),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // 性能数据
              if (performance != null) ...[
                Row(
                  children: [
                    Expanded(
                      child: _buildPerformanceMetric(
                        label: '总盈亏',
                        value: '${NumberFormat('+#,###.##;-#,###.##').format(performance.netPnL)}',
                        color: performance.netPnL >= 0 ? Colors.green : Colors.red,
                      ),
                    ),
                    Expanded(
                      child: _buildPerformanceMetric(
                        label: '胜率',
                        value: '${(performance.winRate * 100).toStringAsFixed(1)}%',
                        color: theme.colorScheme.primary,
                      ),
                    ),
                    Expanded(
                      child: _buildPerformanceMetric(
                        label: '交易次数',
                        value: performance.totalTrades.toString(),
                        color: theme.colorScheme.tertiary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: _buildPerformanceMetric(
                        label: '夏普比率',
                        value: performance.sharpeRatio.toStringAsFixed(2),
                        color: theme.colorScheme.secondary,
                      ),
                    ),
                    Expanded(
                      child: _buildPerformanceMetric(
                        label: '最大回撤',
                        value: '${(performance.maxDrawdown * 100).toStringAsFixed(1)}%',
                        color: Colors.orange,
                      ),
                    ),
                    Expanded(
                      child: _buildPerformanceMetric(
                        label: '总收益率',
                        value: '${(performance.totalReturns * 100).toStringAsFixed(1)}%',
                        color: performance.totalReturns >= 0 ? Colors.green : Colors.red,
                      ),
                    ),
                  ],
                ),
              ],
              
              const SizedBox(height: 12),
              
              // 操作按钮
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: () => _editStrategy(strategy),
                    icon: const Icon(Icons.edit, size: 16),
                    label: const Text('编辑'),
                  ),
                  const SizedBox(width: 8),
                  if (strategy.status == StrategyStatus.inactive || 
                      strategy.status == StrategyStatus.stopped) ...[
                    ElevatedButton.icon(
                      onPressed: () => _startStrategy(strategy.id),
                      icon: const Icon(Icons.play_arrow, size: 16),
                      label: const Text('启动'),
                    ),
                  ] else if (strategy.status == StrategyStatus.running) ...[
                    ElevatedButton.icon(
                      onPressed: () => _pauseStrategy(strategy.id),
                      icon: const Icon(Icons.pause, size: 16),
                      label: const Text('暂停'),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton.icon(
                      onPressed: () => _stopStrategy(strategy.id),
                      icon: const Icon(Icons.stop, size: 16),
                      label: const Text('停止'),
                    ),
                  ] else if (strategy.status == StrategyStatus.paused) ...[
                    ElevatedButton.icon(
                      onPressed: () => _resumeStrategy(strategy.id),
                      icon: const Icon(Icons.play_arrow, size: 16),
                      label: const Text('恢复'),
                    ),
                  ],
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: () => _deleteStrategy(strategy),
                    icon: const Icon(Icons.delete, color: Colors.red),
                    tooltip: '删除策略',
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusChip(StrategyStatus status) {
    Color color;
    IconData icon;
    
    switch (status) {
      case StrategyStatus.running:
        color = Colors.green;
        icon = Icons.play_circle;
        break;
      case StrategyStatus.paused:
        color = Colors.orange;
        icon = Icons.pause_circle;
        break;
      case StrategyStatus.stopped:
        color = Colors.grey;
        icon = Icons.stop_circle;
        break;
      case StrategyStatus.error:
        color = Colors.red;
        icon = Icons.error_circle;
        break;
      case StrategyStatus.inactive:
      default:
        color = Colors.blue;
        icon = Icons.stop;
        break;
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            status.displayName,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoChip({required IconData icon, required String label, required String value}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: Theme.of(context).colorScheme.onSurfaceVariant),
          const SizedBox(width: 4),
          Text(
            '$label: $value',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceMetric({required String label, required String value, required Color color}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildPerformanceMonitorTab() {
    return Column(
      children: [
        // 策略选择器
        _buildStrategySelector(),
        
        // 图表类型选择器
        _buildChartTypeSelector(),
        
        // 图表和性能指标
        Expanded(
          child: _buildPerformanceContent(),
        ),
      ],
    );
  }

  Widget _buildStrategySelector() {
    final strategyState = ref.read(strategyProvider);
    final activeStrategies = strategyState.strategies.where((s) => s.isActive).toList();
    
    return Container(
      padding: const EdgeInsets.all(16),
      child: DropdownButtonFormField<StrategyConfig>(
        value: activeStrategies.isNotEmpty ? activeStrategies.first : null,
        decoration: const InputDecoration(
          labelText: '选择策略',
          border: OutlineInputBorder(),
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ),
        items: activeStrategies.map((strategy) {
          return DropdownMenuItem(
            value: strategy,
            child: Text('${strategy.name} (${strategy.symbol})'),
          );
        }).toList(),
        onChanged: (strategy) {
          setState(() {
            // 重新构建图表
          });
        },
      ),
    );
  }

  ChartType _selectedChartType = ChartType.pnl;
  String _selectedStrategyId = '';

  Widget _buildChartTypeSelector() {
    return Container(
      height: 50,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: ChartType.values.map((type) {
          final isSelected = type == _selectedChartType;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Text(type.displayName),
              selected: isSelected,
              onSelected: (selected) {
                if (selected) {
                  setState(() {
                    _selectedChartType = type;
                  });
                }
              },
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildPerformanceContent() {
    final strategyState = ref.read(strategyProvider);
    if (strategyState.strategies.isEmpty) {
      return const Center(
        child: Text('暂无活跃策略'),
      );
    }

    final strategy = strategyState.strategies.firstWhere(
      (s) => s.isActive,
      orElse: () => strategyState.strategies.first,
    );
    
    final performance = ref.read(strategyProvider.notifier).getStrategyPerformance(strategy.id);
    
    if (performance == null) {
      return const Center(
        child: LoadingWidget(message: '加载性能数据...'),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 性能指标卡片
          PerformanceMetricsCard(performance: performance),
          const SizedBox(height: 16),
          
          // 性能图表
          // 模拟性能数据
          _buildPerformanceChart(strategy.id, performance),
          const SizedBox(height: 16),
          
          // 性能报告
          PerformanceReportWidget(
            strategy: strategy,
            performance: performance,
          ),
          const SizedBox(height: 16),
          
          // 报告历史
          ReportHistoryWidget(strategyId: strategy.id),
        ],
      ),
    );
  }

  Widget _buildPerformanceChart(String strategyId, StrategyPerformance currentPerformance) {
    // 模拟历史性能数据
    final List<StrategyPerformance> performanceData = List.generate(30, (index) {
      final date = DateTime.now().subtract(Duration(days: 29 - index));
      return StrategyPerformance(
        strategyId: strategyId,
        totalPnL: currentPerformance.totalPnL * (0.5 + index / 30.0),
        totalCommission: currentPerformance.totalCommission * (0.5 + index / 30.0),
        netPnL: currentPerformance.netPnL * (0.5 + index / 30.0),
        winRate: currentPerformance.winRate * (0.8 + (index % 10) / 50.0),
        profitFactor: currentPerformance.profitFactor,
        maxDrawdown: currentPerformance.maxDrawdown * (0.5 + index / 30.0),
        currentDrawdown: currentPerformance.currentDrawdown * (0.5 + index / 30.0),
        sharpeRatio: currentPerformance.sharpeRatio * (0.5 + index / 30.0),
        sortinoRatio: currentPerformance.sortinoRatio * (0.5 + index / 30.0),
        totalReturns: currentPerformance.totalReturns * (0.5 + index / 30.0),
        totalTrades: (currentPerformance.totalTrades * (index + 1) / 30).round(),
        lastUpdated: date,
      );
    });

    return PerformanceChartWidget(
      strategyId: strategyId,
      chartType: _selectedChartType,
      performanceData: performanceData,
    );
  }

  Widget _buildStrategyComparisonTab() {
    return _buildStrategyComparisonContent();
  }

  Widget _buildStrategyComparisonContent() {
    final strategyState = ref.read(strategyProvider);
    final allStrategies = strategyState.strategies;
    
    if (allStrategies.isEmpty) {
      return const Center(
        child: Text('暂无策略数据'),
      );
    }

    // 获取性能数据
    final performanceData = allStrategies.map((strategy) {
      final performance = ref.read(strategyProvider.notifier).getStrategyPerformance(strategy.id);
      return performance;
    }).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 策略对比说明
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(
                    Icons.compare_arrows,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '策略对比分析帮助您了解不同策略的相对表现，选择最适合您风险偏好的策略。',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          
          // 策略对比组件
          StrategyComparisonWidget(
            strategies: allStrategies,
            performanceData: performanceData.whereType<StrategyPerformance>().toList(),
          ),
          const SizedBox(height: 16),
          
          // 对比图表
          _buildComparisonCharts(allStrategies, performanceData.whereType<StrategyPerformance>().toList()),
        ],
      ),
    );
  }

  Widget _buildComparisonCharts(List<StrategyConfig> strategies, List<StrategyPerformance> performanceData) {
    if (strategies.length < 2) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Center(
            child: Text(
              '需要至少2个策略才能进行对比',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ),
      );
    }

    return Column(
      children: [
        // 性能对比雷达图
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '性能对比雷达图',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  height: 300,
                  child: _buildRadarChart(strategies, performanceData),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        
        // 收益对比柱状图
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '收益对比',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  height: 200,
                  child: _buildReturnsBarChart(strategies, performanceData),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRadarChart(List<StrategyConfig> strategies, List<StrategyPerformance> performanceData) {
    // TODO: 实现雷达图
    return Center(
      child: Text(
        '雷达图功能开发中...\n将显示多个维度的策略对比',
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }

  Widget _buildReturnsBarChart(List<StrategyConfig> strategies, List<StrategyPerformance> performanceData) {
    // TODO: 实现柱状图
    return Center(
      child: Text(
        '柱状图功能开发中...\n将显示各策略的收益对比',
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.strategy,
            size: 64,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            '暂无策略',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '点击右下角按钮创建你的第一个策略',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildFloatingActionButton() {
    return FloatingActionButtonWidget(
      onPressed: () => _createNewStrategy(),
      icon: Icons.add,
      label: '新建策略',
    );
  }

  // 筛选策略
  List<StrategyConfig> _getFilteredStrategies() {
    final strategyState = ref.read(strategyProvider);
    var filtered = strategyState.strategies;
    
    // 搜索过滤
    if (_searchController.text.isNotEmpty) {
      final query = _searchController.text.toLowerCase();
      filtered = filtered.where((strategy) {
        return strategy.name.toLowerCase().contains(query) ||
               strategy.symbol.toLowerCase().contains(query);
      }).toList();
    }
    
    // 策略类型过滤
    if (_selectedStrategyType != 'all') {
      filtered = filtered.where((strategy) {
        return strategy.type.value == _selectedStrategyType;
      }).toList();
    }
    
    // 状态过滤
    if (_selectedStatus != 'all') {
      filtered = filtered.where((strategy) {
        return strategy.status.value == _selectedStatus;
      }).toList();
    }
    
    return filtered;
  }

  // 事件处理方法
  void _createNewStrategy() async {
    final result = await showModalBottomSheet<StrategyConfig>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildStrategyConfigSheet(),
    );
    
    if (result != null) {
      final success = await ref.read(strategyProvider.notifier).createStrategy(result);
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('策略创建成功')),
        );
      }
    }
  }

  void _editStrategy(StrategyConfig strategy) async {
    final result = await showModalBottomSheet<StrategyConfig>(
      context: context,
      isScrollPersistent: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildStrategyConfigSheet(strategy: strategy),
    );
    
    if (result != null) {
      final success = await ref.read(strategyProvider.notifier).updateStrategy(strategy.id, result);
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('策略更新成功')),
        );
      }
    }
  }

  void _showStrategyDetails(StrategyConfig strategy) {
    // TODO: 实现策略详情页面
  }

  void _startStrategy(String id) async {
    final success = await ref.read(strategyProvider.notifier).startStrategy(id);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('策略启动成功')),
      );
    }
  }

  void _pauseStrategy(String id) async {
    final success = await ref.read(strategyProvider.notifier).pauseStrategy(id);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('策略暂停成功')),
      );
    }
  }

  void _stopStrategy(String id) async {
    final success = await ref.read(strategyProvider.notifier).stopStrategy(id);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('策略停止成功')),
      );
    }
  }

  void _resumeStrategy(String id) async {
    final success = await ref.read(strategyProvider.notifier).startStrategy(id);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('策略恢复成功')),
      );
    }
  }

  void _deleteStrategy(StrategyConfig strategy) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除策略'),
        content: Text('确定要删除策略 "${strategy.name}" 吗？此操作不可撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    
    if (confirmed == true) {
      final success = await ref.read(strategyProvider.notifier).deleteStrategy(strategy.id);
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('策略删除成功')),
        );
      }
    }
  }

  void _showGlobalSettings() {
    // TODO: 实现全局设置
  }

  Widget _buildStrategyConfigSheet({StrategyConfig? strategy}) {
    return StrategyConfigSheet(existingStrategy: strategy);
  }
}

/// 策略配置表单组件
class StrategyConfigSheet extends StatefulWidget {
  final StrategyConfig? existingStrategy;

  const StrategyConfigSheet({super.key, this.existingStrategy});

  @override
  State<StrategyConfigSheet> createState() => _StrategyConfigSheetState();
}

class _StrategyConfigSheetState extends State<StrategyConfigSheet> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _symbolController = TextEditingController();
  final _exchangeController = TextEditingController();
  final _baseQuantityController = TextEditingController();
  final _minOrderSizeController = TextEditingController();
  final _maxOrderSizeController = TextEditingController();
  final _profitTargetController = TextEditingController();
  final _stopLossController = TextEditingController();
  
  // 策略特定参数
  final _gridLevelsController = TextEditingController();
  final _gridSpacingController = TextEditingController();
  final _martingaleMultiplierController = TextEditingController();
  final _maxMartingaleStepsController = TextEditingController();
  final _arbitrageThresholdController = TextEditingController();

  StrategyType _selectedType = StrategyType.grid;
  List<String> _targetExchanges = [];

  @override
  void initState() {
    super.initState();
    
    if (widget.existingStrategy != null) {
      final strategy = widget.existingStrategy!;
      _nameController.text = strategy.name;
      _symbolController.text = strategy.symbol;
      _exchangeController.text = strategy.exchange;
      _baseQuantityController.text = strategy.baseQuantity.toString();
      _minOrderSizeController.text = strategy.minOrderSize.toString();
      _maxOrderSizeController.text = strategy.maxOrderSize.toString();
      _profitTargetController.text = strategy.profitTarget.toString();
      _stopLossController.text = strategy.stopLoss.toString();
      _selectedType = strategy.type;
      
      if (strategy.gridLevels != null) {
        _gridLevelsController.text = strategy.gridLevels.toString();
      }
      if (strategy.gridSpacing != null) {
        _gridSpacingController.text = strategy.gridSpacing.toString();
      }
      if (strategy.martingaleMultiplier != null) {
        _martingaleMultiplierController.text = strategy.martingaleMultiplier.toString();
      }
      if (strategy.maxMartingaleSteps != null) {
        _maxMartingaleStepsController.text = strategy.maxMartingaleSteps.toString();
      }
      if (strategy.arbitrageThreshold != null) {
        _arbitrageThresholdController.text = strategy.arbitrageThreshold.toString();
      }
      if (strategy.targetExchanges != null) {
        _targetExchanges = List.from(strategy.targetExchanges!);
      }
    } else {
      // 设置默认值
      _baseQuantityController.text = '0.001';
      _minOrderSizeController.text = '0.001';
      _maxOrderSizeController.text = '0.1';
      _profitTargetController.text = '2.0';
      _stopLossController.text = '1.0';
      _gridLevelsController.text = '5';
      _gridSpacingController.text = '0.02';
      _martingaleMultiplierController.text = '2.0';
      _maxMartingaleStepsController.text = '5';
      _arbitrageThresholdController.text = '0.5';
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _symbolController.dispose();
    _exchangeController.dispose();
    _baseQuantityController.dispose();
    _minOrderSizeController.dispose();
    _maxOrderSizeController.dispose();
    _profitTargetController.dispose();
    _stopLossController.dispose();
    _gridLevelsController.dispose();
    _gridSpacingController.dispose();
    _martingaleMultiplierController.dispose();
    _maxMartingaleStepsController.dispose();
    _arbitrageThresholdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      height: MediaQuery.of(context).size.height * 0.9,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        children: [
          // 拖拽条
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: theme.colorScheme.onSurfaceVariant,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          
          // 标题栏
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Text(
                  widget.existingStrategy != null ? '编辑策略' : '创建策略',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
          ),
          
          // 表单内容
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildBasicInfoSection(),
                    const SizedBox(height: 24),
                    _buildRiskControlSection(),
                    const SizedBox(height: 24),
                    _buildStrategySpecificSection(),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
          ),
          
          // 底部按钮
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('取消'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _saveStrategy,
                    child: Text(widget.existingStrategy != null ? '保存' : '创建'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBasicInfoSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '基本信息',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _nameController,
          decoration: const InputDecoration(
            labelText: '策略名称',
            hintText: '输入策略名称',
            border: OutlineInputBorder(),
          ),
          validator: (value) {
            if (value?.trim().isEmpty ?? true) {
              return '请输入策略名称';
            }
            return null;
          },
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _symbolController,
                decoration: const InputDecoration(
                  labelText: '交易对',
                  hintText: 'BTC/USDT',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入交易对';
                  }
                  return null;
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: DropdownButtonFormField<StrategyType>(
                value: _selectedType,
                decoration: const InputDecoration(
                  labelText: '策略类型',
                  border: OutlineInputBorder(),
                ),
                items: StrategyType.values.map((type) {
                  return DropdownMenuItem(
                    value: type,
                    child: Text(type.displayName),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedType = value ?? StrategyType.grid;
                  });
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _exchangeController,
          decoration: const InputDecoration(
            labelText: '交易所',
            hintText: 'binance',
            border: OutlineInputBorder(),
          ),
          validator: (value) {
            if (value?.trim().isEmpty ?? true) {
              return '请输入交易所';
            }
            return null;
          },
        ),
      ],
    );
  }

  Widget _buildRiskControlSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '风险控制',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _baseQuantityController,
          decoration: const InputDecoration(
            labelText: '基础数量',
            hintText: '0.001',
            border: OutlineInputBorder(),
          ),
          keyboardType: TextInputType.number,
          validator: (value) {
            if (value?.trim().isEmpty ?? true) {
              return '请输入基础数量';
            }
            return null;
          },
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _minOrderSizeController,
                decoration: const InputDecoration(
                  labelText: '最小订单大小',
                  hintText: '0.001',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入最小订单大小';
                  }
                  return null;
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextFormField(
                controller: _maxOrderSizeController,
                decoration: const InputDecoration(
                  labelText: '最大订单大小',
                  hintText: '0.1',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入最大订单大小';
                  }
                  return null;
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _profitTargetController,
                decoration: const InputDecoration(
                  labelText: '盈利目标 (%)',
                  hintText: '2.0',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入盈利目标';
                  }
                  return null;
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextFormField(
                controller: _stopLossController,
                decoration: const InputDecoration(
                  labelText: '止损 (%)',
                  hintText: '1.0',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入止损';
                  }
                  return null;
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStrategySpecificSection() {
    switch (_selectedType) {
      case StrategyType.grid:
        return _buildGridStrategySection();
      case StrategyType.martingale:
        return _buildMartingaleStrategySection();
      case StrategyType.arbitrage:
        return _buildArbitrageStrategySection();
    }
  }

  Widget _buildGridStrategySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '网格策略参数',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _gridLevelsController,
                decoration: const InputDecoration(
                  labelText: '网格层数',
                  hintText: '5',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入网格层数';
                  }
                  return null;
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextFormField(
                controller: _gridSpacingController,
                decoration: const InputDecoration(
                  labelText: '网格间距',
                  hintText: '0.02',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入网格间距';
                  }
                  return null;
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMartingaleStrategySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '马丁格尔策略参数',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _martingaleMultiplierController,
                decoration: const InputDecoration(
                  labelText: '马丁格尔倍数',
                  hintText: '2.0',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入马丁格尔倍数';
                  }
                  return null;
                },
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextFormField(
                controller: _maxMartingaleStepsController,
                decoration: const InputDecoration(
                  labelText: '最大步数',
                  hintText: '5',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value?.trim().isEmpty ?? true) {
                    return '请输入最大步数';
                  }
                  return null;
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildArbitrageStrategySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '套利策略参数',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _arbitrageThresholdController,
          decoration: const InputDecoration(
            labelText: '套利阈值 (%)',
            hintText: '0.5',
            border: OutlineInputBorder(),
          ),
          keyboardType: TextInputType.number,
          validator: (value) {
            if (value?.trim().isEmpty ?? true) {
              return '请输入套利阈值';
            }
            return null;
          },
        ),
        const SizedBox(height: 16),
        Text(
          '目标交易所',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: ['binance', 'okx'].map((exchange) {
            return FilterChip(
              label: Text(exchange),
              selected: _targetExchanges.contains(exchange),
              onSelected: (selected) {
                setState(() {
                  if (selected) {
                    _targetExchanges.add(exchange);
                  } else {
                    _targetExchanges.remove(exchange);
                  }
                });
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  void _saveStrategy() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final config = StrategyConfig(
      id: widget.existingStrategy?.id ?? 'strategy_${DateTime.now().millisecondsSinceEpoch}',
      name: _nameController.text.trim(),
      type: _selectedType,
      symbol: _symbolController.text.trim().toUpperCase(),
      exchange: _exchangeController.text.trim(),
      baseQuantity: double.parse(_baseQuantityController.text),
      minOrderSize: double.parse(_minOrderSizeController.text),
      maxOrderSize: double.parse(_maxOrderSizeController.text),
      profitTarget: double.parse(_profitTargetController.text),
      stopLoss: double.parse(_stopLossController.text),
      isActive: true,
      status: StrategyStatus.inactive,
      createdAt: widget.existingStrategy?.createdAt ?? DateTime.now(),
      updatedAt: DateTime.now(),
      gridLevels: _gridLevelsController.text.isNotEmpty 
        ? int.parse(_gridLevelsController.text) 
        : null,
      gridSpacing: _gridSpacingController.text.isNotEmpty 
        ? double.parse(_gridSpacingController.text) 
        : null,
      martingaleMultiplier: _martingaleMultiplierController.text.isNotEmpty 
        ? double.parse(_martingaleMultiplierController.text) 
        : null,
      maxMartingaleSteps: _maxMartingaleStepsController.text.isNotEmpty 
        ? int.parse(_maxMartingaleStepsController.text) 
        : null,
      arbitrageThreshold: _arbitrageThresholdController.text.isNotEmpty 
        ? double.parse(_arbitrageThresholdController.text) 
        : null,
      targetExchanges: _targetExchanges.isNotEmpty ? _targetExchanges : null,
    );

    Navigator.of(context).pop(config);
  }
}