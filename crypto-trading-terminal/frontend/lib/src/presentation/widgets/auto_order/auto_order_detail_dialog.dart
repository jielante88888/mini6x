import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../domain/entities/auto_order.dart';
import '../../providers/auto_order/auto_order_provider.dart';

/// 自动订单详情对话框
class AutoOrderDetailDialog extends ConsumerStatefulWidget {
  final AutoOrder order;

  const AutoOrderDetailDialog({
    super.key,
    required this.order,
  });

  @override
  ConsumerState<AutoOrderDetailDialog> createState() =>
      _AutoOrderDetailDialogState();
}

class _AutoOrderDetailDialogState
    extends ConsumerState<AutoOrderDetailDialog> {
  int _selectedTabIndex = 0;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final order = widget.order;

    return Dialog(
      insetPadding: const EdgeInsets.all(16),
      child: Container(
        width: double.maxFinite,
        height: MediaQuery.of(context).size.height * 0.8,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题栏
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(28),
                  topRight: Radius.circular(28),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.autorenew,
                    color: theme.colorScheme.onPrimary,
                    size: 24,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          order.strategyName,
                          style: theme.textTheme.headlineSmall?.copyWith(
                            color: theme.colorScheme.onPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
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
                            const SizedBox(width: 8),
                            Text(
                              '${order.symbol} ${order.orderSide == OrderSide.BUY ? '买入' : '卖出'} x${order.quantity.toStringAsFixed(4)}',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                color: theme.colorScheme.onPrimary.withOpacity(0.9),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: Icon(
                      Icons.close,
                      color: theme.colorScheme.onPrimary,
                    ),
                  ),
                ],
              ),
            ),

            // 状态和操作
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: Row(
                children: [
                  // 状态指示器
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: _getStatusColor().withOpacity(0.2),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: _getStatusColor(),
                        width: 1,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _getStatusIcon(),
                          size: 16,
                          color: _getStatusColor(),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _getStatusText(),
                          style: TextStyle(
                            color: _getStatusColor(),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  
                  const SizedBox(width: 12),
                  
                  // 激活状态
                  Icon(
                    order.isActive ? Icons.play_circle : Icons.pause_circle,
                    size: 16,
                    color: order.isActive ? Colors.green : Colors.orange,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    order.isActive ? '活跃' : (order.isPaused ? '已暂停' : '已停止'),
                    style: TextStyle(
                      color: order.isActive ? Colors.green : Colors.orange,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  
                  const Spacer(),
                  
                  // 操作按钮
                  Row(
                    children: [
                      // 启用/禁用按钮
                      ElevatedButton.icon(
                        onPressed: () => _toggleOrderStatus(),
                        icon: Icon(
                          order.isActive ? Icons.pause : Icons.play_arrow,
                          size: 16,
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: order.isActive
                              ? Colors.orange
                              : Colors.green,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                        ),
                        label: Text(
                          order.isActive ? '暂停' : '启用',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ),
                      const SizedBox(width: 8),
                      
                      // 删除按钮
                      ElevatedButton.icon(
                        onPressed: () => _deleteOrder(),
                        icon: const Icon(Icons.delete, size: 16),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.red,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                        ),
                        label: const Text('删除', style: TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // 标签页
            Container(
              child: Row(
                children: [
                  Expanded(
                    child: _buildTabButton(
                      0,
                      Icons.info_outline,
                      '基础信息',
                    ),
                  ),
                  Expanded(
                    child: _buildTabButton(
                      1,
                      Icons.security,
                      '风险控制',
                    ),
                  ),
                  Expanded(
                    child: _buildTabButton(
                      2,
                      Icons.analytics,
                      '执行统计',
                    ),
                  ),
                ],
              ),
            ),

            // 内容区域
            Expanded(
              child: Container(
                width: double.infinity,
                child: _buildTabContent(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建标签页按钮
  Widget _buildTabButton(int index, IconData icon, String label) {
    final isSelected = _selectedTabIndex == index;
    final theme = Theme.of(context);

    return GestureDetector(
      onTap: () {
        setState(() {
          _selectedTabIndex = index;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: isSelected
              ? theme.colorScheme.primaryContainer
              : Colors.transparent,
          border: Border(
            bottom: BorderSide(
              color: isSelected
                  ? theme.colorScheme.primary
                  : Colors.transparent,
              width: 2,
            ),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 18,
              color: isSelected
                  ? theme.colorScheme.primary
                  : theme.colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: isSelected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.onSurfaceVariant,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建标签页内容
  Widget _buildTabContent() {
    switch (_selectedTabIndex) {
      case 0:
        return _buildBasicInfoTab();
      case 1:
        return _buildRiskControlTab();
      case 2:
        return _buildExecutionStatsTab();
      default:
        return Container();
    }
  }

  /// 基础信息标签页
  Widget _buildBasicInfoTab() {
    final order = widget.order;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildInfoSection(
            '订单配置',
            [
              _buildInfoItem('订单ID', order.autoOrderId),
              _buildInfoItem('策略名称', order.strategyName),
              _buildInfoItem('交易对', order.symbol),
              _buildInfoItem('市场类型', order.marketType == MarketType.spot ? '现货' : '合约'),
              _buildInfoItem('订单方向', order.orderSide == OrderSide.BUY ? '买入' : '卖出'),
              _buildInfoItem('数量', order.quantity.toStringAsFixed(4)),
              _buildInfoItem('订单类型', order.orderType.name),
            ],
          ),
          
          const SizedBox(height: 20),
          
          _buildInfoSection(
            '时间信息',
            [
              _buildInfoItem('创建时间', DateFormat('yyyy-MM-dd HH:mm:ss').format(order.createdAt)),
              _buildInfoItem('更新时间', DateFormat('yyyy-MM-dd HH:mm:ss').format(order.updatedAt)),
              if (order.lastTriggered != null)
                _buildInfoItem('最后触发', DateFormat('yyyy-MM-dd HH:mm:ss').format(order.lastTriggered!)),
              if (order.expiresAt != null)
                _buildInfoItem('过期时间', DateFormat('yyyy-MM-dd HH:mm:ss').format(order.expiresAt!)),
            ],
          ),
          
          const SizedBox(height: 20),
          
          _buildInfoSection(
            '状态信息',
            [
              _buildInfoItem('当前状态', _getStatusText()),
              _buildInfoItem('是否活跃', order.isActive ? '是' : '否'),
              _buildInfoItem('是否暂停', order.isPaused ? '是' : '否'),
              _buildInfoItem('触发次数', '${order.triggerCount}'),
              _buildInfoItem('执行次数', '${order.executionCount}'),
            ],
          ),
        ],
      ),
    );
  }

  /// 风险控制标签页
  Widget _buildRiskControlTab() {
    final order = widget.order;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildInfoSection(
            '风险参数',
            [
              _buildInfoItem(
                '止损价格',
                order.stopLossPrice != null
                    ? order.stopLossPrice!.toStringAsFixed(2)
                    : '未设置',
              ),
              _buildInfoItem(
                '止盈价格',
                order.takeProfitPrice != null
                    ? order.takeProfitPrice!.toStringAsFixed(2)
                    : '未设置',
              ),
              _buildInfoItem('最大滑点', '${(order.maxSlippage * 100).toStringAsFixed(2)}%'),
              _buildInfoItem('最大点差', '${(order.maxSpread * 100).toStringAsFixed(2)}%'),
            ],
          ),
          
          const SizedBox(height: 20),
          
          _buildInfoSection(
            '触发条件',
            [
              _buildInfoItem(
                '条件ID',
                '${order.entryConditionId}',
              ),
              const _buildInfoNote(
                '注: 详细的条件配置信息需要在条件监控页面查看',
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 执行统计标签页
  Widget _buildExecutionStatsTab() {
    final order = widget.order;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildInfoSection(
            '执行统计',
            [
              _buildInfoItem('触发次数', '${order.triggerCount}'),
              _buildInfoItem('成功执行次数', '${order.executionCount}'),
              _buildInfoItem('最后执行时间', order.lastTriggered != null
                  ? DateFormat('yyyy-MM-dd HH:mm:ss').format(order.lastTriggered!)
                  : '未执行'),
            ],
          ),
          
          const SizedBox(height: 20),
          
          // 执行结果
          if (order.lastExecutionResult != null) ...[
            _buildInfoSection(
              '上次执行结果',
              _buildExecutionResultItems(order.lastExecutionResult!),
            ),
          ] else
            _buildInfoSection(
              '上次执行结果',
              [
                const _buildInfoNote('暂无执行记录'),
              ],
            ),
        ],
      ),
    );
  }

  /// 构建信息区域
  Widget _buildInfoSection(String title, List<Widget> children) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }

  /// 构建信息项
  Widget _buildInfoItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建信息提示
  Widget _buildInfoNote(String note) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Colors.amber.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.info_outline,
            size: 16,
            color: Colors.amber.shade700,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              note,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.amber.shade700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// 构建执行结果项
  List<Widget> _buildExecutionResultItems(Map<String, dynamic> result) {
    return result.entries.map((entry) {
      return _buildInfoItem(
        _getExecutionResultLabel(entry.key),
        entry.value.toString(),
      );
    }).toList();
  }

  /// 获取执行结果标签
  String _getExecutionResultLabel(String key) {
    switch (key) {
      case 'status':
        return '执行状态';
      case 'filled_quantity':
        return '成交数量';
      case 'average_price':
        return '平均价格';
      case 'commission':
        return '手续费';
      case 'pnl':
        return '盈亏';
      case 'execution_time':
        return '执行时间';
      case 'latency_ms':
        return '延迟(毫秒)';
      case 'error_message':
        return '错误信息';
      default:
        return key;
    }
  }

  /// 切换订单状态
  Future<void> _toggleOrderStatus() async {
    final notifier = ref.read(autoOrderProvider.notifier);
    await notifier.toggleOrderStatus(
      widget.order.id,
      !widget.order.isActive,
    );
  }

  /// 删除订单
  Future<void> _deleteOrder() async {
    Navigator.of(context).pop(); // 关闭对话框
    
    final notifier = ref.read(autoOrderProvider.notifier);
    await notifier.deleteAutoOrder(widget.order.id);
  }

  /// 获取状态颜色
  Color _getStatusColor() {
    switch (widget.order.status) {
      case OrderStatus.FILLED:
        return Colors.green;
      case OrderStatus.PARTIALLY_FILLED:
        return Colors.orange;
      case OrderStatus.CANCELLED:
        return Colors.grey;
      case OrderStatus.REJECTED:
        return Colors.red;
      default:
        return Colors.blue;
    }
  }

  /// 获取状态图标
  IconData _getStatusIcon() {
    switch (widget.order.status) {
      case OrderStatus.FILLED:
        return Icons.check_circle;
      case OrderStatus.PARTIALLY_FILLED:
        return Icons.hourglass_empty;
      case OrderStatus.CANCELLED:
        return Icons.cancel;
      case OrderStatus.REJECTED:
        return Icons.error;
      default:
        return Icons.pending;
    }
  }

  /// 获取状态文本
  String _getStatusText() {
    switch (widget.order.status) {
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
}