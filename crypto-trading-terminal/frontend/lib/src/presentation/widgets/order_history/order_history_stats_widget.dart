import 'package:flutter/material.dart';
import '../../../domain/entities/order_history.dart';

class OrderHistoryStatsWidget extends StatelessWidget {
  final OrderHistoryStats stats;

  const OrderHistoryStatsWidget({
    super.key,
    required this.stats,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 总体统计卡片
          _buildOverallStatsCard(theme),
          const SizedBox(height: 16),
          
          // 执行状态分布
          _buildExecutionStatusDistribution(theme),
          const SizedBox(height: 16),
          
          // 时间统计
          _buildTimeBasedStats(theme),
          const SizedBox(height: 16),
          
          // 热门交易对
          _buildTopSymbolsCard(theme),
          const SizedBox(height: 16),
          
          // 热门交易所
          _buildTopExchangesCard(theme),
        ],
      ),
    );
  }

  Widget _buildOverallStatsCard(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '总体统计',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            // 第一行统计
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '总执行次数',
                    '${stats.totalExecutions}',
                    Icons.play_circle,
                    theme.colorScheme.primary,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '成功率',
                    '${stats.successRate.toStringAsFixed(1)}%',
                    Icons.trending_up,
                    Colors.green,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 第二行统计
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '失败率',
                    '${stats.failureRate.toStringAsFixed(1)}%',
                    Icons.trending_down,
                    Colors.red,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '平均执行时长',
                    '${stats.averageExecutionTime.toStringAsFixed(1)}s',
                    Icons.timer,
                    Colors.orange,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 第三行统计
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '总交易量',
                    '${stats.totalVolume.toStringAsFixed(4)}',
                    Icons.account_balance_wallet,
                    theme.colorScheme.secondary,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '总盈亏',
                    '${stats.totalPnl.toStringAsFixed(4)}',
                    Icons.monetization_on,
                    stats.totalPnl >= 0 ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExecutionStatusDistribution(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '执行状态分布',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            // 状态分布列表
            _buildStatusDistributionItem(
              theme,
              '成功',
              stats.successfulExecutions,
              stats.totalExecutions,
              Colors.green,
            ),
            const SizedBox(height: 8),
            _buildStatusDistributionItem(
              theme,
              '失败',
              stats.failedExecutions,
              stats.totalExecutions,
              Colors.red,
            ),
            const SizedBox(height: 8),
            _buildStatusDistributionItem(
              theme,
              '部分成交',
              stats.partiallyFilledExecutions,
              stats.totalExecutions,
              Colors.orange,
            ),
            const SizedBox(height: 8),
            _buildStatusDistributionItem(
              theme,
              '已取消',
              stats.cancelledExecutions,
              stats.totalExecutions,
              Colors.grey,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeBasedStats(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '时间维度统计',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '今日执行',
                    '${stats.executionsToday}',
                    Icons.today,
                    Colors.blue,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '本周执行',
                    '${stats.executionsThisWeek}',
                    Icons.calendar_view_week,
                    Colors.purple,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    theme,
                    '本月执行',
                    '${stats.executionsThisMonth}',
                    Icons.calendar_month,
                    Colors.indigo,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopSymbolsCard(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '热门交易对',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            if (stats.topSymbols.isEmpty)
              const Text('暂无数据')
            else
              ...stats.topSymbols.asMap().entries.map((entry) {
                final index = entry.key;
                final symbolData = entry.value;
                final symbol = symbolData['symbol'] as String;
                final count = symbolData['count'] as int;
                
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withOpacity(0.2),
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: Text(
                            '${index + 1}',
                            style: theme.textTheme.bodySmall?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              symbol,
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            Text(
                              '$count 次执行',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurface.withOpacity(0.7),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildTopExchangesCard(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '热门交易所',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            if (stats.topExchanges.isEmpty)
              const Text('暂无数据')
            else
              ...stats.topExchanges.asMap().entries.map((entry) {
                final index = entry.key;
                final exchangeData = entry.value;
                final exchange = exchangeData['exchange'] as String;
                final count = exchangeData['count'] as int;
                
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          color: theme.colorScheme.secondary.withOpacity(0.2),
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: Text(
                            '${index + 1}',
                            style: theme.textTheme.bodySmall?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              exchange,
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            Text(
                              '$count 次执行',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurface.withOpacity(0.7),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(ThemeData theme, String label, String value, 
      IconData icon, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              color: color,
              size: 20,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                value,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
      ],
    );
  }

  Widget _buildStatusDistributionItem(ThemeData theme, String label, int count, 
      int total, Color color) {
    final percentage = total > 0 ? (count / total * 100) : 0.0;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: theme.textTheme.bodyMedium,
            ),
            Text(
              '${count}次 (${percentage.toStringAsFixed(1)}%)',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(
          value: percentage / 100,
          backgroundColor: theme.colorScheme.surface,
          valueColor: AlwaysStoppedAnimation<Color>(color),
        ),
      ],
    );
  }
}