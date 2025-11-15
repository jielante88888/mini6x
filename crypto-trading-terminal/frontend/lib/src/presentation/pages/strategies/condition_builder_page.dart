import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_slidable/flutter_slidable.dart';
import 'package:intl/intl.dart';

import '../../providers/conditions_provider.dart';
import '../../widgets/common/app_bar_widget.dart';
import '../../widgets/common/loading_widget.dart';
import '../../widgets/common/error_widget.dart' as custom_error;
import '../../widgets/common/floating_action_button_widget.dart';
import 'condition_form_widget.dart';
import 'condition_card_widget.dart';

/// 条件构建器页面
/// 提供条件的创建、编辑、查看和管理功能
class ConditionBuilderPage extends ConsumerStatefulWidget {
  const ConditionBuilderPage({super.key});

  @override
  ConsumerState<ConditionBuilderPage> createState() => _ConditionBuilderPageState();
}

class _ConditionBuilderPageState extends ConsumerState<ConditionBuilderPage>
    with TickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    
    // 监听搜索框变化
    _searchController.addListener(() {
      ref.read(conditionsFilterProvider.notifier).state = _searchController.text;
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
    final conditionsState = ref.watch(conditionsProvider);
    final filteredConditions = ref.watch(filteredConditionsProvider);
    final statistics = ref.read(conditionsProvider.notifier).getConditionStatistics();

    return Scaffold(
      appBar: AppBarWidget(
        title: '条件管理',
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.list), text: '全部'),
            Tab(icon: Icon(Icons.play_arrow), text: '启用'),
            Tab(icon: Icon(Icons.pause), text: '禁用'),
          ],
        ),
      ),
      body: Column(
        children: [
          // 搜索栏和统计信息
          _buildSearchAndStatsBar(context, statistics),
          
          // 条件列表
          Expanded(
            child: conditionsState.isLoading
                ? const LoadingWidget()
                : conditionsState.error != null
                    ? custom_error.ErrorWidget(
                        message: conditionsState.error!,
                        onRetry: () {
                          ref.read(conditionsProvider.notifier).clearError();
                          ref.refresh(conditionsProvider);
                        },
                      )
                    : _buildConditionsList(context, filteredConditions),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButtonWidget(
        onPressed: () => _showConditionForm(context),
        icon: Icons.add,
        tooltip: '添加条件',
      ),
      bottomNavigationBar: _buildBottomNavigationBar(context),
    );
  }

  /// 构建搜索栏和统计信息栏
  Widget _buildSearchAndStatsBar(BuildContext context, Map<String, int> statistics) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          // 搜索框
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: '搜索条件名称或交易对...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                        ref.read(conditionsFilterProvider.notifier).state = '';
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 12,
              ),
            ),
          ),
          const SizedBox(height: 12),
          
          // 统计信息
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildStatItem(
                context,
                '总计',
                '${statistics['total'] ?? 0}',
                Icons.all_inclusive,
                Colors.blue,
              ),
              _buildStatItem(
                context,
                '启用',
                '${statistics['enabled'] ?? 0}',
                Icons.play_arrow,
                Colors.green,
              ),
              _buildStatItem(
                context,
                '禁用',
                '${statistics['disabled'] ?? 0}',
                Icons.pause,
                Colors.orange,
              ),
              _buildStatItem(
                context,
                '已触发',
                '${statistics['triggered'] ?? 0}',
                Icons.notifications_active,
                Colors.red,
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建统计项
  Widget _buildStatItem(
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
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: color,
                fontWeight: FontWeight.bold,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  /// 构建条件列表
  Widget _buildConditionsList(BuildContext context, List<Condition> conditions) {
    if (conditions.isEmpty) {
      return _buildEmptyState(context);
    }

    return TabBarView(
      controller: _tabController,
      children: [
        _buildConditionsByTab(context, conditions, null),
        _buildConditionsByTab(context, conditions, true),
        _buildConditionsByTab(context, conditions, false),
      ],
    );
  }

  /// 按标签页构建条件列表
  Widget _buildConditionsByTab(BuildContext context, List<Condition> conditions, bool? enabled) {
    final filteredConditions = enabled == null
        ? conditions
        : conditions.where((c) => c.enabled == enabled).toList();

    if (filteredConditions.isEmpty) {
      return _buildEmptyTabState(context, enabled);
    }

    return RefreshIndicator(
      onRefresh: () async => ref.refresh(conditionsProvider),
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.all(16),
        itemCount: filteredConditions.length,
        itemBuilder: (context, index) {
          final condition = filteredConditions[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Slidable(
              key: Key(condition.id),
              endActionPane: ActionPane(
                motion: const ScrollMotion(),
                children: [
                  SlidableAction(
                    onPressed: (_) => _editCondition(context, condition),
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                    icon: Icons.edit,
                    label: '编辑',
                  ),
                  SlidableAction(
                    onPressed: (_) => _deleteCondition(context, condition.id),
                    backgroundColor: Colors.red,
                    foregroundColor: Colors.white,
                    icon: Icons.delete,
                    label: '删除',
                  ),
                ],
              ),
              child: ConditionCardWidget(
                condition: condition,
                onTap: () => _showConditionDetails(context, condition),
                onToggle: () => _toggleCondition(context, condition.id),
              ),
            ),
          );
        },
      ),
    );
  }

  /// 构建空状态
  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.rule,
            size: 64,
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            '暂无条件',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
          ),
          const SizedBox(height: 8),
          Text(
            '点击右下角按钮创建第一个条件',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                ),
          ),
        ],
      ),
    );
  }

  /// 构建空标签页状态
  Widget _buildEmptyTabState(BuildContext context, bool? enabled) {
    String message;
    if (enabled == true) {
      message = '暂无启用的条件';
    } else if (enabled == false) {
      message = '暂无禁用的条件';
    } else {
      message = '暂无符合条件的记录';
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            enabled == null ? Icons.search_off : Icons.inbox,
            size: 48,
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
          ),
          const SizedBox(height: 12),
          Text(
            message,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
          ),
        ],
      ),
    );
  }

  /// 构建底部导航栏
  Widget _buildBottomNavigationBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _buildBottomNavItem(
            context,
            '导入',
            Icons.file_upload,
            () => _importConditions(context),
          ),
          _buildBottomNavItem(
            context,
            '导出',
            Icons.file_download,
            () => _exportConditions(context),
          ),
          _buildBottomNavItem(
            context,
            '模板',
            Icons.template,
            () => _showTemplates(context),
          ),
          _buildBottomNavItem(
            context,
            '设置',
            Icons.settings,
            () => _showSettings(context),
          ),
        ],
      ),
    );
  }

  /// 构建底部导航项
  Widget _buildBottomNavItem(
    BuildContext context,
    String label,
    IconData icon,
    VoidCallback onTap,
  ) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 24,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.primary,
                  ),
            ),
          ],
        ),
      ),
    );
  }

  /// 显示条件表单
  void _showConditionForm(BuildContext context, {Condition? condition}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => ConditionFormWidget(
        condition: condition,
        onSaved: (savedCondition) {
          if (condition == null) {
            ref.read(conditionsProvider.notifier).addCondition(savedCondition);
          } else {
            ref.read(conditionsProvider.notifier).updateCondition(savedCondition);
          }
          Navigator.of(context).pop();
        },
      ),
    );
  }

  /// 编辑条件
  void _editCondition(BuildContext context, Condition condition) {
    _showConditionForm(context, condition: condition);
  }

  /// 删除条件
  void _deleteCondition(BuildContext context, String conditionId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除条件'),
        content: const Text('确定要删除这个条件吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              ref.read(conditionsProvider.notifier).deleteCondition(conditionId);
              Navigator.of(context).pop();
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  /// 切换条件启用状态
  void _toggleCondition(BuildContext context, String conditionId) {
    ref.read(conditionsProvider.notifier).toggleCondition(conditionId);
  }

  /// 显示条件详情
  void _showConditionDetails(BuildContext context, Condition condition) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildConditionDetailsSheet(context, condition),
    );
  }

  /// 构建条件详情底部表单
  Widget _buildConditionDetailsSheet(BuildContext context, Condition condition) {
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
                        Icon(
                          _getConditionIcon(condition.type),
                          size: 32,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                condition.name,
                                style: Theme.of(context).textTheme.headlineSmall,
                              ),
                              if (condition.description != null)
                                Text(
                                  condition.description!,
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                  ),
                                ),
                            ],
                          ),
                        ),
                        _buildStatusChip(context, condition.status),
                      ],
                    ),
                    const SizedBox(height: 24),
                    
                    // 条件信息
                    _buildDetailSection(
                      context,
                      '条件信息',
                      [
                        _buildDetailItem('类型', condition.type.displayName),
                        _buildDetailItem('操作符', condition.operator.displayName),
                        _buildDetailItem('阈值', condition.formattedValue),
                        _buildDetailItem('交易对', condition.symbol),
                        _buildDetailItem('优先级', '${condition.priorityDisplay} ${condition.priorityEmoji}'),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // 执行统计
                    _buildDetailSection(
                      context,
                      '执行统计',
                      [
                        _buildDetailItem('创建时间', DateFormat('yyyy-MM-dd HH:mm').format(condition.createdAt)),
                        _buildDetailItem('更新时间', DateFormat('yyyy-MM-dd HH:mm').format(condition.updatedAt)),
                        _buildDetailItem('触发次数', '${condition.triggerCount}'),
                        if (condition.lastTriggered != null)
                          _buildDetailItem('最后触发', DateFormat('yyyy-MM-dd HH:mm').format(condition.lastTriggered!)),
                      ],
                    ),
                  ],
                ),
              ),
              
              // 底部按钮
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          _editCondition(context, condition);
                          Navigator.of(context).pop();
                        },
                        child: const Text('编辑'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () => _toggleCondition(context, condition.id),
                        child: Text(condition.enabled ? '禁用' : '启用'),
                      ),
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
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.w500,
              fontSize: 14,
            ),
          ),
        ],
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

  /// 构建状态标签
  Widget _buildStatusChip(BuildContext context, ConditionStatus status) {
    Color color;
    IconData icon;
    
    switch (status) {
      case ConditionStatus.enabled:
        color = Colors.green;
        icon = Icons.play_arrow;
        break;
      case ConditionStatus.disabled:
        color = Colors.orange;
        icon = Icons.pause;
        break;
      case ConditionStatus.triggered:
        color = Colors.blue;
        icon = Icons.notifications_active;
        break;
    }

    return Chip(
      avatar: Icon(icon, size: 16, color: Colors.white),
      label: Text(
        status.displayName,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
        ),
      ),
      backgroundColor: color,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  /// 获取条件类型图标
  IconData _getConditionIcon(ConditionType type) {
    switch (type) {
      case ConditionType.price:
        return Icons.attach_money;
      case ConditionType.volume:
        return Icons.bar_chart;
      case ConditionType.time:
        return Icons.schedule;
      case ConditionType.technical:
        return Icons.trending_up;
      case ConditionType.market:
        return Icons.public;
    }
  }

  /// 导入条件
  void _importConditions(BuildContext context) {
    // TODO: 实现导入功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('导入功能待实现')),
    );
  }

  /// 导出条件
  void _exportConditions(BuildContext context) {
    // TODO: 实现导出功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('导出功能待实现')),
    );
  }

  /// 显示模板
  void _showTemplates(BuildContext context) {
    // TODO: 实现模板功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('模板功能待实现')),
    );
  }

  /// 显示设置
  void _showSettings(BuildContext context) {
    // TODO: 实现设置功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('设置功能待实现')),
    );
  }
}
