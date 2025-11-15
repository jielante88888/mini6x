import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/system_status_provider.dart';

class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final systemStatus = ref.watch(systemStatusProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('加密货币专业交易终端'),
        elevation: 0,
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        actions: [
          _buildSystemStatusIndicator(systemStatus),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              // TODO: 打开设置页面
            },
          ),
          IconButton(
            icon: const Icon(Icons.brightness_6),
            onPressed: () {
              // TODO: 切换主题
            },
          ),
        ],
      ),
      
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 系统状态卡片
            _buildSystemStatusCard(context, systemStatus),
            const SizedBox(height: 16),
            
            // 欢迎信息
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.welcome,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '欢迎使用加密货币专业交易终端',
                            style: TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        if (systemStatus.failoverActive)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.orange.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: Colors.orange.withOpacity(0.3)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.warning_amber, size: 14, color: Colors.orange),
                                const SizedBox(width: 4),
                                Text(
                                  'Failover',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.orange,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '支持币安和OKX现货/合约交易，提供实时行情监控和自动交易功能',
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.grey,
                      ),
                    ),
                    if (systemStatus.lastUpdate != null) ...[
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(
                            Icons.access_time,
                            size: 14,
                            color: Colors.grey,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '最后更新: ${_formatTime(systemStatus.lastUpdate!)}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: Colors.grey,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
            
            SizedBox(height: 24),
            
            // 功能入口
            Text(
              '主要功能',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
              ),
            ),
            
            SizedBox(height: 16),
            
            Expanded(
              child: GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 1.5,
                children: [
                  _buildFeatureCard(
                    icon: Icons.show_chart,
                    title: '现货市场',
                    subtitle: '实时行情监控',
                    color: Colors.blue,
                    statusColor: systemStatus.binanceStatus == ExchangeStatus.connected 
                        ? Colors.green : Colors.red,
                    statusText: 'Binance: ${systemStatus.binanceStatusDescription}',
                    onTap: () {
                      // TODO: 导航到现货市场页面
                    },
                  ),
                  
                  _buildFeatureCard(
                    icon: Icons.trending_up,
                    title: '合约交易',
                    subtitle: '杠杆交易功能',
                    color: Colors.orange,
                    statusColor: systemStatus.okxStatus == ExchangeStatus.connected 
                        ? Colors.green : Colors.red,
                    statusText: 'OKX: ${systemStatus.okxStatusDescription}',
                    onTap: () {
                      // TODO: 导航到合约市场页面
                    },
                  ),
                  
                  _buildFeatureCard(
                    icon: Icons.notifications,
                    title: '条件触发',
                    subtitle: '智能提醒设置',
                    color: Colors.green,
                    statusColor: systemStatus.hasWarning ? Colors.orange : Colors.green,
                    statusText: systemStatus.hasWarning ? '部分服务异常' : '服务正常',
                    onTap: () {
                      // TODO: 导航到条件设置页面
                    },
                  ),
                  
                  _buildFeatureCard(
                    icon: Icons.auto_mode,
                    title: '自动交易',
                    subtitle: '策略交易系统',
                    color: Colors.purple,
                    statusColor: systemStatus.primaryExchange != 'none' ? Colors.green : Colors.red,
                    statusText: systemStatus.primaryExchange != 'none' 
                        ? '主: ${systemStatus.primaryExchange.toUpperCase()}' 
                        : '无可用交易所',
                    onTap: () {
                      // TODO: 导航到自动交易页面
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildFeatureCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required Color statusColor,
    required String statusText,
    required VoidCallback onTap,
  }) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: statusColor,
                      shape: BoxShape.circle,
                    ),
                  ),
                ],
              ),
              Icon(
                icon,
                size: 48,
                color: color,
              ),
              const SizedBox(height: 12),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: const TextStyle(
                  fontSize: 14,
                  color: Colors.grey,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: statusColor.withOpacity(0.3)),
                ),
                child: Text(
                  statusText,
                  style: TextStyle(
                    fontSize: 10,
                    color: statusColor,
                    fontWeight: FontWeight.w500,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建系统状态指示器
  Widget _buildSystemStatusIndicator(SystemStatusData systemStatus) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _parseColor(systemStatus.overallStatusColor),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            systemStatus.overallStatusDescription,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建系统状态卡片
  Widget _buildSystemStatusCard(BuildContext context, SystemStatusData systemStatus) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.monitor_heart_outlined,
                  color: _parseColor(systemStatus.overallStatusColor),
                ),
                const SizedBox(width: 8),
                Text(
                  '系统状态监控',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _parseColor(systemStatus.overallStatusColor),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    systemStatus.overallStatusDescription,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            // 交易所状态
            Row(
              children: [
                Expanded(
                  child: _buildExchangeStatusItem(
                    'Binance',
                    systemStatus.binanceStatus,
                    systemStatus.binanceLatency,
                    systemStatus.binanceStatusDescription,
                    context,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildExchangeStatusItem(
                    'OKX',
                    systemStatus.okxStatus,
                    systemStatus.okxLatency,
                    systemStatus.okxStatusDescription,
                    context,
                  ),
                ),
              ],
            ),
            
            if (systemStatus.failoverActive && systemStatus.failoverTime != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.warning_amber, color: Colors.orange, size: 16),
                    const SizedBox(width: 4),
                    Text(
                      'Failover 激活于: ${_formatTime(systemStatus.failoverTime!)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.orange,
                      ),
                    ),
                  ],
                ),
              ),
            ],
            
            if (systemStatus.errorMessage != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red, size: 16),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        systemStatus.errorMessage!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.red,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 16, color: Colors.red),
                      onPressed: () {
                        // TODO: 清除错误信息
                      },
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建交易所状态项
  Widget _buildExchangeStatusItem(
    String name,
    ExchangeStatus status,
    int? latency,
    String description,
    BuildContext context,
  ) {
    final statusColor = _getStatusColor(status);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: statusColor,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              name,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          description,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: statusColor,
          ),
        ),
        if (latency != null) ...[
          const SizedBox(height: 2),
          Text(
            '延迟: ${latency}ms',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey,
            ),
          ),
        ],
      ],
    );
  }

  /// 获取状态颜色
  Color _getStatusColor(ExchangeStatus status) {
    switch (status) {
      case ExchangeStatus.connected:
        return Colors.green;
      case ExchangeStatus.reconnecting:
        return Colors.orange;
      case ExchangeStatus.disconnected:
        return Colors.red;
      case ExchangeStatus.error:
        return Colors.red.shade700;
      case ExchangeStatus.maintenance:
        return Colors.purple;
    }
  }

  /// 解析颜色字符串
  Color _parseColor(String hexColor) {
    try {
      return Color(int.parse(hexColor.replaceFirst('#', '0xff')));
    } catch (e) {
      return Colors.grey;
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