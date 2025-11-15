import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../domain/entities/risk_control.dart';
import '../../widgets/common/custom_card.dart';

/// 风险警告管理组件
class AlertManagementWidget extends StatefulWidget {
  final List<RiskAlert> alerts;
  final Function(int)? onAlertAcknowledged;

  const AlertManagementWidget({
    super.key,
    required this.alerts,
    this.onAlertAcknowledged,
  });

  @override
  State<AlertManagementWidget> createState() => _AlertManagementWidgetState();
}

class _AlertManagementWidgetState extends State<AlertManagementWidget> {
  String _filterSeverity = 'all';
  String _filterStatus = 'all';
  String _sortBy = 'timestamp';
  bool _sortDescending = true;

  @override
  Widget build(BuildContext context) {
    final filteredAlerts = _getFilteredAndSortedAlerts();
    final unacknowledgedCount = widget.alerts.where((alert) => !alert.isAcknowledged).length;
    
    return Column(
      children: [
        // 统计信息栏
        _buildStatisticsBar(unacknowledgedCount),
        
        // 过滤和排序栏
        _buildFilterSortBar(),
        
        // 警告列表
        Expanded(
          child: filteredAlerts.isEmpty
              ? const Center(
                  child: Text('暂无风险警告'),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: filteredAlerts.length,
                  itemBuilder: (context, index) {
                    final alert = filteredAlerts[index];
                    return _buildAlertCard(context, alert);
                  },
                ),
        ),
      ],
    );
  }

  /// 构建统计信息栏
  Widget _buildStatisticsBar(int unacknowledgedCount) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.all(16),
      color: theme.colorScheme.surface,
      child: Row(
        children: [
          Expanded(
            child: _buildStatCard(
              theme,
              '总警告数',
              widget.alerts.length.toString(),
              Icons.warning,
              theme.colorScheme.primary,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: _buildStatCard(
              theme,
              '未确认',
              unacknowledgedCount.toString(),
              Icons.notification_important,
              unacknowledgedCount > 0 ? Colors.red : Colors.green,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: _buildStatCard(
              theme,
              '已确认',
              (widget.alerts.length - unacknowledgedCount).toString(),
              Icons.check_circle,
              Colors.green,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: _buildStatCard(
              theme,
              '已解决',
              widget.alerts.where((alert) => alert.isResolved).length.toString(),
              Icons.done_all,
              Colors.blue,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建统计卡片
  Widget _buildStatCard(
    ThemeData theme,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 4),
          Text(
            value,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  /// 构建过滤排序栏
  Widget _buildFilterSortBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Theme.of(context).colorScheme.surface,
      child: Column(
        children: [
          Row(
            children: [
              // 严重性过滤
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filterSeverity,
                  decoration: const InputDecoration(
                    labelText: '严重性',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('全部')),
                    DropdownMenuItem(value: 'INFO', child: Text('信息')),
                    DropdownMenuItem(value: 'WARNING', child: Text('警告')),
                    DropdownMenuItem(value: 'CRITICAL', child: Text('严重')),
                    DropdownMenuItem(value: 'BLOCKED', child: Text('阻断')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _filterSeverity = value!;
                    });
                  },
                ),
              ),
              const SizedBox(width: 16),
              
              // 状态过滤
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filterStatus,
                  decoration: const InputDecoration(
                    labelText: '状态',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('全部状态')),
                    DropdownMenuItem(value: 'unacknowledged', child: Text('未确认')),
                    DropdownMenuItem(value: 'acknowledged', child: Text('已确认')),
                    DropdownMenuItem(value: 'resolved', child: Text('已解决')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _filterStatus = value!;
                    });
                  },
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 12),
          
          Row(
            children: [
              // 排序字段
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _sortBy,
                  decoration: const InputDecoration(
                    labelText: '排序依据',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'timestamp', child: Text('时间')),
                    DropdownMenuItem(value: 'severity', child: Text('严重性')),
                    DropdownMenuItem(value: 'type', child: Text('类型')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _sortBy = value!;
                    });
                  },
                ),
              ),
              
              const SizedBox(width: 16),
              
              // 排序方向
              IconButton(
                onPressed: () {
                  setState(() {
                    _sortDescending = !_sortDescending;
                  });
                },
                icon: Icon(
                  _sortDescending ? Icons.arrow_downward : Icons.arrow_upward,
                  color: Theme.of(context).colorScheme.primary,
                ),
                tooltip: _sortDescending ? '降序' : '升序',
              ),
              
              const SizedBox(width: 8),
              
              // 清除过滤器按钮
              ElevatedButton.icon(
                onPressed: _clearFilters,
                icon: const Icon(Icons.clear, size: 16),
                label: const Text('清除'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 获取过滤和排序后的警告列表
  List<RiskAlert> _getFilteredAndSortedAlerts() {
    var filtered = widget.alerts.where((alert) {
      // 严重性过滤
      if (_filterSeverity != 'all' && alert.severity != _filterSeverity) {
        return false;
      }
      
      // 状态过滤
      switch (_filterStatus) {
        case 'unacknowledged':
          return !alert.isAcknowledged;
        case 'acknowledged':
          return alert.isAcknowledged && !alert.isResolved;
        case 'resolved':
          return alert.isResolved;
        default:
          return true;
      }
    }).toList();

    // 排序
    filtered.sort((a, b) {
      int comparison;
      switch (_sortBy) {
        case 'timestamp':
          comparison = a.timestamp.compareTo(b.timestamp);
          break;
        case 'severity':
          comparison = _getSeverityScore(a.severity).compareTo(_getSeverityScore(b.severity));
          break;
        case 'type':
          comparison = a.alertType.compareTo(b.alertType);
          break;
        default:
          comparison = 0;
      }
      return _sortDescending ? -comparison : comparison;
    });

    return filtered;
  }

  /// 获取严重性分数（用于排序）
  int _getSeverityScore(String severity) {
    switch (severity.toUpperCase()) {
      case 'INFO':
        return 1;
      case 'WARNING':
        return 2;
      case 'CRITICAL':
        return 3;
      case 'BLOCKED':
        return 4;
      default:
        return 0;
    }
  }

  /// 清除过滤器
  void _clearFilters() {
    setState(() {
      _filterSeverity = 'all';
      _filterStatus = 'all';
      _sortBy = 'timestamp';
      _sortDescending = true;
    });
  }

  /// 构建警告卡片
  Widget _buildAlertCard(BuildContext context, RiskAlert alert) {
    final theme = Theme.of(context);
    final severityColor = _getSeverityColor(alert.severity);
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 警告头部信息
            _buildAlertHeader(theme, alert, severityColor),
            
            const SizedBox(height: 12),
            
            // 警告详情
            _buildAlertDetails(theme, alert),
            
            const SizedBox(height: 12),
            
            // 警告操作按钮
            _buildAlertActions(context, theme, alert, severityColor),
          ],
        ),
      ),
    );
  }

  /// 构建警告头部信息
  Widget _buildAlertHeader(ThemeData theme, RiskAlert alert, Color severityColor) {
    return Row(
      children: [
        // 严重性指示器
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: severityColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: severityColor,
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _getSeverityIcon(alert.severity),
                size: 14,
                color: severityColor,
              ),
              const SizedBox(width: 4),
              Text(
                _getSeverityText(alert.severity),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: severityColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        
        const SizedBox(width: 12),
        
        // 警告类型
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: theme.colorScheme.outline,
              width: 1,
            ),
          ),
          child: Text(
            _getAlertTypeText(alert.alertType),
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        
        const Spacer(),
        
        // 交易对
        if (alert.symbol != null)
          Text(
            alert.symbol!,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        
        const SizedBox(width: 16),
        
        // 状态指示器
        if (alert.isAcknowledged)
          Icon(
            Icons.check_circle,
            color: Colors.green,
            size: 20,
          )
        else
          Icon(
            Icons.radio_button_unchecked,
            color: Colors.orange,
            size: 20,
          ),
      ],
    );
  }

  /// 构建警告详情
  Widget _buildAlertDetails(ThemeData theme, RiskAlert alert) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 警告消息
        Text(
          alert.message,
          style: theme.textTheme.bodyLarge,
        ),
        
        const SizedBox(height: 8),
        
        // 数值信息
        if (alert.currentValue != null || alert.limitValue != null)
          Row(
            children: [
              if (alert.currentValue != null)
                Expanded(
                  child: _buildDetailItem(
                    theme,
                    '当前值',
                    alert.currentValue.toString(),
                  ),
                ),
              if (alert.limitValue != null)
                Expanded(
                  child: _buildDetailItem(
                    theme,
                    '限制值',
                    alert.limitValue.toString(),
                  ),
                ),
            ],
          ),
        
        const SizedBox(height: 8),
        
        // 时间信息
        Row(
          children: [
            Expanded(
              child: Text(
                '时间: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(alert.timestamp)}',
                style: theme.textTheme.bodySmall,
              ),
            ),
            if (alert.acknowledgedAt != null)
              Text(
                '确认: ${DateFormat('MM/dd HH:mm').format(alert.acknowledgedAt!)}',
                style: theme.textTheme.bodySmall,
              ),
          ],
        ),
      ],
    );
  }

  /// 构建详细信息项
  Widget _buildDetailItem(ThemeData theme, String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
        Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  /// 构建警告操作按钮
  Widget _buildAlertActions(BuildContext context, ThemeData theme, RiskAlert alert, Color severityColor) {
    return Row(
      children: [
        // 确认按钮
        if (!alert.isAcknowledged)
          ElevatedButton.icon(
            onPressed: () => _acknowledgeAlert(alert.alertId),
            icon: const Icon(Icons.check, size: 16),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
            ),
            label: const Text('确认'),
          ),
        
        if (!alert.isAcknowledged) const SizedBox(width: 8),
        
        // 详情按钮
        OutlinedButton.icon(
          onPressed: () => _showAlertDetail(context, alert),
          icon: const Icon(Icons.info_outline, size: 16),
          label: const Text('详情'),
        ),
        
        const Spacer(),
        
        // 状态标签
        if (alert.isAcknowledged)
          Chip(
            label: const Text('已确认'),
            backgroundColor: Colors.green.withOpacity(0.1),
            labelStyle: const TextStyle(color: Colors.green),
            avatar: const Icon(Icons.check, size: 16, color: Colors.green),
          )
        else
          Chip(
            label: const Text('待确认'),
            backgroundColor: Colors.orange.withOpacity(0.1),
            labelStyle: const TextStyle(color: Colors.orange),
            avatar: const Icon(Icons.warning, size: 16, color: Colors.orange),
          ),
      ],
    );
  }

  /// 确认警告
  void _acknowledgeAlert(int alertId) {
    widget.onAlertAcknowledged?.call(alertId);
  }

  /// 显示警告详情
  void _showAlertDetail(BuildContext context, RiskAlert alert) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('警告详情'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                alert.message,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 16),
              _buildDetailRow('严重性', _getSeverityText(alert.severity)),
              _buildDetailRow('类型', _getAlertTypeText(alert.alertType)),
              if (alert.symbol != null) _buildDetailRow('交易对', alert.symbol!),
              _buildDetailRow('时间', DateFormat('yyyy-MM-dd HH:mm:ss').format(alert.timestamp)),
              if (alert.acknowledgedAt != null)
                _buildDetailRow('确认时间', DateFormat('yyyy-MM-dd HH:mm:ss').format(alert.acknowledgedAt!)),
              if (alert.isResolved && alert.resolvedAt != null)
                _buildDetailRow('解决时间', DateFormat('yyyy-MM-dd HH:mm:ss').format(alert.resolvedAt!)),
              if (alert.currentValue != null)
                _buildDetailRow('当前值', alert.currentValue.toString()),
              if (alert.limitValue != null)
                _buildDetailRow('限制值', alert.limitValue.toString()),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  /// 构建详情行
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
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  /// 获取严重性颜色
  Color _getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'INFO':
        return Colors.blue;
      case 'WARNING':
        return Colors.orange;
      case 'CRITICAL':
        return Colors.red;
      case 'BLOCKED':
        return Colors.red.shade700;
      default:
        return Colors.grey;
    }
  }

  /// 获取严重性图标
  IconData _getSeverityIcon(String severity) {
    switch (severity.toUpperCase()) {
      case 'INFO':
        return Icons.info;
      case 'WARNING':
        return Icons.warning;
      case 'CRITICAL':
        return Icons.error;
      case 'BLOCKED':
        return Icons.block;
      default:
        return Icons.help;
    }
  }

  /// 获取严重性文本
  String _getSeverityText(String severity) {
    switch (severity.toUpperCase()) {
      case 'INFO':
        return '信息';
      case 'WARNING':
        return '警告';
      case 'CRITICAL':
        return '严重';
      case 'BLOCKED':
        return '阻断';
      default:
        return '未知';
    }
  }

  /// 获取警告类型文本
  String _getAlertTypeText(String alertType) {
    switch (alertType) {
      case 'order_size':
        return '订单大小';
      case 'position_size':
        return '仓位大小';
      case 'daily_limit':
        return '日限制';
      case 'emergency_stop':
        return '紧急停止';
      default:
        return alertType;
    }
  }
}
