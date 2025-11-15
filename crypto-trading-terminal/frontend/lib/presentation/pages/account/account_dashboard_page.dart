"""
账户仪表板页面
显示用户所有账户的总览信息，包括余额、持仓、盈亏统计等
"""

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../../src/presentation/widgets/common/chart_card.dart';
import '../../../src/presentation/widgets/common/loading_indicator.dart';
import '../../../src/presentation/widgets/common/error_display.dart';
import '../../../src/presentation/widgets/account/balance_card.dart';
import '../../../src/presentation/widgets/account/position_card.dart';
import '../../../src/presentation/widgets/account/pnl_chart_card.dart';
import '../../../src/presentation/widgets/account/performance_metrics_card.dart';
import '../../../src/presentation/widgets/account/risk_indicator_card.dart';
import '../../../src/presentation/providers/account/account_provider.dart';
import '../../../src/presentation/providers/market/market_data_provider.dart';
import '../../../src/presentation/providers/settings/theme_provider.dart';

class AccountDashboardPage extends ConsumerStatefulWidget {
  const AccountDashboardPage({Key? key}) : super(key: key);

  @override
  ConsumerState<AccountDashboardPage> createState() => _AccountDashboardPageState();
}

class _AccountDashboardPageState extends ConsumerState<AccountDashboardPage>
    with TickerProviderStateMixin {
  late TabController _tabController;
  late AnimationController _refreshAnimationController;
  late Animation<double> _refreshAnimation;
  
  // 刷新控制
  bool _isAutoRefresh = true;
  Duration _refreshInterval = const Duration(seconds: 30);
  
  // 图表控制
  bool _showPnLChart = true;
  bool _showPositionChart = true;
  
  // 筛选控制
  String _selectedExchange = 'ALL';
  String _selectedAccountType = 'ALL';
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    
    // 初始化刷新动画
    _refreshAnimationController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    _refreshAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _refreshAnimationController,
      curve: Curves.easeInOut,
    ));
    
    // 启动数据获取
    _loadAccountData();
    
    // 自动刷新
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _refreshAnimationController.dispose();
    super.dispose();
  }

  void _startAutoRefresh() {
    Future.delayed(Duration.zero, () async {
      while (_isAutoRefresh) {
        await Future.delayed(_refreshInterval);
        if (mounted && _isAutoRefresh) {
          await _loadAccountData();
          _refreshAnimationController.forward(from: 0);
        }
      }
    });
  }

  Future<void> _loadAccountData() async {
    try {
      final accountProvider = ref.read(accountProviderProvider.notifier);
      await accountProvider.refreshAccountData();
    } catch (e) {
      debugPrint('加载账户数据失败: $e');
    }
  }

  Future<void> _forceRefresh() async {
    setState(() {});
    await _loadAccountData();
    _refreshAnimationController.forward(from: 0);
  }

  @override
  Widget build(BuildContext context) {
    final theme = ref.watch(themeProvider);
    final accountState = ref.watch(accountProviderProvider);
    final marketDataState = ref.watch(marketDataProviderProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('账户总览'),
        elevation: 0,
        backgroundColor: theme.surface,
        foregroundColor: theme.onSurface,
        actions: [
          // 刷新按钮
          IconButton(
            icon: AnimatedBuilder(
              animation: _refreshAnimation,
              builder: (context, child) {
                return Transform.rotate(
                  angle: _refreshAnimation.value * 2 * 3.14159,
                  child: const Icon(Icons.refresh),
                );
              },
            ),
            onPressed: _forceRefresh,
            tooltip: '手动刷新',
          ),
          
          // 设置菜单
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            onSelected: (value) => _handleMenuAction(value),
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'auto_refresh',
                child: Row(
                  children: [
                    Icon(
                      _isAutoRefresh ? Icons.pause : Icons.play_arrow,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(_isAutoRefresh ? '暂停自动刷新' : '开启自动刷新'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'settings',
                child: Row(
                  children: [
                    const Icon(Icons.settings, size: 20),
                    const SizedBox(width: 8),
                    const Text('设置'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'export',
                child: Row(
                  children: [
                    const Icon(Icons.download, size: 20),
                    const SizedBox(width: 8),
                    const Text('导出数据'),
                  ],
                ),
              ),
            ],
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: theme.primary,
          labelColor: theme.primary,
          unselectedLabelColor: theme.onSurface.withOpacity(0.6),
          tabs: const [
            Tab(text: '总览', icon: Icon(Icons.dashboard)),
            Tab(text: '持仓', icon: Icon(Icons.account_balance_wallet)),
            Tab(text: '分析', icon: Icon(Icons.analytics)),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildOverviewTab(accountState, theme, marketDataState),
          _buildPositionsTab(accountState, theme),
          _buildAnalyticsTab(accountState, theme),
        ],
      ),
      floatingActionButton: _buildFloatingActionButton(theme),
    );
  }

  Widget _buildOverviewTab(AccountState accountState, ThemeData theme, MarketDataState marketDataState) {
    if (accountState.isLoading) {
      return const LoadingIndicator(message: '加载账户数据...');
    }

    if (accountState.hasError) {
      return ErrorDisplay(
        message: accountState.errorMessage ?? '加载账户数据失败',
        onRetry: _forceRefresh,
      );
    }

    return RefreshIndicator(
      onRefresh: _forceRefresh,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 账户概览卡片
            _buildAccountOverviewCard(accountState, theme),
            
            const SizedBox(height: 16),
            
            // 今日盈亏统计
            _buildTodayPnLCard(accountState, theme),
            
            const SizedBox(height: 16),
            
            // 各交易所余额
            _buildExchangeBalances(accountState, theme),
            
            const SizedBox(height: 16),
            
            // 快速统计
            _buildQuickStats(accountState, theme),
            
            const SizedBox(height: 24),
            
            // PnL趋势图表
            if (_showPnLChart)
              PnLChartCard(
                data: accountState.pnlHistory,
                height: 200,
              ),
            
            const SizedBox(height: 16),
            
            // 风险指标
            RiskIndicatorCard(
              riskMetrics: accountState.riskMetrics,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPositionsTab(AccountState accountState, ThemeData theme) {
    return Column(
      children: [
        // 筛选栏
        _buildFilterBar(theme),
        
        // 持仓列表
        Expanded(
          child: accountState.positions.isEmpty 
            ? const Center(
                child: Text('暂无持仓数据'),
              )
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: accountState.positions.length,
                itemBuilder: (context, index) {
                  final position = accountState.positions[index];
                  return PositionCard(
                    position: position,
                    onTap: () => _showPositionDetails(position),
                  );
                },
              ),
        ),
      ],
    );
  }

  Widget _buildAnalyticsTab(AccountState accountState, ThemeData theme) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 性能指标卡片
          PerformanceMetricsCard(
            metrics: accountState.performanceMetrics,
          ),
          
          const SizedBox(height: 16),
          
          // 收益分布图
          _buildReturnDistributionChart(accountState, theme),
          
          const SizedBox(height: 16),
          
          // 持仓分布图
          _buildPositionDistributionChart(accountState, theme),
          
          const SizedBox(height: 16),
          
          // 风险分析
          _buildRiskAnalysisCard(accountState, theme),
        ],
      ),
    );
  }

  Widget _buildAccountOverviewCard(AccountState accountState, ThemeData theme) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '总资产',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: theme.onSurface.withOpacity(0.7),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.visibility_off),
                  onPressed: () => ref.read(accountProviderProvider.notifier).toggleVisibility(),
                  tooltip: '隐藏/显示金额',
                ),
              ],
            ),
            
            const SizedBox(height: 8),
            
            Text(
              NumberFormat.currency(
                symbol: '¥',
                decimalDigits: 2,
              ).format(accountState.totalBalance),
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: theme.primary,
              ),
            ),
            
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '今日盈亏',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      Text(
                        NumberFormat.currency(
                          symbol: '¥',
                          decimalDigits: 2,
                        ).format(accountState.todayPnL),
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: accountState.todayPnL >= 0 
                            ? Colors.green 
                            : Colors.red,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                
                Container(
                  height: 40,
                  width: 1,
                  color: theme.dividerColor,
                ),
                
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '总盈亏',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      Text(
                        NumberFormat.currency(
                          symbol: '¥',
                          decimalDigits: 2,
                        ).format(accountState.totalPnL),
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: accountState.totalPnL >= 0 
                            ? Colors.green 
                            : Colors.red,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTodayPnLCard(AccountState accountState, ThemeData theme) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: (accountState.todayPnL >= 0 ? Colors.green : Colors.red).withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                accountState.todayPnL >= 0 ? Icons.trending_up : Icons.trending_down,
                color: accountState.todayPnL >= 0 ? Colors.green : Colors.red,
              ),
            ),
            
            const SizedBox(width: 16),
            
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '今日盈亏',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.onSurface.withOpacity(0.7),
                    ),
                  ),
                  Text(
                    NumberFormat.currency(
                      symbol: '¥',
                      decimalDigits: 2,
                    ).format(accountState.todayPnL),
                    style: theme.textTheme.titleLarge?.copyWith(
                      color: accountState.todayPnL >= 0 ? Colors.green : Colors.red,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            
            Text(
              '${accountState.todayPnLPercentage >= 0 ? '+' : ''}${accountState.todayPnLPercentage.toStringAsFixed(2)}%',
              style: theme.textTheme.titleMedium?.copyWith(
                color: accountState.todayPnL >= 0 ? Colors.green : Colors.red,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExchangeBalances(AccountState accountState, ThemeData theme) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '交易所余额',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            
            const SizedBox(height: 12),
            
            ...accountState.accounts.map((account) => BalanceCard(account: account)),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickStats(AccountState accountState, ThemeData theme) {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            theme,
            '持仓数量',
            accountState.positions.length.toString(),
            Icons.account_balance_wallet,
            Colors.blue,
          ),
        ),
        
        const SizedBox(width: 8),
        
        Expanded(
          child: _buildStatCard(
            theme,
            '胜率',
            '${accountState.winRate.toStringAsFixed(1)}%',
            Icons.emoji_events,
            Colors.orange,
          ),
        ),
        
        const SizedBox(width: 8),
        
        Expanded(
          child: _buildStatCard(
            theme,
            '收益率',
            '${accountState.totalReturnRate.toStringAsFixed(1)}%',
            Icons.trending_up,
            Colors.green,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard(ThemeData theme, String title, String value, IconData icon, Color color) {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(
              value,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(
              title,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.onSurface.withOpacity(0.6),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterBar(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              value: _selectedExchange,
              decoration: const InputDecoration(
                labelText: '交易所',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: const [
                DropdownMenuItem(value: 'ALL', child: Text('全部交易所')),
                DropdownMenuItem(value: 'binance', child: Text('币安')),
                DropdownMenuItem(value: 'okx', child: Text('OKX')),
              ],
              onChanged: (value) {
                setState(() {
                  _selectedExchange = value!;
                });
              },
            ),
          ),
          
          const SizedBox(width: 12),
          
          Expanded(
            child: DropdownButtonFormField<String>(
              value: _selectedAccountType,
              decoration: const InputDecoration(
                labelText: '账户类型',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: const [
                DropdownMenuItem(value: 'ALL', child: Text('全部类型')),
                DropdownMenuItem(value: 'spot', child: Text('现货')),
                DropdownMenuItem(value: 'futures', child: Text('合约')),
              ],
              onChanged: (value) {
                setState(() {
                  _selectedAccountType = value!;
                });
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReturnDistributionChart(AccountState accountState, ThemeData theme) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '收益分布',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            
            const SizedBox(height: 16),
            
            SizedBox(
              height: 200,
              child: PieChart(
                PieChartData(
                  sections: [
                    PieChartSectionData(
                      value: 65,
                      color: Colors.green,
                      title: '盈利 65%',
                      radius: 60,
                    ),
                    PieChartSectionData(
                      value: 25,
                      color: Colors.red,
                      title: '亏损 25%',
                      radius: 60,
                    ),
                    PieChartSectionData(
                      value: 10,
                      color: Colors.grey,
                      title: '持平 10%',
                      radius: 60,
                    ),
                  ],
                  centerSpaceRadius: 30,
                  sectionsSpace: 2,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPositionDistributionChart(AccountState accountState, ThemeData theme) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '持仓分布',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            
            const SizedBox(height: 16),
            
            SizedBox(
              height: 150,
              child: BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceAround,
                  maxY: 100,
                  barTouchData: BarTouchData(enabled: false),
                  titlesData: FlTitlesData(
                    show: true,
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 30,
                        getTitlesWidget: (value, meta) {
                          const symbols = ['BTC', 'ETH', 'ADA', 'DOT', 'LINK'];
                          return SideTitleWidget(
                            axisSide: meta.axisSide,
                            child: Text(
                              symbols[value.toInt() % symbols.length],
                              style: const TextStyle(fontSize: 12),
                            ),
                          );
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: false,
                      ),
                    ),
                    topTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: false,
                      ),
                    ),
                    rightTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: false,
                      ),
                    ),
                  ),
                  borderData: FlBorderData(
                    show: false,
                  ),
                  barGroups: List.generate(5, (index) {
                    return BarChartGroupData(
                      x: index,
                      barRods: [
                        BarChartRodData(
                          toY: 20 + (index * 15).toDouble(),
                          color: Colors.blue,
                          width: 16,
                        ),
                      ],
                    );
                  }),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRiskAnalysisCard(AccountState accountState, ThemeData theme) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '风险分析',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            
            const SizedBox(height: 16),
            
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildRiskStat(
                  theme,
                  '风险等级',
                  accountState.riskMetrics.riskLevel,
                  _getRiskColor(accountState.riskMetrics.riskLevel),
                ),
                
                _buildRiskStat(
                  theme,
                  '最大回撤',
                  '${accountState.riskMetrics.maxDrawdown.toStringAsFixed(2)}%',
                  Colors.red,
                ),
                
                _buildRiskStat(
                  theme,
                  '夏普比率',
                  accountState.riskMetrics.sharpeRatio.toStringAsFixed(2),
                  Colors.blue,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRiskStat(ThemeData theme, String title, String value, Color color) {
    return Column(
      children: [
        Text(
          title,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.onSurface.withOpacity(0.6),
          ),
        ),
        
        const SizedBox(height: 4),
        
        Text(
          value,
          style: theme.textTheme.titleMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Color _getRiskColor(String riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'low':
        return Colors.green;
      case 'medium':
        return Colors.orange;
      case 'high':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Widget _buildFloatingActionButton(ThemeData theme) {
    return FloatingActionButton(
      onPressed: _showAddAccountDialog,
      tooltip: '添加账户',
      child: const Icon(Icons.add),
    );
  }

  void _handleMenuAction(String action) {
    switch (action) {
      case 'auto_refresh':
        setState(() {
          _isAutoRefresh = !_isAutoRefresh;
        });
        break;
      case 'settings':
        _showSettingsDialog();
        break;
      case 'export':
        _exportData();
        break;
    }
  }

  void _showAddAccountDialog() {
    // TODO: 实现添加账户对话框
  }

  void _showSettingsDialog() {
    // TODO: 实现设置对话框
  }

  void _exportData() {
    // TODO: 实现数据导出
  }

  void _showPositionDetails(dynamic position) {
    // TODO: 实现持仓详情页面
  }
}