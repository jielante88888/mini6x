import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/notification_provider.dart';
import '../../widgets/common/app_bar_widget.dart';
import '../../widgets/common/loading_widget.dart';
import '../../widgets/common/error_widget.dart';
import 'notification_channels_widget.dart';
import 'notification_templates_widget.dart';
import 'notification_global_settings_widget.dart';

/// 通知设置页面
/// 提供通知渠道管理、模板配置和全局设置功能
class NotificationSettingsPage extends ConsumerStatefulWidget {
  const NotificationSettingsPage({super.key});

  @override
  ConsumerState<NotificationSettingsPage> createState() => _NotificationSettingsPageState();
}

class _NotificationSettingsPageState extends ConsumerState<NotificationSettingsPage>
    with TickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final notificationState = ref.watch(notificationProvider);
    final statistics = ref.read(notificationProvider.notifier).getChannelStatistics();

    return Scaffold(
      appBar: AppBarWidget(
        title: '通知设置',
        actions: [
          IconButton(
            onPressed: _showHelp,
            icon: const Icon(Icons.help_outline),
            tooltip: '帮助',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(100),
          child: Container(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                // 统计信息卡片
                _buildStatisticsCard(context, statistics),
                const SizedBox(height: 8),
                // Tab栏
                TabBar(
                  controller: _tabController,
                  labelColor: theme.colorScheme.primary,
                  unselectedLabelColor: theme.colorScheme.onSurface.withOpacity(0.6),
                  indicatorColor: theme.colorScheme.primary,
                  indicatorWeight: 2,
                  tabs: const [
                    Tab(icon: Icon(Icons.tune), text: '渠道管理'),
                    Tab(icon: Icon(Icons.text_snippet), text: '模板设置'),
                    Tab(icon: Icon(Icons.settings), text: '全局设置'),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
      body: notificationState.isLoading
          ? const LoadingWidget(message: '正在加载通知设置...')
          : notificationState.error != null
              ? ErrorWidget(
                  message: notificationState.error!,
                  onRetry: () {
                    ref.read(notificationProvider.notifier).clearError();
                    ref.refresh(notificationProvider);
                  },
                )
              : _buildTabContent(),
      floatingActionButton: _buildFAB(),
    );
  }

  /// 构建统计信息卡片
  Widget _buildStatisticsCard(BuildContext context, Map<String, int> statistics) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // 总渠道数
            Expanded(
              child: _buildStatItem(
                context,
                '渠道数',
                '${statistics['total_channels'] ?? 0}',
                Icons.channel,
                theme.colorScheme.primary,
              ),
            ),
            Container(
              width: 1,
              height: 40,
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
            // 已启用渠道
            Expanded(
              child: _buildStatItem(
                context,
                '已启用',
                '${statistics['enabled_channels'] ?? 0}',
                Icons.check_circle,
                Colors.green,
              ),
            ),
            Container(
              width: 1,
              height: 40,
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
            // 总发送数
            Expanded(
              child: _buildStatItem(
                context,
                '发送数',
                '${statistics['total_sent'] ?? 0}',
                Icons.send,
                theme.colorScheme.secondary,
              ),
            ),
            Container(
              width: 1,
              height: 40,
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
            // 成功率
            Expanded(
              child: _buildStatItem(
                context,
                '成功率',
                '${statistics['total_sent']! > 0 ? ((statistics['total_successful']! / statistics['total_sent']!) * 100).toStringAsFixed(1) : '0'}%',
                Icons.trending_up,
                Colors.blue,
              ),
            ),
          ],
        ),
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
        Icon(icon, color: color, size: 20),
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
        ),
      ],
    );
  }

  /// 构建Tab内容
  Widget _buildTabContent() {
    return TabBarView(
      controller: _tabController,
      children: const [
        NotificationChannelsWidget(),
        NotificationTemplatesWidget(),
        NotificationGlobalSettingsWidget(),
      ],
    );
  }

  /// 构建浮动操作按钮
  Widget? _buildFAB() {
    if (_tabController.index == 0) {
      // 渠道管理页面
      return FloatingActionButton.extended(
        onPressed: () => _showAddChannelDialog(),
        icon: const Icon(Icons.add),
        label: const Text('添加渠道'),
      );
    }
    return null;
  }

  /// 显示添加渠道对话框
  void _showAddChannelDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('选择通知渠道'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildChannelOption(
              context,
              NotificationChannelType.popup,
              () {
                Navigator.of(context).pop();
                _showChannelConfigDialog(NotificationChannelType.popup);
              },
            ),
            _buildChannelOption(
              context,
              NotificationChannelType.desktop,
              () {
                Navigator.of(context).pop();
                _showChannelConfigDialog(NotificationChannelType.desktop);
              },
            ),
            _buildChannelOption(
              context,
              NotificationChannelType.telegram,
              () {
                Navigator.of(context).pop();
                _showChannelConfigDialog(NotificationChannelType.telegram);
              },
            ),
            _buildChannelOption(
              context,
              NotificationChannelType.email,
              () {
                Navigator.of(context).pop();
                _showChannelConfigDialog(NotificationChannelType.email);
              },
            ),
          ],
        ),
      ),
    );
  }

  /// 构建渠道选项
  Widget _buildChannelOption(
    BuildContext context,
    NotificationChannelType type,
    VoidCallback onTap,
  ) {
    return ListTile(
      leading: Icon(type.icon),
      title: Text(type.displayName),
      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
      onTap: onTap,
    );
  }

  /// 显示渠道配置对话框
  void _showChannelConfigDialog(NotificationChannelType type) {
    // TODO: 实现渠道配置对话框
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${type.displayName}渠道配置功能待实现')),
    );
  }

  /// 显示帮助
  void _showHelp() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('通知设置帮助'),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('渠道管理'),
              SizedBox(height: 8),
              Text('• 管理不同的通知渠道（弹窗、桌面、Telegram、邮件）'),
              Text('• 启用/禁用渠道和测试连接状态'),
              SizedBox(height: 16),
              Text('模板设置'),
              SizedBox(height: 8),
              Text('• 自定义不同类型预警的模板内容'),
              Text('• 支持变量替换和格式化'),
              SizedBox(height: 16),
              Text('全局设置'),
              SizedBox(height: 8),
              Text('• 配置通用的通知行为和选项'),
              Text('• 控制声音、震动等全局特性'),
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
