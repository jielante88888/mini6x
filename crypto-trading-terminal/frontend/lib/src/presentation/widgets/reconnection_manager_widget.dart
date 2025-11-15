import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/reconnection_provider.dart';
import '../providers/system_status_provider.dart';

/// 重连管理Widget
class ReconnectionManagerWidget extends ConsumerWidget {
  final String exchange;
  final FailureType failureType;

  const ReconnectionManagerWidget({
    super.key,
    required this.exchange,
    required this.failureType,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reconnectionState = ref.watch(reconnectionProvider)[exchange];
    final systemStatus = ref.watch(systemStatusProvider);
    final statistics = ref.read(reconnectionManagerProvider).getStatistics(exchange);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            Row(
              children: [
                Icon(
                  _getExchangeIcon(exchange),
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${exchange.toUpperCase()} 重连管理',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                _buildReconnectionStateIndicator(reconnectionState),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // 失败信息
            _buildFailureInfo(context, failureType),
            
            const SizedBox(height: 12),
            
            // 重连统计
            _buildStatisticsCard(context, statistics),
            
            const SizedBox(height: 12),
            
            // 重连控制
            _buildReconnectionControls(context, ref, reconnectionState),
            
            const SizedBox(height: 12),
            
            // 策略配置
            _buildStrategyConfiguration(context, ref),
          ],
        ),
      ),
    );
  }

  /// 构建交易所图标
  IconData _getExchangeIcon(String exchange) {
    switch (exchange.toLowerCase()) {
      case 'binance':
        return Icons.currency_exchange;
      case 'okx':
        return Icons.account_balance;
      default:
        return Icons.exchange;
    }
  }

  /// 构建重连状态指示器
  Widget _buildReconnectionStateIndicator(ReconnectionState? state) {
    if (state == null) return const SizedBox.shrink();

    Color color;
    IconData icon;
    String text;

    switch (state) {
      case ReconnectionState.idle:
        color = Colors.grey;
        icon = Icons.pause_circle_outline;
        text = '空闲';
        break;
      case ReconnectionState.attempting:
        color = Colors.blue;
        icon = Icons.sync;
        text = '重连中';
        break;
      case ReconnectionState.scheduled:
        color = Colors.orange;
        icon = Icons.schedule;
        text = '计划重连';
        break;
      case ReconnectionState.backoff:
        color = Colors.orange;
        icon = Icons.timer;
        text = '退避中';
        break;
      case ReconnectionState.success:
        color = Colors.green;
        icon = Icons.check_circle;
        text = '重连成功';
        break;
      case ReconnectionState.failed:
        color = Colors.red;
        icon = Icons.error;
        text = '重连失败';
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
          Icon(
            icon,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              fontSize: 12,
              color: color,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建失败信息
  Widget _buildFailureInfo(BuildContext context, FailureType failureType) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _getFailureColor(failureType).withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            _getFailureIcon(failureType),
            color: _getFailureColor(failureType),
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '失败类型: ${_getFailureTypeName(failureType)}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: _getFailureColor(failureType),
                  ),
                ),
                Text(
                  _getFailureDescription(failureType),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: _getFailureColor(failureType),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// 构建统计信息卡片
  Widget _buildStatisticsCard(BuildContext context, ReconnectionStatistics statistics) {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceVariant,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '重连统计 (最近24小时)',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    '总尝试',
                    '${statistics.totalAttempts}',
                    Icons.refresh,
                    Colors.blue,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    '成功',
                    '${statistics.successfulAttempts}',
                    Icons.check_circle,
                    Colors.green,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    '失败',
                    '${statistics.failedAttempts}',
                    Icons.error,
                    Colors.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    '成功率',
                    '${(statistics.successRate * 100).toStringAsFixed(1)}%',
                    Icons.analytics,
                    statistics.successRate > 0.7 ? Colors.green : 
                    statistics.successRate > 0.3 ? Colors.orange : Colors.red,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    '平均延迟',
                    '${statistics.averageDelay.inSeconds}秒',
                    Icons.timer,
                    Colors.purple,
                  ),
                ),
              ],
            ),
            if (statistics.lastAttempt != null) ...[
              const SizedBox(height: 8),
              Text(
                '最后尝试: ${_formatTimeAgo(statistics.lastAttempt!.timestamp)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建统计项
  Widget _buildStatItem(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 16),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
        Text(
          label,
          style: const TextStyle(fontSize: 10),
        ),
      ],
    );
  }

  /// 构建重连控制按钮
  Widget _buildReconnectionControls(BuildContext context, WidgetRef ref, ReconnectionState? state) {
    final isProcessing = state == ReconnectionState.attempting || 
                        state == ReconnectionState.scheduled || 
                        state == ReconnectionState.backoff;

    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: isProcessing ? null : () => _startReconnection(context, ref),
            icon: Icon(isProcessing ? Icons.sync : Icons.refresh),
            label: Text(isProcessing ? '重连中...' : '开始重连'),
            style: ElevatedButton.styleFrom(
              backgroundColor: isProcessing ? Colors.grey.shade300 : null,
            ),
          ),
        ),
        const SizedBox(width: 8),
        if (!isProcessing && state != ReconnectionState.idle)
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => _cancelReconnection(context, ref),
              icon: const Icon(Icons.stop),
              label: const Text('取消'),
            ),
          ),
      ],
    );
  }

  /// 构建策略配置
  Widget _buildStrategyConfiguration(BuildContext context, WidgetRef ref) {
    return ExpansionTile(
      title: const Text('重连策略配置'),
      children: [
        const SizedBox(height: 8),
        _buildStrategyOption(
          context,
          '立即重连',
          '适用于网络波动等临时性问题',
          ReconnectionStrategy.immediate,
          ref,
        ),
        _buildStrategyOption(
          context,
          '指数退避',
          '逐渐增加重连间隔，避免服务器过载',
          ReconnectionStrategy.exponential,
          ref,
        ),
        _buildStrategyOption(
          context,
          '自适应重连',
          '根据历史成功率动态调整策略',
          ReconnectionStrategy.adaptive,
          ref,
        ),
      ],
    );
  }

  /// 构建策略选项
  Widget _buildStrategyOption(
    BuildContext context,
    String title,
    String description,
    ReconnectionStrategy strategy,
    WidgetRef ref,
  ) {
    return ListTile(
      leading: Radio<ReconnectionStrategy>(
        value: strategy,
        groupValue: ReconnectionStrategy.exponential, // 默认选中
        onChanged: (ReconnectionStrategy? value) {
          // TODO: 实现策略选择逻辑
        },
      ),
      title: Text(title),
      subtitle: Text(description),
    );
  }

  /// 开始重连
  void _startReconnection(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(reconnectionProvider.notifier);
    final success = await notifier.startReconnection(exchange, failureType);
    
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            success 
                ? '${exchange.toUpperCase()} 重连成功!' 
                : '${exchange.toUpperCase()} 重连失败，请检查网络连接',
          ),
          backgroundColor: success ? Colors.green : Colors.red,
        ),
      );
    }
  }

  /// 取消重连
  void _cancelReconnection(BuildContext context, WidgetRef ref) {
    ref.read(reconnectionProvider.notifier).cancelReconnection(exchange);
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('重连已取消'),
      ),
    );
  }

  /// 获取失败类型颜色
  Color _getFailureColor(FailureType failureType) {
    switch (failureType) {
      case FailureType.networkTimeout:
        return Colors.orange;
      case FailureType.serverError:
        return Colors.red;
      case FailureType.rateLimit:
        return Colors.purple;
      case FailureType.authentication:
        return Colors.blue;
      case FailureType.serviceMaintenance:
        return Colors.grey;
      case FailureType.unknown:
        return Colors.brown;
    }
  }

  /// 获取失败类型图标
  IconData _getFailureIcon(FailureType failureType) {
    switch (failureType) {
      case FailureType.networkTimeout:
        return Icons.wifi_off;
      case FailureType.serverError:
        return Icons.error;
      case FailureType.rateLimit:
        return Icons.speed;
      case FailureType.authentication:
        return Icons.lock;
      case FailureType.serviceMaintenance:
        return Icons.build;
      case FailureType.unknown:
        return Icons.help;
    }
  }

  /// 获取失败类型名称
  String _getFailureTypeName(FailureType failureType) {
    switch (failureType) {
      case FailureType.networkTimeout:
        return '网络超时';
      case FailureType.serverError:
        return '服务器错误';
      case FailureType.rateLimit:
        return '频率限制';
      case FailureType.authentication:
        return '认证失败';
      case FailureType.serviceMaintenance:
        return '服务维护';
      case FailureType.unknown:
        return '未知错误';
    }
  }

  /// 获取失败类型描述
  String _getFailureDescription(FailureType failureType) {
    switch (failureType) {
      case FailureType.networkTimeout:
        return '网络连接超时，请检查网络状态';
      case FailureType.serverError:
        return '服务器返回错误，请稍后重试';
      case FailureType.rateLimit:
        return '触发频率限制，请等待后重试';
      case FailureType.authentication:
        return '认证信息无效，请检查API配置';
      case FailureType.serviceMaintenance:
        return '交易所正在维护，请稍后再试';
      case FailureType.unknown:
        return '连接出现问题，正在分析原因';
    }
  }

  /// 格式化时间差
  String _formatTimeAgo(DateTime dateTime) {
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

/// 智能重连建议Widget
class SmartReconnectionSuggestion extends ConsumerWidget {
  final String exchange;
  final FailureType failureType;

  const SmartReconnectionSuggestion({
    super.key,
    required this.exchange,
    required this.failureType,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statistics = ref.read(reconnectionManagerProvider).getStatistics(exchange);
    final suggestion = _getReconnectionSuggestion(failureType, statistics);

    return Container(
      margin: const EdgeInsets.all(8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: suggestion.color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: suggestion.color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(
            suggestion.icon,
            color: suggestion.color,
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '智能重连建议',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: suggestion.color,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  suggestion.message,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: suggestion.color,
                  ),
                ),
              ],
            ),
          ),
          ElevatedButton(
            onPressed: () => _applySuggestion(context, ref),
            style: ElevatedButton.styleFrom(
              backgroundColor: suggestion.color,
              foregroundColor: Colors.white,
            ),
            child: const Text('应用'),
          ),
        ],
      ),
    );
  }

  /// 获取重连建议
  _ReconnectionSuggestion _getReconnectionSuggestion(FailureType failureType, ReconnectionStatistics statistics) {
    switch (failureType) {
      case FailureType.networkTimeout:
        if (statistics.successRate > 0.7) {
          return _ReconnectionSuggestion(
            message: '网络状况良好，建议立即重连',
            icon: Icons.wifi,
            color: Colors.green,
          );
        } else {
          return _ReconnectionSuggestion(
            message: '网络不稳定，建议使用指数退避策略',
            icon: Icons.wifi_tethering,
            color: Colors.orange,
          );
        }
      case FailureType.serverError:
        if (statistics.recentAttempts < 3) {
          return _ReconnectionSuggestion(
            message: '服务器错误，建议等待1-2分钟后重试',
            icon: Icons.schedule,
            color: Colors.orange,
          );
        } else {
          return _ReconnectionSuggestion(
            message: '服务器持续错误，建议联系交易所客服',
            icon: Icons.support_agent,
            color: Colors.red,
          );
        }
      case FailureType.rateLimit:
        return _ReconnectionSuggestion(
          message: '触发频率限制，建议等待5-10分钟后重试',
          icon: Icons.timer,
          color: Colors.purple,
        );
      case FailureType.authentication:
        return _ReconnectionSuggestion(
          message: '认证信息无效，请检查API密钥配置',
          icon: Icons.lock,
          color: Colors.blue,
        );
      case FailureType.serviceMaintenance:
        return _ReconnectionSuggestion(
          message: '交易所维护中，建议30分钟后再次检查',
          icon: Icons.build_circle,
          color: Colors.grey,
        );
      case FailureType.unknown:
        if (statistics.successRate < 0.3) {
          return _ReconnectionSuggestion(
            message: '连接问题频繁，建议检查网络设置',
            icon: Icons.network_check,
            color: Colors.red,
          );
        } else {
          return _ReconnectionSuggestion(
            message: '偶发问题，建议使用自适应重连策略',
            icon: Icons.tune,
            color: Colors.orange,
          );
        }
    }
  }

  /// 应用建议
  void _applySuggestion(BuildContext context, WidgetRef ref) {
    // TODO: 实现应用建议逻辑
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('正在应用智能重连建议...'),
      ),
    );
  }
}

/// 重连建议数据类
class _ReconnectionSuggestion {
  final String message;
  final IconData icon;
  final Color color;

  const _ReconnectionSuggestion({
    required this.message,
    required this.icon,
    required this.color,
  });
}