import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../providers/conditions_provider.dart';

/// 条件卡片Widget
/// 用于在列表中显示单个条件的详细信息的卡片组件
class ConditionCardWidget extends StatelessWidget {
  final Condition condition;
  final VoidCallback? onTap;
  final VoidCallback? onToggle;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  const ConditionCardWidget({
    super.key,
    required this.condition,
    this.onTap,
    this.onToggle,
    this.onEdit,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: _getBorderColor(context, condition),
          width: condition.enabled ? 2 : 1,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 顶部信息行
              _buildTopRow(context),
              const SizedBox(height: 12),
              
              // 条件详情
              _buildConditionDetails(context),
              const SizedBox(height: 12),
              
              // 底部信息
              _buildBottomRow(context),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建顶部信息行
  Widget _buildTopRow(BuildContext context) {
    return Row(
      children: [
        // 条件图标和状态
        _buildConditionIcon(context),
        const SizedBox(width: 12),
        
        // 条件名称和描述
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      condition.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: condition.enabled 
                                ? Theme.of(context).colorScheme.onSurface
                                : Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                          ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  _buildStatusBadge(context),
                ],
              ),
              if (condition.description != null) ...[
                const SizedBox(height: 2),
                Text(
                  condition.description!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                      ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
        
        // 操作按钮
        _buildActionButtons(context),
      ],
    );
  }

  /// 构建条件图标
  Widget _buildConditionIcon(BuildContext context) {
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        color: _getIconBackgroundColor(context, condition),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(
        _getConditionIcon(condition.type),
        color: _getIconColor(context, condition),
        size: 24,
      ),
    );
  }

  /// 构建状态标签
  Widget _buildStatusBadge(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _getStatusBadgeColor(context, condition),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            condition.enabled ? Icons.play_arrow : Icons.pause,
            size: 14,
            color: Colors.white,
          ),
          const SizedBox(width: 4),
          Text(
            condition.enabled ? '启用' : '禁用',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建操作按钮
  Widget _buildActionButtons(BuildContext context) {
    return Column(
      children: [
        // 切换按钮
        IconButton(
          onPressed: onToggle,
          icon: Icon(
            condition.enabled ? Icons.pause : Icons.play_arrow,
            color: condition.enabled 
                ? Colors.orange 
                : Colors.green,
          ),
          tooltip: condition.enabled ? '禁用' : '启用',
        ),
        
        // 菜单按钮
        PopupMenuButton<String>(
          onSelected: (value) {
            switch (value) {
              case 'edit':
                onEdit?.call();
                break;
              case 'delete':
                onDelete?.call();
                break;
              case 'duplicate':
                _duplicateCondition(context);
                break;
              case 'test':
                _testCondition(context);
                break;
            }
          },
          itemBuilder: (context) => [
            const PopupMenuItem(
              value: 'edit',
              child: ListTile(
                leading: Icon(Icons.edit),
                title: Text('编辑'),
                contentPadding: EdgeInsets.zero,
                visualDensity: VisualDensity.compact,
              ),
            ),
            const PopupMenuItem(
              value: 'duplicate',
              child: ListTile(
                leading: Icon(Icons.content_copy),
                title: Text('复制'),
                contentPadding: EdgeInsets.zero,
                visualDensity: VisualDensity.compact,
              ),
            ),
            const PopupMenuItem(
              value: 'test',
              child: ListTile(
                leading: Icon(Icons.play_arrow),
                title: Text('测试'),
                contentPadding: EdgeInsets.zero,
                visualDensity: VisualDensity.compact,
              ),
            ),
            const PopupMenuItem(
              value: 'delete',
              child: ListTile(
                leading: Icon(Icons.delete, color: Colors.red),
                title: Text('删除', style: TextStyle(color: Colors.red)),
                contentPadding: EdgeInsets.zero,
                visualDensity: VisualDensity.compact,
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// 构建条件详情
  Widget _buildConditionDetails(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          // 交易对
          Expanded(
            child: _buildDetailItem(
              context,
              Icons.currency_bitcoin,
              '交易对',
              condition.symbol,
              isHighlighted: true,
            ),
          ),
          
          const SizedBox(width: 16),
          
          // 条件表达式
          Expanded(
            child: _buildDetailItem(
              context,
              Icons.compare_arrows,
              '条件',
              _buildConditionExpression(),
            ),
          ),
          
          const SizedBox(width: 16),
          
          // 优先级
          Expanded(
            child: _buildDetailItem(
              context,
              Icons.priority_high,
              '优先级',
              '${condition.priorityEmoji} ${condition.priorityDisplay}',
            ),
          ),
        ],
      ),
    );
  }

  /// 构建详情项
  Widget _buildDetailItem(
    BuildContext context,
    IconData icon,
    String label,
    String value, {
    bool isHighlighted = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 16,
              color: isHighlighted 
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
            ),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                value,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: isHighlighted ? FontWeight.w600 : FontWeight.normal,
                      color: isHighlighted
                          ? Theme.of(context).colorScheme.primary
                          : Theme.of(context).colorScheme.onSurface,
                    ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
        ),
      ],
    );
  }

  /// 构建条件表达式
  String _buildConditionExpression() {
    switch (condition.type) {
      case ConditionType.price:
      case ConditionType.volume:
        return '${condition.operator.displayName} ${condition.formattedValue}';
      default:
        return '${condition.operator.displayName} ${condition.value}';
    }
  }

  /// 构建底部信息行
  Widget _buildBottomRow(BuildContext context) {
    return Row(
      children: [
        // 创建时间
        Expanded(
          child: Row(
            children: [
              Icon(
                Icons.schedule,
                size: 16,
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
              const SizedBox(width: 4),
              Text(
                '创建于 ${DateFormat('MM-dd HH:mm').format(condition.createdAt)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    ),
              ),
            ],
          ),
        ),
        
        // 触发统计
        if (condition.triggerCount > 0) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.notifications_active,
                  size: 14,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
                const SizedBox(width: 4),
                Text(
                  '${condition.triggerCount}次触发',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.w500,
                      ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  /// 获取边界颜色
  Color _getBorderColor(BuildContext context, Condition condition) {
    if (!condition.enabled) {
      return Theme.of(context).colorScheme.outline.withOpacity(0.3);
    }
    
    switch (condition.status) {
      case ConditionStatus.enabled:
        return Theme.of(context).colorScheme.primary.withOpacity(0.3);
      case ConditionStatus.triggered:
        return Theme.of(context).colorScheme.secondary;
      case ConditionStatus.disabled:
        return Theme.of(context).colorScheme.outline.withOpacity(0.3);
    }
  }

  /// 获取图标背景颜色
  Color _getIconBackgroundColor(BuildContext context, Condition condition) {
    if (!condition.enabled) {
      return Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3);
    }
    
    switch (condition.status) {
      case ConditionStatus.enabled:
        return Theme.of(context).colorScheme.primaryContainer;
      case ConditionStatus.triggered:
        return Theme.of(context).colorScheme.secondaryContainer;
      case ConditionStatus.disabled:
        return Theme.of(context).colorScheme.surfaceVariant;
    }
  }

  /// 获取图标颜色
  Color _getIconColor(BuildContext context, Condition condition) {
    if (!condition.enabled) {
      return Theme.of(context).colorScheme.onSurface.withOpacity(0.4);
    }
    
    switch (condition.status) {
      case ConditionStatus.enabled:
        return Theme.of(context).colorScheme.onPrimaryContainer;
      case ConditionStatus.triggered:
        return Theme.of(context).colorScheme.onSecondaryContainer;
      case ConditionStatus.disabled:
        return Theme.of(context).colorScheme.onSurfaceVariant;
    }
  }

  /// 获取状态标签颜色
  Color _getStatusBadgeColor(BuildContext context, Condition condition) {
    switch (condition.status) {
      case ConditionStatus.enabled:
        return Colors.green;
      case ConditionStatus.triggered:
        return Colors.blue;
      case ConditionStatus.disabled:
        return Colors.orange;
    }
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

  /// 复制条件
  void _duplicateCondition(BuildContext context) {
    // TODO: 实现条件复制功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('复制功能待实现')),
    );
  }

  /// 测试条件
  void _testCondition(BuildContext context) {
    // TODO: 实现条件测试功能
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('测试条件: ${condition.name}'),
        backgroundColor: Colors.blue,
      ),
    );
  }
}
