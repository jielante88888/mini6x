import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/notification_provider.dart';
import 'channel_config_dialog_widget.dart';

/// 通知渠道管理Widget
/// 显示和管理所有通知渠道的列表和状态
class NotificationChannelsWidget extends ConsumerWidget {
  const NotificationChannelsWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationState = ref.watch(notificationProvider);
    final channelsByType = ref.watch(channelsByTypeProvider);
    final testStatus = ref.watch(channelTestStatusProvider);

    if (notificationState.channels.isEmpty) {
      return _buildEmptyState(context);
    }

    return RefreshIndicator(
      onRefresh: () async => ref.refresh(notificationProvider),
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: channelsByType.length,
        itemBuilder: (context, index) {
          final type = channelsByType.keys.elementAt(index);
          final channels = channelsByType[type]!;
          return _buildChannelTypeSection(context, type, channels, testStatus, ref);
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
            Icons.notifications_off,
            size: 64,
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            '暂无通知渠道',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
          ),
          const SizedBox(height: 8),
          Text(
            '点击右下角按钮添加第一个通知渠道',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                ),
          ),
        ],
      ),
    );
  }

  /// 构建渠道类型区块
  Widget _buildChannelTypeSection(
    BuildContext context,
    NotificationChannelType type,
    List<NotificationChannelConfig> channels,
    Map<String, String> testStatus,
    WidgetRef ref,
  ) {
    final enabledCount = channels.where((c) => c.enabled).length;
    final totalCount = channels.length;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Column(
        children: [
          // 区块标题
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
            ),
            child: Row(
              children: [
                Icon(
                  type.icon,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        type.displayName,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      Text(
                        '已启用 $enabledCount/$totalCount 个渠道',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                            ),
                      ),
                    ],
                  ),
                ),
                _buildTypeActions(context, type, channels, ref),
              ],
            ),
          ),
          
          // 渠道列表
          ...channels.asMap().entries.map((entry) {
            final index = entry.key;
            final channel = entry.value;
            final isLast = index == channels.length - 1;
            
            return _buildChannelItem(
              context,
              channel,
              testStatus,
              ref,
              isLast: isLast,
            );
          }),
        ],
      ),
    );
  }

  /// 构建渠道类型操作
  Widget _buildTypeActions(
    BuildContext context,
    NotificationChannelType type,
    List<NotificationChannelConfig> channels,
    WidgetRef ref,
  ) {
    final enabledChannels = channels.where((c) => c.enabled).toList();
    
    return PopupMenuButton<String>(
      icon: const Icon(Icons.more_vert),
      onSelected: (value) async {
        switch (value) {
          case 'test_all':
            for (final channel in enabledChannels) {
              await ref.read(notificationProvider.notifier).testChannel(channel.id);
            }
            break;
          case 'enable_all':
            for (final channel in channels.where((c) => !c.enabled)) {
              await ref.read(notificationProvider.notifier).toggleChannel(channel.id);
            }
            break;
          case 'disable_all':
            for (final channel in channels.where((c) => c.enabled)) {
              await ref.read(notificationProvider.notifier).toggleChannel(channel.id);
            }
            break;
        }
      },
      itemBuilder: (context) => [
        if (enabledChannels.isNotEmpty)
          const PopupMenuItem(
            value: 'test_all',
            child: ListTile(
              leading: Icon(Icons.play_arrow),
              title: Text('测试全部'),
              contentPadding: EdgeInsets.zero,
              visualDensity: VisualDensity.compact,
            ),
          ),
        const PopupMenuItem(
          value: 'enable_all',
          child: ListTile(
            leading: Icon(Icons.check_circle),
            title: Text('全部启用'),
            contentPadding: EdgeInsets.zero,
            visualDensity: VisualDensity.compact,
          ),
        ),
        const PopupMenuItem(
          value: 'disable_all',
          child: ListTile(
            leading: Icon(Icons.cancel),
            title: Text('全部禁用'),
            contentPadding: EdgeInsets.zero,
            visualDensity: VisualDensity.compact,
          ),
        ),
      ],
    );
  }

  /// 构建渠道项
  Widget _buildChannelItem(
    BuildContext context,
    NotificationChannelConfig channel,
    Map<String, String> testStatus,
    WidgetRef ref, {
    bool isLast = false,
  }) {
    final theme = Theme.of(context);
    final testResult = testStatus[channel.id];

    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: isLast
              ? BorderSide.none
              : BorderSide(
                  color: theme.colorScheme.outline.withOpacity(0.2),
                  width: 1,
                ),
        ),
      ),
      child: ListTile(
        leading: _buildChannelIcon(context, channel, testResult),
        title: Row(
          children: [
            Expanded(
              child: Text(
                channel.name,
                style: theme.textTheme.titleMedium,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            _buildStatusChip(context, channel, testResult),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              channel.description,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            _buildChannelStats(context, channel),
          ],
        ),
        trailing: _buildChannelActions(context, channel, testResult, ref),
        onTap: () => _showChannelDetails(context, channel, ref),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
    );
  }

  /// 构建渠道图标
  Widget _buildChannelIcon(BuildContext context, NotificationChannelConfig channel, String? testResult) {
    Color iconColor;
    
    if (testResult == 'testing') {
      iconColor = Colors.orange;
    } else if (testResult == 'error') {
      iconColor = Colors.red;
    } else if (channel.status == ChannelStatus.enabled) {
      iconColor = Colors.green;
    } else {
      iconColor = Colors.grey;
    }

    return Stack(
      children: [
        Icon(
          channel.type.icon,
          color: iconColor,
          size: 32,
        ),
        if (testResult == 'testing')
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

  /// 构建状态标签
  Widget _buildStatusChip(BuildContext context, NotificationChannelConfig channel, String? testResult) {
    String text;
    Color color;
    
    if (testResult == 'testing') {
      text = '测试中';
      color = Colors.orange;
    } else if (testResult == 'error') {
      text = '连接失败';
      color = Colors.red;
    } else {
      switch (channel.status) {
        case ChannelStatus.enabled:
          text = '已启用';
          color = Colors.green;
          break;
        case ChannelStatus.disabled:
          text = '已禁用';
          color = Colors.grey;
          break;
        case ChannelStatus.error:
          text = '配置错误';
          color = Colors.red;
          break;
        case ChannelStatus.testing:
          text = '测试中';
          color = Colors.orange;
          break;
      }
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  /// 构建渠道统计
  Widget _buildChannelStats(BuildContext context, NotificationChannelConfig channel) {
    return Row(
      children: [
        // 发送次数
        Icon(
          Icons.send,
          size: 14,
          color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
        ),
        const SizedBox(width: 4),
        Text(
          '${channel.totalSent}',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
        ),
        const SizedBox(width: 12),
        // 成功率
        Icon(
          Icons.trending_up,
          size: 14,
          color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
        ),
        const SizedBox(width: 4),
        Text(
          '${channel.successRate.toStringAsFixed(1)}%',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
        ),
        const SizedBox(width: 12),
        // 最后使用时间
        if (channel.lastUsed != null) ...[
          Icon(
            Icons.access_time,
            size: 14,
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
          ),
          const SizedBox(width: 4),
          Text(
            '最后: ${_formatRelativeTime(channel.lastUsed!)}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
          ),
        ],
      ],
    );
  }

  /// 构建渠道操作按钮
  Widget _buildChannelActions(
    BuildContext context,
    NotificationChannelConfig channel,
    String? testResult,
    WidgetRef ref,
  ) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 测试按钮
        IconButton(
          onPressed: testResult == 'testing' 
              ? null 
              : () => ref.read(notificationProvider.notifier).testChannel(channel.id),
          icon: Icon(
            testResult == 'testing' ? Icons.sync : Icons.play_arrow,
            color: testResult == 'testing' ? Colors.orange : Colors.blue,
          ),
          tooltip: '测试连接',
        ),
        // 设置按钮
        IconButton(
          onPressed: () => _showChannelConfig(context, channel, ref),
          icon: const Icon(Icons.settings, color: Colors.grey),
          tooltip: '配置设置',
        ),
      ],
    );
  }

  /// 显示渠道详情
  void _showChannelDetails(BuildContext context, NotificationChannelConfig channel, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildChannelDetailsSheet(context, channel),
    );
  }

  /// 构建渠道详情底部表单
  Widget _buildChannelDetailsSheet(BuildContext context, NotificationChannelConfig channel) {
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
                        Icon(channel.type.icon, size: 32),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                channel.name,
                                style: Theme.of(context).textTheme.headlineSmall,
                              ),
                              Text(
                                channel.description,
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                    ),
                              ),
                            ],
                          ),
                        ),
                        _buildStatusChip(context, channel, null),
                      ],
                    ),
                    const SizedBox(height: 24),
                    
                    // 统计信息
                    _buildDetailSection(
                      context,
                      '使用统计',
                      [
                        _buildDetailItem('总发送', '${channel.totalSent}次'),
                        _buildDetailItem('成功发送', '${channel.statistics['successful'] ?? 0}次'),
                        _buildDetailItem('失败次数', '${channel.statistics['failed'] ?? 0}次'),
                        _buildDetailItem('成功率', '${channel.successRate.toStringAsFixed(1)}%'),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // 配置信息
                    _buildDetailSection(
                      context,
                      '配置信息',
                      [
                        _buildDetailItem('模板类型', channel.templateTypes.join(', ')),
                        _buildDetailItem('创建时间', _formatDateTime(channel.createdAt)),
                        _buildDetailItem('更新时间', _formatDateTime(channel.updatedAt)),
                        if (channel.lastUsed != null)
                          _buildDetailItem('最后使用', _formatDateTime(channel.lastUsed!)),
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
                        onPressed: () => _showChannelConfig(context, channel, ref),
                        child: const Text('编辑配置'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () {
                          ref.read(notificationProvider.notifier).toggleChannel(channel.id);
                          Navigator.of(context).pop();
                        },
                        child: Text(channel.enabled ? '禁用' : '启用'),
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

  /// 显示渠道配置
  void _showChannelConfig(BuildContext context, NotificationChannelConfig channel, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => ChannelConfigDialogWidget(
        channel: channel,
        onSaved: (updatedChannel) {
          ref.read(notificationProvider.notifier).updateChannel(updatedChannel);
          Navigator.of(context).pop();
        },
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
