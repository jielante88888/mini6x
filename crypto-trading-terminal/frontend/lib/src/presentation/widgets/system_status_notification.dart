import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/system_status_provider.dart';

/// 系统状态通知Widget
class SystemStatusNotification extends ConsumerWidget {
  const SystemStatusNotification({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final systemStatus = ref.watch(systemStatusProvider);
    final shouldShow = ref.watch(shouldShowStatusNotificationProvider);

    if (!shouldShow) {
      return const SizedBox.shrink();
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: const EdgeInsets.all(8),
      child: Card(
        elevation: 4,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    _getNotificationIcon(systemStatus),
                    color: _getNotificationColor(systemStatus),
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _getNotificationTitle(systemStatus),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: _getNotificationColor(systemStatus),
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 16),
                    onPressed: () {
                      ref.read(systemStatusProvider.notifier).clearError();
                    },
                  ),
                ],
              ),
              if (systemStatus.errorMessage != null) ...[
                const SizedBox(height: 4),
                Text(
                  systemStatus.errorMessage!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: _getNotificationColor(systemStatus),
                  ),
                ),
              ],
              const SizedBox(height: 8),
              
              // 快速操作按钮
              Row(
                children: [
                  _buildQuickActionButton(
                    context,
                    '查看详情',
                    Icons.info_outline,
                    () => _showDetailedStatus(context, ref),
                  ),
                  const SizedBox(width: 8),
                  if (systemStatus.binanceStatus == ExchangeStatus.disconnected ||
                      systemStatus.okxStatus == ExchangeStatus.disconnected) ...[
                    _buildQuickActionButton(
                      context,
                      '重连',
                      Icons.refresh,
                      () => _performReconnection(context, ref),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 获取通知图标
  IconData _getNotificationIcon(SystemStatusData systemStatus) {
    if (systemStatus.failoverActive) {
      return Icons.warning_amber;
    } else if (systemStatus.binanceStatus == ExchangeStatus.disconnected &&
               systemStatus.okxStatus == ExchangeStatus.disconnected) {
      return Icons.error_outline;
    } else if (systemStatus.binanceStatus == ExchangeStatus.disconnected ||
               systemStatus.okxStatus == ExchangeStatus.disconnected) {
      return Icons.warning_outlined;
    } else if (systemStatus.binanceStatus == ExchangeStatus.reconnecting ||
               systemStatus.okxStatus == ExchangeStatus.reconnecting) {
      return Icons.sync;
    } else {
      return Icons.info_outline;
    }
  }

  /// 获取通知颜色
  Color _getNotificationColor(SystemStatusData systemStatus) {
    if (systemStatus.failoverActive) {
      return Colors.orange;
    } else if (systemStatus.binanceStatus == ExchangeStatus.disconnected &&
               systemStatus.okxStatus == ExchangeStatus.disconnected) {
      return Colors.red;
    } else if (systemStatus.binanceStatus == ExchangeStatus.disconnected ||
               systemStatus.okxStatus == ExchangeStatus.disconnected) {
      return Colors.orange;
    } else if (systemStatus.binanceStatus == ExchangeStatus.reconnecting ||
               systemStatus.okxStatus == ExchangeStatus.reconnecting) {
      return Colors.blue;
    } else {
      return Colors.green;
    }
  }

  /// 获取通知标题
  String _getNotificationTitle(SystemStatusData systemStatus) {
    if (systemStatus.failoverActive) {
      return '系统故障转移已激活';
    } else if (systemStatus.binanceStatus == ExchangeStatus.disconnected &&
               systemStatus.okxStatus == ExchangeStatus.disconnected) {
      return '所有交易所连接中断';
    } else if (systemStatus.binanceStatus == ExchangeStatus.disconnected ||
               systemStatus.okxStatus == ExchangeStatus.disconnected) {
      return '部分交易所连接异常';
    } else if (systemStatus.binanceStatus == ExchangeStatus.reconnecting ||
               systemStatus.okxStatus == ExchangeStatus.reconnecting) {
      return '正在重连交易所...';
    } else {
      return '系统状态正常';
    }
  }

  /// 构建快速操作按钮
  Widget _buildQuickActionButton(
    BuildContext context,
    String label,
    IconData icon,
    VoidCallback onTap,
  ) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: _getNotificationColor(
            // 这里需要一个系统状态对象，但我们只关心颜色
            const SystemStatusData(
              binanceStatus: ExchangeStatus.connected,
              okxStatus: ExchangeStatus.connected,
              activeMarketType: MarketType.spot,
              activeExchange: 'binance',
            ),
          ).withOpacity(0.1),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: _getNotificationColor(
                const SystemStatusData(
                  binanceStatus: ExchangeStatus.connected,
                  okxStatus: ExchangeStatus.connected,
                  activeMarketType: MarketType.spot,
                  activeExchange: 'binance',
                ),
              ),
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: _getNotificationColor(
                  const SystemStatusData(
                    binanceStatus: ExchangeStatus.connected,
                    okxStatus: ExchangeStatus.connected,
                    activeMarketType: MarketType.spot,
                    activeExchange: 'binance',
                  ),
                ),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 显示详细状态
  void _showDetailedStatus(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => SystemStatusDetailSheet(),
    );
  }

  /// 执行重连操作
  void _performReconnection(BuildContext context, WidgetRef ref) {
    final systemStatus = ref.read(systemStatusProvider);
    
    if (systemStatus.binanceStatus == ExchangeStatus.disconnected) {
      ref.read(systemStatusProvider.notifier).reconnectExchange('binance');
    }
    
    if (systemStatus.okxStatus == ExchangeStatus.disconnected) {
      ref.read(systemStatusProvider.notifier).reconnectExchange('okx');
    }
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('正在尝试重连断开的交易所...'),
        duration: Duration(seconds: 2),
      ),
    );
  }
}

/// 系统状态详情底部弹窗
class SystemStatusDetailSheet extends ConsumerWidget {
  const SystemStatusDetailSheet({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final systemStatus = ref.watch(systemStatusProvider);
    
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题栏
            Row(
              children: [
                Icon(
                  Icons.monitor_heart_outlined,
                  color: Theme.of(context).colorScheme.primary,
                  size: 24,
                ),
                const SizedBox(width: 8),
                Text(
                  '系统状态详情',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            
            const SizedBox(height: 20),
            
            // 总体状态
            _buildStatusSection(
              context,
              '系统概览',
              [
                _buildStatusRow(
                  '总体状态',
                  systemStatus.overallStatusDescription,
                  _getStatusColor(systemStatus.binanceStatus == ExchangeStatus.connected && 
                                 systemStatus.okxStatus == ExchangeStatus.connected),
                ),
                _buildStatusRow(
                  '活跃市场',
                  systemStatus.activeMarketType.name.toUpperCase(),
                  Theme.of(context).colorScheme.primary,
                ),
                _buildStatusRow(
                  '主交易所',
                  systemStatus.primaryExchange.toUpperCase(),
                  Theme.of(context).colorScheme.secondary,
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Binance状态
            _buildStatusSection(
              context,
              'Binance 状态',
              [
                _buildStatusRow(
                  '连接状态',
                  systemStatus.binanceStatusDescription,
                  _getStatusColor(systemStatus.binanceStatus),
                ),
                if (systemStatus.binanceLatency != null)
                  _buildStatusRow(
                    '响应延迟',
                    '${systemStatus.binanceLatency}ms',
                    systemStatus.binanceLatency! < 100 ? Colors.green : 
                    systemStatus.binanceLatency! < 300 ? Colors.orange : Colors.red,
                  ),
                _buildActionRow(
                  context,
                  '重新连接',
                  Icons.refresh,
                  () {
                    ref.read(systemStatusProvider.notifier).reconnectExchange('binance');
                    Navigator.of(context).pop();
                  },
                  systemStatus.binanceStatus == ExchangeStatus.connected,
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // OKX状态
            _buildStatusSection(
              context,
              'OKX 状态',
              [
                _buildStatusRow(
                  '连接状态',
                  systemStatus.okxStatusDescription,
                  _getStatusColor(systemStatus.okxStatus),
                ),
                if (systemStatus.okxLatency != null)
                  _buildStatusRow(
                    '响应延迟',
                    '${systemStatus.okxLatency}ms',
                    systemStatus.okxLatency! < 100 ? Colors.green : 
                    systemStatus.okxLatency! < 300 ? Colors.orange : Colors.red,
                  ),
                _buildActionRow(
                  context,
                  '重新连接',
                  Icons.refresh,
                  () {
                    ref.read(systemStatusProvider.notifier).reconnectExchange('okx');
                    Navigator.of(context).pop();
                  },
                  systemStatus.okxStatus == ExchangeStatus.connected,
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // 故障转移信息
            if (systemStatus.failoverActive)
              _buildStatusSection(
                context,
                '故障转移',
                [
                  _buildStatusRow(
                    '状态',
                    '已激活',
                    Colors.orange,
                  ),
                  if (systemStatus.failoverTime != null)
                    _buildStatusRow(
                      '激活时间',
                      _formatTime(systemStatus.failoverTime!),
                      Colors.grey,
                    ),
                ],
              ),
            
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  /// 构建状态部分
  Widget _buildStatusSection(BuildContext context, String title, List<Widget> children) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }

  /// 构建状态行
  Widget _buildStatusRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontWeight: FontWeight.w500,
            ),
          ),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                value,
                style: TextStyle(
                  fontWeight: FontWeight.w500,
                  color: color,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建操作行
  Widget _buildActionRow(
    BuildContext context,
    String label,
    IconData icon,
    VoidCallback onTap,
    bool disabled,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontWeight: FontWeight.w500,
            ),
          ),
          ElevatedButton.icon(
            onPressed: disabled ? null : onTap,
            icon: Icon(icon, size: 16),
            label: const Text('执行'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            ),
          ),
        ],
      ),
    );
  }

  /// 获取状态颜色
  Color _getStatusColor(ExchangeStatus status) {
    switch (status) {
      case ExchangeStatus.connected:
        return Colors.green;
      case ExchangeStatus.reconnecting:
        return Colors.blue;
      case ExchangeStatus.disconnected:
        return Colors.red;
      case ExchangeStatus.error:
        return Colors.red.shade700;
      case ExchangeStatus.maintenance:
        return Colors.purple;
    }
  }

  /// 格式化时间
  String _formatTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inSeconds < 60) {
      return '${difference.inSeconds}秒前';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}分钟前';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}小时前';
    } else {
      return '${difference.inDays}天前';
    }
  }
}

/// 交易所连接状态指示器Widget
class ExchangeStatusIndicator extends ConsumerWidget {
  final String exchange;
  final bool compact;

  const ExchangeStatusIndicator({
    super.key,
    required this.exchange,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final systemStatus = ref.watch(systemStatusProvider);
    final status = exchange.toLowerCase() == 'binance' 
        ? systemStatus.binanceStatus 
        : systemStatus.okxStatus;
    final latency = exchange.toLowerCase() == 'binance' 
        ? systemStatus.binanceLatency 
        : systemStatus.okxLatency;

    if (compact) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: _getStatusColor(status).withOpacity(0.2),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 4,
              height: 4,
              decoration: BoxDecoration(
                color: _getStatusColor(status),
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 3),
            Text(
              exchange.toUpperCase(),
              style: TextStyle(
                fontSize: 10,
                color: _getStatusColor(status),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _getStatusColor(status).withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _getStatusColor(status).withOpacity(0.3)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  color: _getStatusColor(status),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 4),
              Text(
                '${exchange.toUpperCase()} ${_getStatusDescription(status)}',
                style: TextStyle(
                  fontSize: 11,
                  color: _getStatusColor(status),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          if (latency != null) ...[
            const SizedBox(height: 1),
            Text(
              '${latency}ms',
              style: TextStyle(
                fontSize: 9,
                color: Colors.grey,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Color _getStatusColor(ExchangeStatus status) {
    switch (status) {
      case ExchangeStatus.connected:
        return Colors.green;
      case ExchangeStatus.reconnecting:
        return Colors.blue;
      case ExchangeStatus.disconnected:
        return Colors.red;
      case ExchangeStatus.error:
        return Colors.red.shade700;
      case ExchangeStatus.maintenance:
        return Colors.purple;
    }
  }

  String _getStatusDescription(ExchangeStatus status) {
    switch (status) {
      case ExchangeStatus.connected:
        return '在线';
      case ExchangeStatus.reconnecting:
        return '重连';
      case ExchangeStatus.disconnected:
        return '离线';
      case ExchangeStatus.error:
        return '错误';
      case ExchangeStatus.maintenance:
        return '维护';
    }
  }
}