import 'package:flutter/material.dart';

import '../../../domain/entities/risk_control.dart';
import '../../widgets/common/custom_card.dart';

/// 风险概览组件
class RiskOverviewWidget extends StatelessWidget {
  final RiskDashboardData dashboardData;

  const RiskOverviewWidget({
    super.key,
    required this.dashboardData,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '风险概览',
          style: theme.textTheme.headlineMedium,
        ),
        const SizedBox(height: 16),
        
        // 风险等级卡片
        _buildRiskLevelCard(theme),
        
        const SizedBox(height: 16),
        
        // 风险分布饼图
        _buildRiskDistributionChart(theme),
        
        const SizedBox(height: 16),
        
        // 关键指标
        _buildKeyMetrics(theme),
        
        const SizedBox(height: 16),
        
        // 风险分布统计
        _buildRiskDistributionStats(theme),
      ],
    );
  }

  /// 构建风险等级卡片
  Widget _buildRiskLevelCard(ThemeData theme) {
    final riskLevel = dashboardData.summary.overallRiskLevel;
    Color riskColor;
    String riskText;
    
    switch (riskLevel) {
      case 'LOW':
        riskColor = Colors.green;
        riskText = '低风险';
        break;
      case 'MEDIUM':
        riskColor = Colors.orange;
        riskText = '中风险';
        break;
      case 'HIGH':
        riskColor = Colors.red;
        riskText = '高风险';
        break;
      case 'CRITICAL':
        riskColor = Colors.red.shade700;
        riskText = '极高风险';
        break;
      default:
        riskColor = Colors.grey;
        riskText = '未知风险';
        break;
    }

    return CustomCard(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              riskColor.withOpacity(0.1),
              riskColor.withOpacity(0.05),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: riskColor,
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: riskColor.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                _getRiskLevelIcon(riskLevel),
                color: riskColor,
                size: 32,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '当前风险等级',
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  ),
                  Text(
                    riskText,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: riskColor,
                    ),
                  ),
                ],
              ),
            ),
            _buildRiskTrendIcon(theme),
          ],
        ),
      ),
    );
  }

  /// 构建风险分布图表
  Widget _buildRiskDistributionChart(ThemeData theme) {
    final data = dashboardData.riskDistribution;
    final total = data.lowRisk + data.mediumRisk + data.highRisk + data.criticalRisk;
    
    if (total == 0) {
      return CustomCard(
        title: '风险分布',
        child: const Center(
          child: Text('暂无风险数据'),
        ),
      );
    }
    
    return CustomCard(
      title: '风险分布',
      child: Column(
        children: [
          // 进度条显示
          _buildRiskProgressBar(theme, data, total),
          const SizedBox(height: 16),
          
          // 图例
          Column(
            children: [
              _buildLegendItem('低风险 (${data.lowRisk})', Colors.green, data.lowRisk, total),
              const SizedBox(height: 8),
              _buildLegendItem('中风险 (${data.mediumRisk})', Colors.orange, data.mediumRisk, total),
              const SizedBox(height: 8),
              _buildLegendItem('高风险 (${data.highRisk})', Colors.red.shade600, data.highRisk, total),
              const SizedBox(height: 8),
              _buildLegendItem('极高风险 (${data.criticalRisk})', Colors.red.shade900, data.criticalRisk, total),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建风险进度条
  Widget _buildRiskProgressBar(ThemeData theme, RiskDistribution data, int total) {
    if (total == 0) return const SizedBox.shrink();
    
    final lowPercent = (data.lowRisk / total * 100).toInt();
    final mediumPercent = (data.mediumRisk / total * 100).toInt();
    final highPercent = (data.highRisk / total * 100).toInt();
    final criticalPercent = (data.criticalRisk / total * 100).toInt();
    
    return Container(
      height: 24,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.outline,
          width: 1,
        ),
      ),
      child: Row(
        children: [
          if (data.lowRisk > 0)
            Expanded(
              flex: lowPercent,
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.green,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(12),
                    bottomLeft: Radius.circular(12),
                  ),
                ),
                child: Center(
                  child: Text(
                    lowPercent > 10 ? '$lowPercent%' : '',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
          if (data.mediumRisk > 0)
            Expanded(
              flex: mediumPercent,
              child: Container(
                color: Colors.orange,
                child: Center(
                  child: Text(
                    mediumPercent > 10 ? '$mediumPercent%' : '',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
          if (data.highRisk > 0)
            Expanded(
              flex: highPercent,
              child: Container(
                color: Colors.red.shade600,
                child: Center(
                  child: Text(
                    highPercent > 10 ? '$highPercent%' : '',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
          if (data.criticalRisk > 0)
            Expanded(
              flex: criticalPercent,
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.red.shade900,
                  borderRadius: const BorderRadius.only(
                    topRight: Radius.circular(12),
                    bottomRight: Radius.circular(12),
                  ),
                ),
                child: Center(
                  child: Text(
                    criticalPercent > 10 ? '$criticalPercent%' : '',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  /// 构建图例项
  Widget _buildLegendItem(String label, Color color, int count, int total) {
    final percentage = total > 0 ? (count / total * 100).toInt() : 0;
    
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '$label: ${percentage.toString()}%',
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }

  /// 构建关键指标
  Widget _buildKeyMetrics(ThemeData theme) {
    final performance = dashboardData.performance;
    
    return CustomCard(
      title: '关键指标',
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: _buildMetricItem(
                  theme,
                  '日盈亏',
                  '\$${performance.dailyPnl.toStringAsFixed(2)}',
                  performance.dailyPnl >= 0 ? Icons.trending_up : Icons.trending_down,
                  performance.dailyPnl >= 0 ? Colors.green : Colors.red,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildMetricItem(
                  theme,
                  '胜率',
                  '${performance.winRate.toStringAsFixed(1)}%',
                  Icons.percent,
                  Colors.blue,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildMetricItem(
                  theme,
                  '总交易数',
                  '${performance.totalTrades}',
                  Icons.swap_horiz,
                  Colors.purple,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildMetricItem(
                  theme,
                  '活跃账户',
                  '${dashboardData.summary.totalAccounts}',
                  Icons.account_balance,
                  Colors.indigo,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建指标项
  Widget _buildMetricItem(
    ThemeData theme,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.7),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建风险分布统计
  Widget _buildRiskDistributionStats(ThemeData theme) {
    final summary = dashboardData.summary;
    
    return CustomCard(
      title: '风险监控统计',
      child: Column(
        children: [
          _buildStatRow(
            theme,
            '总仓位数量',
            '${summary.totalPositions}',
            Icons.account_balance_wallet,
            Colors.blue,
          ),
          const Divider(),
          _buildStatRow(
            theme,
            '未确认警告',
            '${summary.unacknowledgedAlerts}',
            Icons.warning,
            summary.unacknowledgedAlerts > 0 ? Colors.orange : Colors.green,
          ),
          const Divider(),
          _buildStatRow(
            theme,
            '活跃自动订单',
            '${summary.activeAutoOrders}',
            Icons.autorenew,
            Colors.green,
          ),
          const Divider(),
          _buildStatRow(
            theme,
            '仓位总价值',
            '\$${summary.totalPositionsValue.toStringAsFixed(2)}',
            Icons.account_balance,
            Colors.purple,
          ),
        ],
      ),
    );
  }

  /// 构建统计行
  Widget _buildStatRow(
    ThemeData theme,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: theme.textTheme.bodyMedium,
            ),
          ),
          Text(
            value,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  /// 获取风险等级图标
  IconData _getRiskLevelIcon(String riskLevel) {
    switch (riskLevel) {
      case 'LOW':
        return Icons.check_circle;
      case 'MEDIUM':
        return Icons.warning;
      case 'HIGH':
        return Icons.error;
      case 'CRITICAL':
        return Icons.emergency;
      default:
        return Icons.help;
    }
  }

  /// 构建风险趋势图标
  Widget _buildRiskTrendIcon(ThemeData theme) {
    // 这里可以根据历史数据计算趋势
    // 简化实现，返回一个向上的箭头
    return Icon(
      Icons.trending_up,
      color: Colors.green,
      size: 24,
    );
  }
}
