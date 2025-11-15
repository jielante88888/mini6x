import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/condition_monitor_provider.dart';
import '../../providers/conditions_provider.dart';
import '../../widgets/common/app_bar_widget.dart';
import '../../widgets/common/loading_widget.dart';
import '../../widgets/common/error_widget.dart';

/// 条件监控页面
/// 实时显示条件状态、执行统计和监控信息
class ConditionMonitorPage extends ConsumerStatefulWidget {
  const ConditionMonitorPage({super.key});

  @override
  ConsumerState<ConditionMonitorPage> createState() => _ConditionMonitorPageState();
}

class _ConditionMonitorPageState extends ConsumerState<ConditionMonitorPage> {
  final PageController _pageController = PageController();
  int _selectedIndex = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final monitorState = ref.watch(conditionMonitorProvider);
    final statistics = ref.watch(conditionStatisticsProvider);

    return Scaffold(
      appBar: AppBarWidget(
        title: '条件监控',
        actions: [
          IconButton(
            onPressed: () => _showMonitorHelp(),
            icon: const Icon(Icons.help_outline),
            tooltip: '监控帮助',
          ),
          IconButton(
            onPressed: () => _refreshData(),
            icon: const Icon(Icons.refresh),
            tooltip: '刷新数据',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(120),
          child: Container(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                // 实时状态卡片
                _buildRealtimeStatusCard(context, statistics),
                const SizedBox(height: 8),
                // Tab栏
                TabBar(
                  onTap: (index) {
                    setState(() {
                      _selectedIndex = index;
                    });
                    _pageController.animateToPage(
                      index,
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut,
                    );
                  },
                  indicatorColor: theme.colorScheme.primary,
                  labelColor: theme.colorScheme.primary,
                  unselectedLabelColor: theme.colorScheme.onSurface.withOpacity(0.6),
                  tabs: const [
                    Tab(icon: Icon(Icons.dashboard), text: '实时监控'),
                    Tab(icon: Icon(Icons.analytics), text: '性能分析'),
                    Tab(icon: Icon(Icons.history), text: '执行历史'),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
      body: monitorState.isLoading
          ? const LoadingWidget(message: '正在加载监控数据...')
          : monitorState.error != null
              ? ErrorWidget(
                  message: monitorState.error!,
                  onRetry: () {
                    ref.read(conditionMonitorProvider.notifier).clearError();
                    ref.refresh(conditionMonitorProvider);
                  },
                )
              : _buildTabContent(),
    );
  }

  /// 构建实时状态卡片
  Widget _buildRealtimeStatusCard(BuildContext context, Map<String, dynamic> stats) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            // 活跃条件数
            Expanded(
              child: _buildRealtimeStat(
                context,
                '活跃',
                '${stats['active_conditions']}/${stats['total_conditions']}',
                Icons.play_circle,
                Colors.green,
              ),
            ),
            Container(
              width: 1,
              height: 30,
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
            // 评估中
            Expanded(
              child: _buildRealtimeStat(
                context,
                '评估',
                '${stats['evaluating_conditions']}',
                Icons.hourglass_empty,
                Colors.orange,
              ),
            ),
            Container(
              width: 1,
              height: 30,
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
            // 总触发数
            Expanded(
              child: _buildRealtimeStat(
                context,
                '触发',
                '${stats['total_triggers']}',
                Icons.flash_on,
                Colors.blue,
              ),
            ),
            Container(
              width: 1,
              height: 30,
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
            // 成功率
            Expanded(
              child: _buildRealtimeStat(
                context,
                  '成功率',
                  '${(stats['overall_success_rate'] * 100).toStringAsFixed(1)}%',
                  Icons.trending_up,
                  Colors.purple,
                ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建实时统计项
  Widget _buildRealtimeStat(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 16),
        const SizedBox(height: 2),
        Text(
          value,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: color,
                fontWeight: FontWeight.bold,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
        ),
      ],
    );
  }

  /// 构建Tab内容
  Widget _buildTabContent() {
    return PageView(
      controller: _pageController,
      onPageChanged: (index) {
        setState(() {
          _selectedIndex = index;
        });
      },
      children: const [
        _RealtimeMonitorTab(),
        _PerformanceAnalysisTab(),
        _ExecutionHistoryTab(),
      ],
    );
  }

  /// 刷新数据
  void _refreshData() {
    ref.refresh(conditionMonitorProvider);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('监控数据已刷新')),
    );
  }

  /// 显示帮助
  void _showMonitorHelp() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('条件监控帮助'),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('实时监控'),
              SizedBox(height: 8),
              Text('• 显示所有条件的实时状态'),
              Text('• 监控条件评估和触发情况'),
              Text('• 提供快速状态概览'),
              SizedBox(height: 16),
              Text('性能分析'),
              SizedBox(height: 8),
              Text('• 分析条件执行性能指标'),
              Text('• 显示成功率和响应时间'),
              Text('• 提供优化建议'),
              SizedBox(height: 16),
              Text('执行历史'),
              SizedBox(height: 8),
              Text('• 记录条件触发的历史'),
              Text('• 分析触发模式和时间'),
              Text('• 支持条件统计重置'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }
}

/// 实时监控Tab
class _RealtimeMonitorTab extends ConsumerWidget {
  const _RealtimeMonitorTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final monitorState = ref.watch(conditionMonitorProvider);
    final conditionsByStatus = ref.watch(conditionsByStatusProvider);
    final typeStats = ref.watch(conditionTypeStatsProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.refresh(conditionMonitorProvider),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 条件类型分布
          _buildTypeDistribution(context, typeStats),
          const SizedBox(height: 16),
          // 按状态分组显示条件
          ...conditionsByStatus.entries.map(
            (entry) => _buildStatusGroup(context, entry.key, entry.value),
          ),
        ],
      ),
    );
  }

  /// 构建类型分布
  Widget _buildTypeDistribution(BuildContext context, Map<ConditionType, int> typeStats) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '条件类型分布',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildTypeItem(
                    context,
                    '价格条件',
                    '${typeStats[ConditionType.price] ?? 0}个',
                    Icons.attach_money,
                    Colors.green,
                  ),
                ),
                Expanded(
                  child: _buildTypeItem(
                    context,
                    '成交量条件',
                    '${typeStats[ConditionType.volume] ?? 0}个',
                    Icons.bar_chart,
                    Colors.blue,
                  ),
                ),
                Expanded(
                  child: _buildTypeItem(
                    context,
                    '技术指标',
                    '${typeStats[ConditionType.technical] ?? 0}个',
                    Icons.trending_up,
                    Colors.orange,
                  ),
                ),
                Expanded(
                  child: _buildTypeItem(
                    context,
                    '时间条件',
                    '${typeStats[ConditionType.time] ?? 0}个',
                    Icons.schedule,
                    Colors.purple,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// 构建类型项
  Widget _buildTypeItem(
    BuildContext context,
    String label,
    String count,
    IconData icon,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(
          count,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  /// 构建状态分组
  Widget _buildStatusGroup(
    BuildContext context,
    ConditionStatus status,
    List<ConditionMonitorData> conditions,
  ) {
    final theme = Theme.of(context);
    Color statusColor;
    IconData statusIcon;
    String statusTitle;

    switch (status) {
      case ConditionStatus.idle:
        statusColor = Colors.blue;
        statusIcon = Icons.pause_circle;
        statusTitle = '空闲状态';
        break;
      case ConditionStatus.evaluating:
        statusColor = Colors.orange;
        statusIcon = Icons.hourglass_empty;
        statusTitle = '评估中';
        break;
      case ConditionStatus.triggered:
        statusColor = Colors.green;
        statusIcon = Icons.play_circle;
        statusTitle = '已触发';
        break;
      case ConditionStatus.error:
        statusColor = Colors.red;
        statusIcon = Icons.error;
        statusTitle = '错误状态';
        break;
      case ConditionStatus.disabled:
        statusColor = Colors.grey;
        statusIcon = Icons.stop_circle;
        statusTitle = '已禁用';
        break;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.1),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
            ),
            child: Row(
              children: [
                Icon(statusIcon, color: statusColor),
                const SizedBox(width: 8),
                Text(
                  '$statusTitle (${conditions.length})',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: statusColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          ...conditions.asMap().entries.map(
            (entry) => _buildConditionItem(context, entry.value, entry.key == conditions.length - 1),
          ),
        ],
      ),
    );
  }

  /// 构建条件项
  Widget _buildConditionItem(BuildContext context, ConditionMonitorData condition, bool isLast) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: isLast ? BorderSide.none : BorderSide(
            color: theme.colorScheme.outline.withOpacity(0.2),
            width: 1,
          ),
        ),
      ),
      child: ListTile(
        leading: _buildConditionIcon(condition),
        title: Text(
          condition.conditionName,
          style: theme.textTheme.titleMedium,
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${condition.symbol} • ${condition.type.displayName}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
            const SizedBox(height: 4),
            _buildConditionStats(context, condition),
          ],
        ),
        trailing: _buildConditionActions(context, condition),
        onTap: () => _showConditionDetails(context, condition),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
    );
  }

  /// 构建条件图标
  Widget _buildConditionIcon(ConditionMonitorData condition) {
    Color iconColor;
    switch (condition.status) {
      case ConditionStatus.evaluating:
        iconColor = Colors.orange;
        break;
      case ConditionStatus.triggered:
        iconColor = Colors.green;
        break;
      case ConditionStatus.error:
        iconColor = Colors.red;
        break;
      default:
        iconColor = Colors.blue;
    }

    return Stack(
      children: [
        Icon(
          _getTypeIcon(condition.type),
          color: iconColor,
          size: 32,
        ),
        if (condition.status == ConditionStatus.evaluating)
          Positioned(
            right: -2,
            top: -2,
            child: SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.orange),
              ),
            ),
          ),
      ],
    );
  }

  /// 获取类型图标
  IconData _getTypeIcon(ConditionType type) {
    switch (type) {
      case ConditionType.price:
        return Icons.attach_money;
      case ConditionType.volume:
        return Icons.bar_chart;
      case ConditionType.technical:
        return Icons.trending_up;
      case ConditionType.time:
        return Icons.schedule;
      case ConditionType.market:
        return Icons.public;
    }
  }

  /// 构建条件统计
  Widget _buildConditionStats(BuildContext context, ConditionMonitorData condition) {
    return Row(
      children: [
        Icon(
          Icons.flash_on,
          size: 14,
          color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
        ),
        const SizedBox(width: 4),
        Text(
          '${condition.triggerCount}次触发',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
        const SizedBox(width: 12),
        Icon(
          Icons.trending_up,
          size: 14,
          color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
        ),
        const SizedBox(width: 4),
        Text(
          '${(condition.successRate * 100).toStringAsFixed(1)}%成功率',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
        if (condition.lastTriggered != null) ...[
          const SizedBox(width: 12),
          Icon(
            Icons.access_time,
            size: 14,
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
          ),
          const SizedBox(width: 4),
          Text(
            _formatRelativeTime(condition.lastTriggered!),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
        ],
      ],
    );
  }

  /// 构建条件操作
  Widget _buildConditionActions(BuildContext context, ConditionMonitorData condition) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          onPressed: () => _showConditionDetails(context, condition),
          icon: const Icon(Icons.info, color: Colors.grey),
          tooltip: '详细信息',
        ),
        Switch(
          value: condition.isActive,
          onChanged: (value) {
            // TODO: 切换条件状态
          },
        ),
      ],
    );
  }

  /// 显示条件详情
  void _showConditionDetails(BuildContext context, ConditionMonitorData condition) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildConditionDetailsSheet(context, condition),
    );
  }

  /// 构建条件详情底部表单
  Widget _buildConditionDetailsSheet(BuildContext context, ConditionMonitorData condition) {
    return DraggableScrollableSheet(
      initialChildSize: 0.6,
      minChildSize: 0.3,
      maxChildSize: 0.8,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // 拖拽指示器
              Container(
                margin: const EdgeInsets.symmetric(vertical: 8),
                height: 4,
                width: 40,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              
              // 内容
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(16),
                  children: [
                    // 标题
                    Row(
                      children: [
                        Icon(_getTypeIcon(condition.type), size: 32),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                condition.conditionName,
                                style: Theme.of(context).textTheme.headlineSmall,
                              ),
                              Text(
                                '${condition.symbol} • ${condition.type.displayName}',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                ),
                              ),
                            ],
                          ),
                        ),
                        _buildStatusChip(condition),
                      ],
                    ),
                    const SizedBox(height: 24),
                    
                    // 详细统计
                    _buildDetailSection(
                      context,
                      '执行统计',
                      [
                        _buildDetailItem('触发次数', '${condition.triggerCount}次'),
                        _buildDetailItem('成功率', '${(condition.successRate * 100).toStringAsFixed(1)}%'),
                        _buildDetailItem('平均执行时间', '${condition.averageExecutionTime.inMilliseconds}ms'),
                        _buildDetailItem('最后触发', condition.lastTriggered != null ? _formatDateTime(condition.lastTriggered!) : '未触发'),
                        _buildDetailItem('下次评估', condition.nextEvaluation != null ? _formatDateTime(condition.nextEvaluation!) : '未知'),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // 当前值
                    _buildDetailSection(
                      context,
                      '当前值',
                      condition.currentValue.entries.map(
                        (entry) => _buildDetailItem(entry.key, entry.value.toString()),
                      ).toList(),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  /// 构建状态标签
  Widget _buildStatusChip(ConditionMonitorData condition) {
    Color color;
    switch (condition.status) {
      case ConditionStatus.idle:
        color = Colors.blue;
        break;
      case ConditionStatus.evaluating:
        color = Colors.orange;
        break;
      case ConditionStatus.triggered:
        color = Colors.green;
        break;
      case ConditionStatus.error:
        color = Colors.red;
        break;
      case ConditionStatus.disabled:
        color = Colors.grey;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        condition.status.displayName,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  /// 构建详情区块
  Widget _buildDetailSection(BuildContext context, String title, List<Widget> children) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ...children,
          ],
        ),
      ),
    );
  }

  /// 构建详情项
  Widget _buildDetailItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.grey[600],
              fontSize: 14,
            ),
          ),
          Flexible(
            child: Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.w500,
                fontSize: 14,
              ),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }

  /// 格式化相对时间
  String _formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inMinutes < 1) {
      return '刚刚';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}分钟前';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}小时前';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}天前';
    } else {
      return _formatDateTime(dateTime);
    }
  }

  /// 格式化日期时间
  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}

/// 性能分析Tab
class _PerformanceAnalysisTab extends ConsumerWidget {
  const _PerformanceAnalysisTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final monitorState = ref.watch(conditionMonitorProvider);
    final statistics = ref.watch(conditionStatisticsProvider);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // 整体性能指标
        _buildOverallPerformanceCard(context, statistics),
        const SizedBox(height: 16),
        // 条件性能对比
        _buildPerformanceComparison(context, monitorState.conditions),
        const SizedBox(height: 16),
        // 执行时间分析
        _buildExecutionTimeAnalysis(context, monitorState.conditions),
      ],
    );
  }

  /// 构建整体性能卡片
  Widget _buildOverallPerformanceCard(BuildContext context, Map<String, dynamic> stats) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '整体性能指标',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildPerformanceMetric(
                    context,
                    '平均成功率',
                    '${(stats['overall_success_rate'] * 100).toStringAsFixed(1)}%',
                    Icons.trending_up,
                    Colors.green,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildPerformanceMetric(
                    context,
                    '总触发次数',
                    '${stats['total_triggers']}',
                    Icons.flash_on,
                    Colors.blue,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildPerformanceMetric(
                    context,
                    '活跃条件',
                    '${stats['active_conditions']}/${stats['total_conditions']}',
                    Icons.play_circle,
                    Colors.orange,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              '最后更新: ${_formatDateTime(DateTime.parse(stats['last_update']))}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建性能指标
  Widget _buildPerformanceMetric(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  /// 构建性能对比
  Widget _buildPerformanceComparison(BuildContext context, List<ConditionMonitorData> conditions) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '条件性能对比',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            ...conditions.map((condition) => _buildConditionPerformanceItem(context, condition)),
          ],
        ),
      ),
    );
  }

  /// 构建条件性能项
  Widget _buildConditionPerformanceItem(BuildContext context, ConditionMonitorData condition) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  condition.conditionName,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  condition.symbol,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          SizedBox(
            width: 100,
            child: LinearProgressIndicator(
              value: condition.successRate,
              backgroundColor: Theme.of(context).colorScheme.surfaceVariant,
              valueColor: AlwaysStoppedAnimation<Color>(
                condition.successRate > 0.8 ? Colors.green : 
                condition.successRate > 0.6 ? Colors.orange : Colors.red,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '${(condition.successRate * 100).toStringAsFixed(0)}%',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建执行时间分析
  Widget _buildExecutionTimeAnalysis(BuildContext context, List<ConditionMonitorData> conditions) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '执行时间分析',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            ...conditions.map((condition) => _buildExecutionTimeItem(context, condition)),
          ],
        ),
      ),
    );
  }

  /// 构建执行时间项
  Widget _buildExecutionTimeItem(BuildContext context, ConditionMonitorData condition) {
    final avgTime = condition.averageExecutionTime.inMilliseconds;
    
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              condition.conditionName,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          const SizedBox(width: 16),
          Text(
            '${avgTime}ms',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
              color: avgTime < 200 ? Colors.green : avgTime < 500 ? Colors.orange : Colors.red,
            ),
          ),
        ],
      ),
    );
  }

  /// 格式化日期时间
  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}

/// 执行历史Tab
class _ExecutionHistoryTab extends ConsumerWidget {
  const _ExecutionHistoryTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recentTriggered = ref.watch(recentTriggeredConditionsProvider);

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: recentTriggered.length,
      itemBuilder: (context, index) {
        final condition = recentTriggered[index];
        return _buildHistoryItem(context, condition);
      },
    );
  }

  /// 构建历史项
  Widget _buildHistoryItem(BuildContext context, ConditionMonitorData condition) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.green.withOpacity(0.1),
          child: Icon(Icons.check_circle, color: Colors.green),
        ),
        title: Text(condition.conditionName),
        subtitle: Text(
          '${condition.symbol} • 触发时间: ${_formatDateTime(condition.lastTriggered!)}',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
        trailing: Text(
          '${(condition.successRate * 100).toStringAsFixed(0)}%',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Colors.green,
            fontWeight: FontWeight.w500,
          ),
        ),
        onTap: () => _showHistoryDetails(context, condition),
      ),
    );
  }

  /// 显示历史详情
  void _showHistoryDetails(BuildContext context, ConditionMonitorData condition) {
    // TODO: 实现历史详情显示
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${condition.conditionName}的历史详情')),
    );
  }

  /// 格式化日期时间
  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
