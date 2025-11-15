import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../domain/ai_analysis/model_performance_models.dart';
import '../../../presentation/providers/ai_analysis_provider.dart';
import '../../../presentation/widgets/common/status_indicator.dart';

class AlertNotificationPanel extends ConsumerStatefulWidget {
  const AlertNotificationPanel({super.key});

  @override
  ConsumerState<AlertNotificationPanel> createState() => _AlertNotificationPanelState();
}

class _AlertNotificationPanelState extends ConsumerState<AlertNotificationPanel> {
  Timer? _notificationTimer;
  bool _isExpanded = false;

  @override
  void initState() {
    super.initState();
    // Start monitoring for new alerts
    _startAlertMonitoring();
  }

  @override
  void dispose() {
    _notificationTimer?.cancel();
    super.dispose();
  }

  void _startAlertMonitoring() {
    _notificationTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      if (mounted) {
        // Check for new critical alerts
        ref.read(modelPerformanceProvider.notifier).refreshData();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final modelPerformanceState = ref.watch(modelPerformanceProvider);
    final criticalAlerts = modelPerformanceState.criticalAlerts;
    final unacknowledgedAlerts = modelPerformanceState.unacknowledgedAlerts;

    if (unacknowledgedAlerts.isEmpty) {
      return const SizedBox.shrink();
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
      height: _isExpanded ? null : 80,
      margin: const EdgeInsets.all(16),
      child: Card(
        color: Theme.of(context).colorScheme.errorContainer.withOpacity(0.9),
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        child: InkWell(
          onTap: () => setState(() => _isExpanded = !_isExpanded),
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  children: [
                    Icon(
                      Icons.warning_amber_rounded,
                      color: Theme.of(context).colorScheme.onErrorContainer,
                      size: 24,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '模型性能警报',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: Theme.of(context).colorScheme.onErrorContainer,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.onErrorContainer.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${unacknowledgedAlerts.length}',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onErrorContainer,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Icon(
                      _isExpanded ? Icons.expand_less : Icons.expand_more,
                      color: Theme.of(context).colorScheme.onErrorContainer,
                    ),
                  ],
                ),
                
                // First alert summary (always visible)
                if (unacknowledgedAlerts.isNotEmpty) ..[
                  const SizedBox(height: 8),
                  _buildAlertSummary(unacknowledgedAlerts.first),
                ],
                
                // Expanded content
                if (_isExpanded) ..[
                  const SizedBox(height: 12),
                  _buildExpandedAlertsList(unacknowledgedAlerts),
                  const SizedBox(height: 12),
                  _buildActionButtons(),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAlertSummary(ModelAlert alert) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.onErrorContainer.withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        children: [
          StatusIndicator(
            status: _getStatusFromAlertLevel(alert.level),
            size: 12,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  alert.title,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: Theme.of(context).colorScheme.onErrorContainer,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  alert.message,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onErrorContainer.withOpacity(0.8),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExpandedAlertsList(List<ModelAlert> alerts) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '活跃警报 (${alerts.length})',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w600,
            color: Theme.of(context).colorScheme.onErrorContainer,
          ),
        ),
        const SizedBox(height: 8),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: alerts.length,
          separatorBuilder: (context, index) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final alert = alerts[index];
            return _buildAlertDetailCard(alert);
          },
        ),
      ],
    );
  }

  Widget _buildAlertDetailCard(ModelAlert alert) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withOpacity(0.9),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _getAlertLevelColor(alert.level).withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _getAlertLevelColor(alert.level),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  alert.level.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  alert.title,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            alert.message,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text(
                '模型: ${alert.modelId}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
              ),
              const Spacer(),
              Text(
                _formatTimestamp(alert.timestamp),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              TextButton.icon(
                onPressed: () => _acknowledgeAlert(alert),
                icon: const Icon(Icons.check, size: 16),
                label: const Text('确认'),
                style: TextButton.styleFrom(
                  foregroundColor: Theme.of(context).colorScheme.primary,
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                ),
              ),
              TextButton.icon(
                onPressed: () => _showAlertDetails(alert),
                icon: const Icon(Icons.info, size: 16),
                label: const Text('详情'),
                style: TextButton.styleFrom(
                  foregroundColor: Theme.of(context).colorScheme.secondary,
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: _acknowledgeAllAlerts,
            icon: const Icon(Icons.done_all, size: 16),
            label: const Text('全部确认'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.onErrorContainer,
              side: BorderSide(color: Theme.of(context).colorScheme.onErrorContainer.withOpacity(0.5)),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () {
              // Navigate to alerts page
              // Navigator.of(context).push(...);
            },
            icon: const Icon(Icons.arrow_forward, size: 16),
            label: const Text('查看全部'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.onErrorContainer,
              foregroundColor: Theme.of(context).colorScheme.errorContainer,
            ),
          ),
        ),
      ],
    );
  }

  Status _getStatusFromAlertLevel(String level) {
    switch (level.toLowerCase()) {
      case 'critical':
        return Status.error;
      case 'warning':
        return Status.warning;
      case 'info':
        return Status.healthy;
      default:
        return Status.unknown;
    }
  }

  Color _getAlertLevelColor(String level) {
    switch (level.toLowerCase()) {
      case 'critical':
        return Colors.red;
      case 'warning':
        return Colors.orange;
      case 'info':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);
    
    if (difference.inMinutes < 1) {
      return '刚刚';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}分钟前';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}小时前';
    } else {
      return '${difference.inDays}天前';
    }
  }

  void _acknowledgeAlert(ModelAlert alert) {
    ref.read(modelPerformanceProvider.notifier).acknowledgeAlert(alert.alertId);
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('警报 "${alert.title}" 已确认'),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _acknowledgeAllAlerts() {
    final unacknowledgedAlerts = ref.read(modelPerformanceProvider).unacknowledgedAlerts;
    
    for (final alert in unacknowledgedAlerts) {
      ref.read(modelPerformanceProvider.notifier).acknowledgeAlert(alert.alertId);
    }
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('所有警报已确认'),
        backgroundColor: Colors.green,
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _showAlertDetails(ModelAlert alert) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(
              _getAlertIcon(alert.level),
              color: _getAlertLevelColor(alert.level),
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(alert.title)),
          ],
        ),
        content: SizedBox(
          width: double.maxFinite,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '警报详情',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 16),
              _buildDetailRow('级别', _getAlertLevelText(alert.level)),
              _buildDetailRow('模型', alert.modelId),
              _buildDetailRow('指标', alert.metricName),
              _buildDetailRow('当前值', alert.currentValue.toString()),
              _buildDetailRow('阈值', alert.thresholdValue.toString()),
              _buildDetailRow('时间', _formatTimestamp(alert.timestamp)),
              const SizedBox(height: 16),
              Text(
                '描述',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(alert.message),
              if (alert.metadata.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  '元数据',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                ...alert.metadata.entries.map((entry) => 
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text('${entry.key}: ${entry.value}'),
                  )
                ).toList(),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
          if (!alert.acknowledged)
            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pop();
                _acknowledgeAlert(alert);
              },
              child: const Text('确认警报'),
            ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              '$label:',
              style: TextStyle(
                fontWeight: FontWeight.w500,
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  String _getAlertLevelText(String level) {
    switch (level.toLowerCase()) {
      case 'critical':
        return '严重';
      case 'warning':
        return '警告';
      case 'info':
        return '信息';
      default:
        return level;
    }
  }

  IconData _getAlertIcon(String level) {
    switch (level.toLowerCase()) {
      case 'critical':
        return Icons.error;
      case 'warning':
        return Icons.warning;
      case 'info':
        return Icons.info;
      default:
        return Icons.notifications;
    }
  }
}