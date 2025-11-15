import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../providers/risk_control/risk_control_provider.dart';
import '../../providers/auto_order/auto_order_provider.dart';
import '../../widgets/common/custom_card.dart';
import '../../widgets/common/loading_overlay.dart';
import '../../widgets/common/error_message.dart';
import '../../widgets/risk_control/risk_overview_widget.dart';
import '../../widgets/risk_control/position_risk_widget.dart';
import '../../widgets/risk_control/alert_management_widget.dart';
import '../../widgets/risk_control/risk_config_widget.dart';

/// 风险控制仪表板页面
class RiskControlDashboard extends ConsumerStatefulWidget {
  const RiskControlDashboard({super.key});

  @override
  ConsumerState<RiskControlDashboard> createState() => _RiskControlDashboardState();
}

class _RiskControlDashboardState extends ConsumerState<RiskControlDashboard>
    with TickerProviderStateMixin {
  late TabController _tabController;
  int _currentUserId = 1; // TODO: 从认证系统获取当前用户ID
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    
    // 加载初始数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadDashboardData();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final riskState = ref.watch(riskControlProvider(_currentUserId));
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('风险控制仪表板'),
        elevation: 0,
        backgroundColor: theme.colorScheme.surface,
        foregroundColor: theme.colorScheme.onSurface,
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: const [
            Tab(icon: Icon(Icons.dashboard), text: '概览'),
            Tab(icon: Icon(Icons.account_balance_wallet), text: '仓位风险'),
            Tab(icon: Icon(Icons.warning), text: '风险警告'),
            Tab(icon: Icon(Icons.settings), text: '风险配置'),
          ],
        ),
        actions: [
          // 紧急停止按钮
          _buildEmergencyStopButton(theme),
          
          // 刷新按钮
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshDashboard,
            tooltip: '刷新数据',
          ),
          
          // 帮助按钮
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: _showHelpDialog,
            tooltip: '帮助',
          ),
        ],
      ),
      
      body: LoadingOverlay(
        isLoading: riskState.isLoading,
        child: riskState.error != null
            ? ErrorMessage(
                message: riskState.error!,
                onRetry: _refreshDashboard,
              )
            : Column(
                children: [
                  // 快速风险状态指示器
                  _buildRiskStatusIndicator(theme, riskState),
                  
                  // 标签页内容
                  Expanded(
                    child: TabBarView(
                      controller: _tabController,
                      children: [
                        // 概览标签页
                        _buildOverviewTab(theme, riskState),
                        
                        // 仓位风险标签页
                        _buildPositionsTab(theme, riskState),
                        
                        // 风险警告标签页
                        _buildAlertsTab(theme, riskState),
                        
                        // 风险配置标签页
                        _buildConfigTab(theme, riskState),
                      ],
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  /// 构建紧急停止按钮
  Widget _buildEmergencyStopButton(ThemeData theme) {
    return PopupMenuButton<String>(
      icon: Icon(
        Icons.emergency,
        color: theme.colorScheme.error,
      ),
      tooltip: '紧急停止',
      onSelected: _handleEmergencyStop,
      itemBuilder: (context) => [
        const PopupMenuItem(
          value: 'all_accounts',
          child: Row(
            children: [
              Icon(Icons.emergency, color: Colors.red),
              SizedBox(width: 8),
              Text('停止所有账户'),
            ],
          ),
        ),
        const PopupMenuItem(
          value: 'current_account',
          child: Row(
            children: [
              Icon(Icons.emergency, color: Colors.orange),
              SizedBox(width: 8),
              Text('停止当前账户'),
            ],
          ),
        ),
      ],
    );
  }

  /// 构建风险状态指示器
  Widget _buildRiskStatusIndicator(ThemeData theme, RiskControlState riskState) {
    final riskLevel = riskState.dashboardData?.summary.overallRiskLevel ?? 'UNKNOWN';
    Color riskColor;
    IconData riskIcon;
    
    switch (riskLevel) {
      case 'LOW':
        riskColor = Colors.green;
        riskIcon = Icons.check_circle;
        break;
      case 'MEDIUM':
        riskColor = Colors.orange;
        riskIcon = Icons.warning;
        break;
      case 'HIGH':
        riskColor = Colors.red;
        riskIcon = Icons.error;
        break;
      case 'CRITICAL':
        riskColor = Colors.red.shade700;
        riskIcon = Icons.emergency;
        break;
      default:
        riskColor = Colors.grey;
        riskIcon = Icons.help;
        break;
    }

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: riskColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: riskColor,
          width: 2,
        ),
      ),
      child: Row(
        children: [
          Icon(
            riskIcon,
            color: riskColor,
            size: 32,
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '当前风险等级: ${_getRiskLevelText(riskLevel)}',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: riskColor,
                  ),
                ),
                const SizedBox(height: 4),
                if (riskState.dashboardData != null) ...[
                  Text(
                    '未确认警告: ${riskState.dashboardData!.summary.unacknowledgedAlerts} 个 | '
                    '活跃订单: ${riskState.dashboardData!.summary.activeAutoOrders} 个 | '
                    '总仓位: ${riskState.dashboardData!.summary.totalPositions} 个',
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              ],
            ),
          ),
          if (riskState.lastUpdateTime != null)
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '更新时间',
                  style: theme.textTheme.bodySmall,
                ),
                Text(
                  DateFormat('HH:mm:ss').format(riskState.lastUpdateTime!),
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  /// 构建概览标签页
  Widget _buildOverviewTab(ThemeData theme, RiskControlState riskState) {
    if (riskState.dashboardData == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 风险概览组件
          RiskOverviewWidget(
            dashboardData: riskState.dashboardData!,
          ),
          
          const SizedBox(height: 20),
          
          // 关键指标卡片
          _buildKeyMetricsCards(theme, riskState),
          
          const SizedBox(height: 20),
          
          // 最近风险警告
          _buildRecentAlerts(theme, riskState),
        ],
      ),
    );
  }

  /// 构建仓位风险标签页
  Widget _buildPositionsTab(ThemeData theme, RiskControlState riskState) {
    return PositionRiskWidget(
      positions: riskState.positions,
      onPositionSelected: _showPositionDetail,
    );
  }

  /// 构建风险警告标签页
  Widget _buildAlertsTab(ThemeData theme, RiskControlState riskState) {
    return AlertManagementWidget(
      alerts: riskState.alerts,
      onAlertAcknowledged: _acknowledgeAlert,
    );
  }

  /// 构建风险配置标签页
  Widget _buildConfigTab(ThemeData theme, RiskControlState riskState) {
    return RiskConfigWidget(
      configs: riskState.configs,
      onConfigChanged: _updateRiskConfig,
    );
  }

  /// 构建关键指标卡片
  Widget _buildKeyMetricsCards(ThemeData theme, RiskControlState riskState) {
    final data = riskState.dashboardData!;
    
    return Row(
      children: [
        Expanded(
          child: _buildMetricCard(
            theme,
            '总仓位价值',
            NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(data.summary.totalPositionsValue),
            Icons.account_balance_wallet,
            Colors.blue,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            theme,
            '未实现盈亏',
            NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(data.summary.totalUnrealizedPnl),
            data.summary.totalUnrealizedPnl >= 0 ? Icons.trending_up : Icons.trending_down,
            data.summary.totalUnrealizedPnl >= 0 ? Colors.green : Colors.red,
          ),
        ),
      ],
    );
  }

  /// 构建指标卡片
  Widget _buildMetricCard(
    ThemeData theme,
    String title,
    String value,
    IconData icon,
    Color color,
  ) {
    return CustomCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Icon(icon, color: color, size: 24),
              Text(
                value,
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            title,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
        ],
      ),
    );
  }

  /// 构建最近风险警告
  Widget _buildRecentAlerts(ThemeData theme, RiskControlState riskState) {
    if (riskState.alerts.isEmpty) {
      return CustomCard(
        child: Column(
          children: [
            Icon(
              Icons.check_circle,
              size: 48,
              color: Colors.green,
            ),
            const SizedBox(height: 8),
            Text(
              '暂无风险警告',
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              '系统运行正常',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      );
    }

    final recentAlerts = riskState.alerts.take(3).toList();
    
    return CustomCard(
      title: '最近警告',
      child: Column(
        children: recentAlerts.map((alert) {
          return ListTile(
            leading: CircleAvatar(
              backgroundColor: _getSeverityColor(alert.severity).withOpacity(0.2),
              child: Icon(
                _getSeverityIcon(alert.severity),
                color: _getSeverityColor(alert.severity),
                size: 20,
              ),
            ),
            title: Text(alert.message),
            subtitle: Text(
              DateFormat('MM/dd HH:mm').format(alert.timestamp),
              style: theme.textTheme.bodySmall,
            ),
            trailing: alert.isAcknowledged ? null : Icon(
              Icons.arrow_forward_ios,
              size: 16,
              color: theme.colorScheme.primary,
            ),
            onTap: () => _showAlertDetail(alert),
          );
        }).toList(),
      ),
    );
  }

  /// 获取风险等级文本
  String _getRiskLevelText(String level) {
    switch (level) {
      case 'LOW':
        return '低风险';
      case 'MEDIUM':
        return '中风险';
      case 'HIGH':
        return '高风险';
      case 'CRITICAL':
        return '极高风险';
      default:
        return '未知';
    }
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

  /// 加载仪表板数据
  void _loadDashboardData() async {
    final notifier = ref.read(riskControlProvider(_currentUserId).notifier);
    await notifier.loadDashboardData(_currentUserId);
    await notifier.loadPositions(_currentUserId);
    await notifier.loadAlerts(_currentUserId);
    await notifier.loadMetrics(_currentUserId);
    await notifier.loadConfigs(_currentUserId);
  }

  /// 刷新仪表板数据
  void _refreshDashboard() async {
    await _loadDashboardData();
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('数据已刷新')),
    );
  }

  /// 处理紧急停止
  void _handleEmergencyStop(String action) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认紧急停止'),
        content: Text(
          action == 'all_accounts'
              ? '确定要停止所有账户的所有交易活动吗？此操作无法撤销。'
              : '确定要停止当前账户的所有交易活动吗？此操作无法撤销。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('确认停止'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      final notifier = ref.read(riskControlProvider(_currentUserId).notifier);
      await notifier.emergencyStop(_currentUserId);
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('紧急停止执行成功'),
          backgroundColor: Colors.red,
        ),
      );
      
      // 刷新数据
      await _loadDashboardData();
    }
  }

  /// 显示帮助对话框
  void _showHelpDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('风险控制仪表板帮助'),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('风险控制仪表板为您提供全面的风险监控功能：\n'),
              Text('• 概览：显示整体风险状态和关键指标'),
              Text('• 仓位风险：监控所有仓位的风险状况'),
              Text('• 风险警告：管理和确认风险警告'),
              Text('• 风险配置：设置和管理风险控制参数'),
              Text('\n紧急停止功能将立即停止所有自动交易活动。'),
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

  /// 显示仓位详情
  void _showPositionDetail(String positionId) {
    // TODO: 实现仓位详情对话框
  }

  /// 确认风险警告
  Future<void> _acknowledgeAlert(int alertId) async {
    final notifier = ref.read(riskControlProvider(_currentUserId).notifier);
    await notifier.acknowledgeAlert(_currentUserId, alertId);
  }

  /// 更新风险配置
  Future<void> _updateRiskConfig(Map<String, dynamic> config) async {
    // TODO: 实现风险配置更新
  }

  /// 显示警告详情
  void _showAlertDetail(String alertId) {
    // TODO: 实现警告详情对话框
  }
}
