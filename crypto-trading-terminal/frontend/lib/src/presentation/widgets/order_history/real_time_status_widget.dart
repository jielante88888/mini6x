import 'package:flutter/material.dart';
import 'dart:async';
import '../../../domain/entities/order_history.dart';

class RealTimeStatusWidget extends StatefulWidget {
  final List<RealTimeExecutionStatus> realTimeStatus;
  final Function(RealTimeExecutionStatus)? onStatusTap;

  const RealTimeStatusWidget({
    super.key,
    required this.realTimeStatus,
    this.onStatusTap,
  });

  @override
  State<RealTimeStatusWidget> createState() => _RealTimeStatusWidgetState();
}

class _RealTimeStatusWidgetState extends State<RealTimeStatusWidget> {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _startRefreshTimer();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startRefreshTimer() {
    // 每5秒刷新一次数据
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      // 这里可以添加实际的数据刷新逻辑
      // 目前只是触发重新构建UI
      if (mounted) {
        setState(() {});
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (widget.realTimeStatus.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.speed,
              size: 64,
              color: Colors.grey,
            ),
            SizedBox(height: 16),
            Text(
              '暂无实时执行状态',
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey,
              ),
            ),
            SizedBox(height: 8),
            Text(
              '没有正在执行的订单',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        // 这里可以添加刷新逻辑
        await Future.delayed(const Duration(seconds: 1));
      },
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: widget.realTimeStatus.length,
        itemBuilder: (context, index) {
          final status = widget.realTimeStatus[index];
          return RealTimeStatusCard(
            status: status,
            onTap: widget.onStatusTap != null ? () => widget.onStatusTap!(status) : null,
          );
        },
      ),
    );
  }
}

class RealTimeStatusCard extends StatelessWidget {
  final RealTimeExecutionStatus status;
  final VoidCallback? onTap;

  const RealTimeStatusCard({
    super.key,
    required this.status,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 第一行：订单ID、状态和进度
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '订单 ${status.orderId}',
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '历史ID: ${status.orderHistoryId}',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withOpacity(0.7),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: _getStatusColor(status.currentStatus),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildStatusIcon(status.currentStatus),
                        const SizedBox(width: 6),
                        Text(
                          status.currentStatus.displayName,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // 执行进度条
              LinearProgressIndicator(
                value: status.progressPercentage / 100,
                backgroundColor: theme.colorScheme.surface,
                valueColor: AlwaysStoppedAnimation<Color>(
                  _getStatusColor(status.currentStatus),
                ),
                minHeight: 8,
              ),
              const SizedBox(height: 8),
              
              // 进度百分比
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '执行进度',
                    style: theme.textTheme.bodyMedium,
                  ),
                  Text(
                    '${status.progressPercentage.toStringAsFixed(1)}%',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: _getStatusColor(status.currentStatus),
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // 第二行：时间信息和预计完成时间
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '最后更新:',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withOpacity(0.7),
                          ),
                        ),
                        Text(
                          _formatTime(status.lastUpdateTime),
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  if (status.estimatedCompletionTime != null) ...[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            '预计完成:',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurface.withOpacity(0.7),
                            ),
                          ),
                          Text(
                            _formatTime(status.estimatedCompletionTime!),
                            style: theme.textTheme.bodySmall?.copyWith(
                              fontWeight: FontWeight.w500,
                              color: Colors.blue,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
              
              // 错误信息
              if (status.errorInfo != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    border: Border.all(color: Colors.red.shade200),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.error_outline,
                        color: Colors.red.shade600,
                        size: 16,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          status.errorInfo!,
                          style: TextStyle(
                            color: Colors.red.shade700,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              
              // 重试信息
              if (status.retryInfo != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    border: Border.all(color: Colors.orange.shade200),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.refresh,
                            color: Colors.orange.shade600,
                            size: 16,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '重试信息',
                            style: TextStyle(
                              color: Colors.orange.shade700,
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '当前重试: ${status.retryInfo!['current_retry']}/${status.retryInfo!['max_retries']}',
                        style: TextStyle(
                          color: Colors.orange.shade700,
                          fontSize: 12,
                        ),
                      ),
                      if (status.retryInfo!['can_retry'] == true)
                        Text(
                          '可以重试',
                          style: TextStyle(
                            color: Colors.orange.shade600,
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
              
              // 实时指示器
              const SizedBox(height: 12),
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: Colors.green,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '实时监控',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.green,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    Icons.wifi,
                    size: 16,
                    color: Colors.green,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);
    
    if (difference.inMinutes < 1) {
      return '刚刚';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}分钟前';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}小时前';
    } else {
      return '${difference.inDays}天前';
    }
  }

  Color _getStatusColor(ExecutionStatus status) {
    switch (status) {
      case ExecutionStatus.success:
        return Colors.green;
      case ExecutionStatus.failed:
        return Colors.red;
      case ExecutionStatus.executing:
      case ExecutionStatus.retrying:
        return Colors.blue;
      case ExecutionStatus.partialFilled:
        return Colors.orange;
      case ExecutionStatus.cancelled:
        return Colors.grey;
      case ExecutionStatus.pending:
        return Colors.blueGrey;
      case ExecutionStatus.timeout:
        return Colors.pink;
      default:
        return Colors.grey;
    }
  }

  Widget _buildStatusIcon(ExecutionStatus status) {
    IconData icon;
    Color color;
    
    switch (status) {
      case ExecutionStatus.success:
        icon = Icons.check;
        color = Colors.white;
        break;
      case ExecutionStatus.failed:
        icon = Icons.close;
        color = Colors.white;
        break;
      case ExecutionStatus.executing:
        icon = Icons.play_arrow;
        color = Colors.white;
        break;
      case ExecutionStatus.retrying:
        icon = Icons.refresh;
        color = Colors.white;
        break;
      case ExecutionStatus.partialFilled:
        icon = Icons.warning;
        color = Colors.white;
        break;
      case ExecutionStatus.cancelled:
        icon = Icons.stop;
        color = Colors.white;
        break;
      case ExecutionStatus.pending:
        icon = Icons.pause;
        color = Colors.white;
        break;
      case ExecutionStatus.timeout:
        icon = Icons.access_time;
        color = Colors.white;
        break;
      default:
        icon = Icons.help;
        color = Colors.white;
    }
    
    return Icon(
      icon,
      size: 12,
      color: color,
    );
  }
}