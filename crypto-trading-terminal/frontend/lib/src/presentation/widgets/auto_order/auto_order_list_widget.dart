import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../domain/entities/auto_order.dart';
import '../../providers/auto_order/auto_order_provider.dart';
import 'auto_order_detail_dialog.dart';

/// 自动订单列表组件
class AutoOrderListWidget extends ConsumerWidget {
  const AutoOrderListWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final autoOrderState = ref.watch(autoOrderProvider);

    if (autoOrderState.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (autoOrderState.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            const SizedBox(height: 16),
            Text(
              '加载失败',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              autoOrderState.error!,
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                ref.read(autoOrderProvider.notifier).loadAutoOrders();
              },
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    if (autoOrderState.autoOrders.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.list_alt,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              '暂无自动订单',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '点击"新增订单"创建您的第一个自动订单',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey.shade500,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 列表头部
        Row(
          children: [
            Text(
              '订单列表',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(width: 16),
            Chip(
              label: Text(
                '${autoOrderState.autoOrders.length} 个订单',
                style: const TextStyle(fontSize: 12),
              ),
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            ),
            const Spacer(),
            // 过滤器
            PopupMenuButton<String>(
              icon: Icon(
                Icons.filter_list,
                color: Theme.of(context).colorScheme.onSurface,
              ),
              onSelected: (filter) {
                ref.read(autoOrderProvider.notifier).setFilter(filter);
              },
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'all',
                  child: Text('全部订单'),
                ),
                const PopupMenuItem(
                  value: 'active',
                  child: Text('活跃订单'),
                ),
                const PopupMenuItem(
                  value: 'paused',
                  child: Text('已暂停'),
                ),
                const PopupMenuItem(
                  value: 'completed',
                  child: Text('已完成'),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: 16),
        
        // 订单列表
        Expanded(
          child: ListView.builder(
            itemCount: autoOrderState.autoOrders.length,
            itemBuilder: (context, index) {
              final order = autoOrderState.autoOrders[index];
              return _buildOrderCard(
                context,
                ref,
                order,
                autoOrderState.filter,
              );
            },
          ),
        ),
      ],
    );
  }

  /// 构建订单卡片
  Widget _buildOrderCard(
    BuildContext context,
    WidgetRef ref,
    AutoOrder order,
    String filter,
  ) {
    final theme = Theme.of(context);
    
    // 根据状态确定颜色
    Color statusColor;
    IconData statusIcon;
    switch (order.status) {
      case OrderStatus.FILLED:
        statusColor = Colors.green;
        statusIcon = Icons.check_circle;
        break;
      case OrderStatus.PARTIALLY_FILLED:
        statusColor = Colors.orange;
        statusIcon = Icons.hourglass_empty;
        break;
      case OrderStatus.CANCELLED:
        statusColor = Colors.grey;
        statusIcon = Icons.cancel;
        break;
      case OrderStatus.REJECTED:
        statusColor = Colors.red;
        statusIcon = Icons.error;
        break;
      default:
        statusColor = Colors.blue;
        statusIcon = Icons.pending;
        break;
    }

    // 盈亏状态
    bool isProfit = false;
    if (order.lastExecutionResult != null) {
      final result = order.lastExecutionResult!;
      if (result.containsKey('pnl')) {
        isProfit = result['pnl'] > 0;
      }
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _showOrderDetailDialog(context, order),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 头部信息
              Row(
                children: [
                  // 状态指示器
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: statusColor,
                        width: 1,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          statusIcon,
                          size: 14,
                          color: statusColor,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _getStatusText(order.status),
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: statusColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  
                  // 订单状态
                  Icon(
                    order.isActive ? Icons.play_circle : Icons.pause_circle,
                    size: 16,
                    color: order.isActive ? Colors.green : Colors.orange,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    order.isActive ? '活跃' : (order.isPaused ? '已暂停' : '已停止'),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: order.isActive ? Colors.green : Colors.orange,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  
                  const Spacer(),
                  
                  // 菜单按钮
                  PopupMenuButton<String>(
                    onSelected: (action) => _handleOrderAction(
                      context,
                      ref,
                      action,
                      order,
                    ),
                    itemBuilder: (context) => [
                      const PopupMenuItem(
                        value: 'toggle',
                        child: Row(
                          children: [
                            Icon(Icons.play_arrow),
                            SizedBox(width: 8),
                            Text('启用/禁用'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'edit',
                        child: Row(
                          children: [
                            Icon(Icons.edit),
                            SizedBox(width: 8),
                            Text('编辑'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, color: Colors.red),
                            SizedBox(width: 8),
                            Text('删除', style: TextStyle(color: Colors.red)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // 订单信息
              Row(
                children: [
                  // 交易对和方向
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surface,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: theme.colorScheme.outline,
                        width: 1,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          order.symbol,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: order.orderSide == OrderSide.BUY
                                    ? Colors.green
                                    : Colors.red,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              order.orderSide == OrderSide.BUY ? '买入' : '卖出',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: order.orderSide == OrderSide.BUY
                                    ? Colors.green
                                    : Colors.red,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'x${order.quantity.toStringAsFixed(4)}',
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  
                  const SizedBox(width: 16),
                  
                  // 风险控制
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Text('止损: ', style: TextStyle(fontSize: 12)),
                            Text(
                              order.stopLossPrice?.toStringAsFixed(2) ?? '未设置',
                              style: TextStyle(
                                fontSize: 12,
                                color: order.stopLossPrice != null
                                    ? Colors.red
                                    : Colors.grey,
                                fontWeight: order.stopLossPrice != null
                                    ? FontWeight.w600
                                    : FontWeight.normal,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Text('止盈: ', style: TextStyle(fontSize: 12)),
                            Text(
                              order.takeProfitPrice?.toStringAsFixed(2) ?? '未设置',
                              style: TextStyle(
                                fontSize: 12,
                                color: order.takeProfitPrice != null
                                    ? Colors.green
                                    : Colors.grey,
                                fontWeight: order.takeProfitPrice != null
                                    ? FontWeight.w600
                                    : FontWeight.normal,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 12),
              
              // 统计数据
              Row(
                children: [
                  // 触发次数
                  Expanded(
                    child: _buildStatItem(
                      theme,
                      Icons.lightbulb_outline,
                      '触发次数',
                      '${order.triggerCount}',
                    ),
                  ),
                  
                  // 执行次数
                  Expanded(
                    child: _buildStatItem(
                      theme,
                      Icons.play_circle_outline,
                      '执行次数',
                      '${order.executionCount}',
                    ),
                  ),
                  
                  // 最后执行
                  Expanded(
                    child: _buildStatItem(
                      theme,
                      Icons.access_time,
                      '最后执行',
                      order.lastTriggered != null
                          ? DateFormat('MM/dd HH:mm').format(order.lastTriggered!)
                          : '未执行',
                    ),
                  ),
                ],
              ),
              
              // 执行结果摘要
              if (order.lastExecutionResult != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: (isProfit ? Colors.green : Colors.red).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isProfit ? Icons.trending_up : Icons.trending_down,
                        size: 16,
                        color: isProfit ? Colors.green : Colors.red,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '上次执行: ${isProfit ? '盈利' : '亏损'}',
                        style: TextStyle(
                          fontSize: 12,
                          color: isProfit ? Colors.green : Colors.red,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  /// 构建统计项
  Widget _buildStatItem(
    ThemeData theme,
    IconData icon,
    String label,
    String value,
  ) {
    return Column(
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: theme.colorScheme.primary),
            const SizedBox(width: 4),
            Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  /// 获取状态文本
  String _getStatusText(OrderStatus status) {
    switch (status) {
      case OrderStatus.NEW:
        return '新建';
      case OrderStatus.SUBMITTED:
        return '已提交';
      case OrderStatus.PARTIALLY_FILLED:
        return '部分成交';
      case OrderStatus.FILLED:
        return '已完成';
      case OrderStatus.CANCELLED:
        return '已取消';
      case OrderStatus.REJECTED:
        return '已拒绝';
      case OrderStatus.EXPIRED:
        return '已过期';
      default:
        return '未知';
    }
  }

  /// 显示订单详情对话框
  void _showOrderDetailDialog(BuildContext context, AutoOrder order) {
    showDialog(
      context: context,
      builder: (context) => AutoOrderDetailDialog(order: order),
    );
  }

  /// 处理订单操作
  void _handleOrderAction(
    BuildContext context,
    WidgetRef ref,
    String action,
    AutoOrder order,
  ) async {
    final notifier = ref.read(autoOrderProvider.notifier);
    
    switch (action) {
      case 'toggle':
        await notifier.toggleOrderStatus(order.id, !order.isActive);
        break;
      case 'edit':
        // TODO: 实现编辑订单功能
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('编辑功能即将推出')),
        );
        break;
      case 'delete':
        _showDeleteConfirmationDialog(context, ref, order);
        break;
    }
  }

  /// 显示删除确认对话框
  void _showDeleteConfirmationDialog(
    BuildContext context,
    WidgetRef ref,
    AutoOrder order,
  ) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除'),
        content: Text('确定要删除自动订单 "${order.strategyName}" 吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(context).pop();
              await ref.read(autoOrderProvider.notifier).deleteAutoOrder(order.id);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }
}