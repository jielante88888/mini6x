import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../providers/futures_market_provider.dart';
import '../../widgets/common/market_card.dart';

/// 期货市场页面
class FuturesMarketPage extends ConsumerStatefulWidget {
  const FuturesMarketPage({super.key});

  @override
  ConsumerState<FuturesMarketPage> createState() => _FuturesMarketPageState();
}

class _FuturesMarketPageState extends ConsumerState<FuturesMarketPage> {
  @override
  void initState() {
    super.initState();
    
    // 页面初始化时获取市场数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(futuresMarketProvider.notifier).fetchMarketData();
      ref.read(futuresMarketProvider.notifier).enableRealtimeData();
      ref.read(futuresMarketProvider.notifier).startAutoRefresh();
    });
  }

  @override
  void dispose() {
    super.dispose();
    ref.read(futuresMarketProvider.notifier).dispose();
  }

  @override
  Widget build(BuildContext context) {
    final futuresMarketDataState = ref.watch(futuresMarketProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('期货市场'),
        elevation: 0,
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        actions: [
          _buildConnectionStatusIndicator(futuresMarketDataState),
          const SizedBox(width: 8),
          _buildFundingRateFilter(),
          const SizedBox(width: 8),
          _buildOpenInterestFilter(),
          const SizedBox(width: 8),
          _buildExchangeSelector(futuresMarketDataState),
          const SizedBox(width: 16),
        ],
      ),
      body: Column(
        children: [
          _buildFuturesStatusCard(futuresMarketDataState),
          _buildFuturesQuickStats(futuresMarketDataState),
          _buildFundingRateSummary(futuresMarketDataState),
          Expanded(
            child: _buildFuturesMarketDataTable(futuresMarketDataState),
          ),
        ],
      ),
      floatingActionButton: _buildFloatingActionButtons(futuresMarketDataState),
    );
  }

  /// 构建连接状态指示器
  Widget _buildConnectionStatusIndicator(FuturesMarketDataState state) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _parseColor(state.getConnectionStatusColor()),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            state.getConnectionStatusDescription(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建资金费率筛选器
  Widget _buildFundingRateFilter() {
    return PopupMenuButton<String>(
      icon: Icon(Icons.percent_outlined),
      tooltip: '资金费率筛选',
      onSelected: (String filter) {
        // TODO: 实现资金费率筛选逻辑
      },
      itemBuilder: (BuildContext context) => [
        PopupMenuItem(
          value: 'all',
          child: Row(
            children: [
              Icon(Icons.list_alt_outlined, size: 18),
              const SizedBox(width: 8),
              Text('全部'),
            ],
          ),
        ),
        PopupMenuItem(
          value: 'positive',
          child: Row(
            children: [
              Icon(Icons.trending_up, size: 18, color: Colors.green),
              const SizedBox(width: 8),
              Text('正向费率'),
            ],
          ),
        ),
        PopupMenuItem(
          value: 'negative',
          child: Row(
            children: [
              Icon(Icons.trending_down, size: 18, color: Colors.red),
              const SizedBox(width: 8),
              Text('负向费率'),
            ],
          ),
        ),
      ],
    );
  }

  /// 构建持仓量筛选器
  Widget _buildOpenInterestFilter() {
    return PopupMenuButton<String>(
      icon: Icon(Icons.account_balance_wallet_outlined),
      tooltip: '持仓量筛选',
      onSelected: (String filter) {
        // TODO: 实现持仓量筛选逻辑
      },
      itemBuilder: (BuildContext context) => [
        PopupMenuItem(
          value: 'all',
          child: Row(
            children: [
              Icon(Icons.list_alt_outlined, size: 18),
              const SizedBox(width: 8),
              Text('全部'),
            ],
          ),
        ),
        PopupMenuItem(
          value: 'high',
          child: Row(
            children: [
              Icon(Icons.show_chart, size: 18, color: Colors.blue),
              const SizedBox(width: 8),
              Text('高持仓量'),
            ],
          ),
        ),
        PopupMenuItem(
          value: 'low',
          child: Row(
            children: [
              Icon(Icons.trending_down, size: 18, color: Colors.orange),
              const SizedBox(width: 8),
              Text('低持仓量'),
            ],
          ),
        ),
      ],
    );
  }

  /// 构建交易所选择器
  Widget _buildExchangeSelector(FuturesMarketDataState state) {
    return PopupMenuButton<String>(
      icon: Icon(Icons.account_balance_outlined),
      tooltip: '选择交易所',
      onSelected: (String exchange) {
        ref.read(futuresMarketProvider.notifier).setExchange(exchange);
      },
      itemBuilder: (BuildContext context) => [
        PopupMenuItem(
          value: 'binance',
          child: Row(
            children: [
              Icon(Icons.currency_exchange, size: 18, color: Colors.amber),
              const SizedBox(width: 8),
              Text('币安期货'),
            ],
          ),
        ),
        PopupMenuItem(
          value: 'okx',
          child: Row(
            children: [
              Icon(Icons.currency_exchange, size: 18, color: Colors.blue),
              const SizedBox(width: 8),
              Text('OKX'),
            ],
          ),
        ),
      ],
    );
  }

  /// 构建期货状态卡片
  Widget _buildFuturesStatusCard(FuturesMarketDataState state) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.trending_up_outlined,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                '期货市场状态',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              if (state.lastUpdateTime != null)
                Text(
                  '最后更新: ${DateFormat('HH:mm:ss').format(state.lastUpdateTime!)}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildStatusItem(
                  '交易所',
                  '${state.exchange.toUpperCase()}',
                  Icons.account_balance_outlined,
                ),
              ),
              Expanded(
                child: _buildStatusItem(
                  '数据源',
                  state.realtimeDataEnabled ? '实时' : '定时',
                  state.realtimeDataEnabled ? Icons.wifi : Icons.wifi_off,
                ),
              ),
              Expanded(
                child: _buildStatusItem(
                  '交易对数',
                  '${state.marketData.length}',
                  Icons.list_alt_outlined,
                ),
              ),
            ],
          ),
          if (state.wsLatency != null) ...[
            const SizedBox(height: 8),
            Text(
              'WebSocket延迟: ${state.wsLatency!.inMilliseconds}ms',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          if (state.wsError != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.error_outline, color: Colors.red, size: 16),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      state.wsError!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.red,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// 构建状态项
  Widget _buildStatusItem(String label, String value, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: Theme.of(context).colorScheme.onSurfaceVariant),
            const SizedBox(width: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  /// 构建期货快速统计
  Widget _buildFuturesQuickStats(FuturesMarketDataState state) {
    if (state.marketData.isEmpty) {
      return const SizedBox.shrink();
    }

    final totalOpenInterest = state.marketData.fold<double>(
      0,
      (sum, item) => sum + (item.openInterest ?? 0),
    );

    final totalVolume = state.marketData.fold<double>(
      0,
      (sum, item) => sum + item.volume24h,
    );

    final gainersCount = state.marketData.where((item) => item.priceChangePercent > 0).length;
    final losersCount = state.marketData.where((item) => item.priceChangePercent < 0).length;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(
            child: _buildStatCard(
              '总持仓量',
              _formatNumber(totalOpenInterest),
              Icons.account_balance_wallet_outlined,
              Colors.purple,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildStatCard(
              '总成交量',
              _formatVolume(totalVolume),
              Icons.volume_up_outlined,
              Colors.blue,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildStatCard(
              '上涨/下跌',
              '$gainersCount/$losersCount',
              Icons.show_chart,
              gainersCount > losersCount ? Colors.green : Colors.red,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建资金费率摘要
  Widget _buildFundingRateSummary(FuturesMarketDataState state) {
    if (state.fundingRates.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.percent_outlined,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                '资金费率概览',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildFundingRateItem('平均费率', _calculateAverageFundingRate(state)),
              ),
              Expanded(
                child: _buildFundingRateItem('最高费率', _getMaxFundingRate(state)),
              ),
              Expanded(
                child: _buildFundingRateItem('最低费率', _getMinFundingRate(state)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建资金费率项目
  Widget _buildFundingRateItem(String label, double rate) {
    final isPositive = rate > 0;
    final color = isPositive ? Colors.green : (rate < 0 ? Colors.red : Colors.grey);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Icon(
              isPositive ? Icons.trending_up : Icons.trending_down,
              size: 16,
              color: color,
            ),
            const SizedBox(width: 4),
            Text(
              '${rate.toStringAsFixed(4)}%',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// 计算平均资金费率
  double _calculateAverageFundingRate(FuturesMarketDataState state) {
    if (state.fundingRates.isEmpty) return 0.0;
    
    final rates = state.fundingRates.values.map((fr) => fr.fundingRate * 100).toList();
    return rates.reduce((a, b) => a + b) / rates.length;
  }
  
  /// 获取最高资金费率
  double _getMaxFundingRate(FuturesMarketDataState state) {
    if (state.fundingRates.isEmpty) return 0.0;
    
    final rates = state.fundingRates.values.map((fr) => fr.fundingRate * 100).toList();
    return rates.isNotEmpty ? rates.reduce(math.max) : 0.0;
  }
  
  /// 获取最低资金费率
  double _getMinFundingRate(FuturesMarketDataState state) {
    if (state.fundingRates.isEmpty) return 0.0;
    
    final rates = state.fundingRates.values.map((fr) => fr.fundingRate * 100).toList();
    return rates.isNotEmpty ? rates.reduce(math.min) : 0.0;
  }

  /// 构建统计卡片
  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color.withOpacity(0.2),
        ),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
          Text(
            title,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建期货市场数据表格
  Widget _buildFuturesMarketDataTable(FuturesMarketDataState state) {
    if (state.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              '加载失败',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              state.error!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                ref.read(futuresMarketProvider.notifier).manualRefresh();
              },
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    if (state.marketData.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.data_usage_outlined, size: 48),
            SizedBox(height: 16),
            Text('暂无期货市场数据'),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(futuresMarketProvider.notifier).manualRefresh();
      },
      child: Column(
        children: [
          _buildFuturesSortingHeader(state),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: state.sortedMarketData.length,
              itemBuilder: (context, index) {
                final marketData = state.sortedMarketData[index];
                final fundingRate = state.fundingRates[marketData.symbol];
                final openInterest = state.openInterests[marketData.symbol];
                
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildFuturesMarketCard(
                    marketData: marketData,
                    fundingRate: fundingRate,
                    openInterest: openInterest,
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  /// 构建期货市场卡片
  Widget _buildFuturesMarketCard({
    required MarketData marketData,
    FundingRateData? fundingRate,
    OpenInterestData? openInterest,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Column(
        children: [
          // 基本信息行
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      marketData.symbol,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      '\$${marketData.currentPrice.toStringAsFixed(4)}',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${marketData.priceChangePercent >= 0 ? '+' : ''}${marketData.priceChangePercent.toStringAsFixed(2)}%',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: marketData.priceChangePercent >= 0 ? Colors.green : Colors.red,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    '\$${marketData.priceChange >= 0 ? '+' : ''}${marketData.priceChange.toStringAsFixed(4)}',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: marketData.priceChange >= 0 ? Colors.green : Colors.red,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          // 期货特有信息
          if (fundingRate != null || openInterest != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  if (fundingRate != null) ...[
                    Expanded(
                      child: _buildFuturesInfoItem(
                        '资金费率',
                        '${(fundingRate.fundingRate * 100).toStringAsFixed(4)}%',
                        fundingRate.fundingRate >= 0 ? Icons.trending_up : Icons.trending_down,
                        fundingRate.fundingRate >= 0 ? Colors.green : Colors.red,
                      ),
                    ),
                  ],
                  if (openInterest != null) ...[
                    Expanded(
                      child: _buildFuturesInfoItem(
                        '持仓量',
                        _formatNumber(openInterest.openInterest),
                        Icons.account_balance_wallet,
                        Colors.blue,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          
          // 成交量信息
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildInfoItem('24h成交量', _formatVolume(marketData.volume24h)),
              ),
              Expanded(
                child: _buildInfoItem('24h最高', '\$${marketData.high24h.toStringAsFixed(4)}'),
              ),
              Expanded(
                child: _buildInfoItem('24h最低', '\$${marketData.low24h.toStringAsFixed(4)}'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 构建期货信息项目
  Widget _buildFuturesInfoItem(String label, String value, IconData icon, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
            color: color,
          ),
        ),
      ],
    );
  }

  /// 构建信息项目
  Widget _buildInfoItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  /// 构建期货排序表头
  Widget _buildFuturesSortingHeader(FuturesMarketDataState state) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: _buildSortableHeader(
              '交易对',
              SortField.symbol,
              state,
              alignment: Alignment.centerLeft,
            ),
          ),
          Expanded(
            flex: 2,
            child: _buildSortableHeader(
              '价格',
              SortField.price,
              state,
              alignment: Alignment.centerRight,
            ),
          ),
          Expanded(
            flex: 2,
            child: _buildSortableHeader(
              '涨跌幅',
              SortField.change,
              state,
              alignment: Alignment.centerRight,
            ),
          ),
          Expanded(
            flex: 2,
            child: _buildSortableHeader(
              '资金费率',
              SortField.volume,
              state,
              alignment: Alignment.centerRight,
            ),
          ),
        ],
      ),
    );
  }

  /// 构建可排序的表头
  Widget _buildSortableHeader(
    String title,
    SortField sortField,
    FuturesMarketDataState state, {
    Alignment alignment = Alignment.center,
  }) {
    final isSelected = state.sortField == sortField;
    final sortDirection = isSelected ? state.sortDirection : null;
    
    return InkWell(
      onTap: () {
        final provider = ref.read(futuresMarketProvider.notifier);
        if (isSelected) {
          // 如果当前字段已选中，则切换排序方向
          provider.setSorting(
            sortField,
            state.sortDirection == SortDirection.ascending
                ? SortDirection.descending
                : SortDirection.ascending,
          );
        } else {
          // 如果是新字段，默认降序排列
          provider.setSorting(sortField, SortDirection.descending);
        }
      },
      borderRadius: BorderRadius.circular(4),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Expanded(
              child: Text(
                title,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                  color: isSelected
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                textAlign: alignment == Alignment.centerLeft
                    ? TextAlign.left
                    : TextAlign.right,
              ),
            ),
            if (sortDirection != null) ...[
              const SizedBox(width: 4),
              Icon(
                sortDirection == SortDirection.ascending
                    ? Icons.arrow_upward
                    : Icons.arrow_downward,
                size: 14,
                color: isSelected
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建浮动按钮
  Widget _buildFloatingActionButtons(FuturesMarketDataState state) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!state.autoRefresh)
          FloatingActionButton(
            heroTag: 'auto_refresh',
            mini: true,
            onPressed: () {
              ref.read(futuresMarketProvider.notifier).startAutoRefresh();
            },
            child: const Icon(Icons.autorenew),
          ),
        const SizedBox(height: 8),
        FloatingActionButton(
          heroTag: 'manual_refresh',
          mini: true,
          onPressed: () {
            ref.read(futuresMarketProvider.notifier).manualRefresh();
          },
          child: const Icon(Icons.refresh),
        ),
        const SizedBox(height: 8),
        FloatingActionButton(
          heroTag: 'realtime_toggle',
          mini: true,
          onPressed: () {
            if (state.realtimeDataEnabled) {
              ref.read(futuresMarketProvider.notifier).disableRealtimeData();
            } else {
              ref.read(futuresMarketProvider.notifier).enableRealtimeData();
            }
          },
          backgroundColor: state.realtimeDataEnabled ? Colors.green : Colors.grey,
          child: Icon(
            state.realtimeDataEnabled ? Icons.wifi : Icons.wifi_off,
            size: 20,
          ),
        ),
      ],
    );
  }

  /// 格式化交易量
  String _formatVolume(double volume) {
    if (volume >= 1e12) {
      return '${(volume / 1e12).toStringAsFixed(1)}T';
    } else if (volume >= 1e9) {
      return '${(volume / 1e9).toStringAsFixed(1)}B';
    } else if (volume >= 1e6) {
      return '${(volume / 1e6).toStringAsFixed(1)}M';
    } else if (volume >= 1e3) {
      return '${(volume / 1e3).toStringAsFixed(1)}K';
    } else {
      return volume.toStringAsFixed(0);
    }
  }

  /// 格式化数字
  String _formatNumber(double value) {
    if (value >= 1e12) {
      return '${(value / 1e12).toStringAsFixed(2)}T';
    } else if (value >= 1e9) {
      return '${(value / 1e9).toStringAsFixed(2)}B';
    } else if (value >= 1e6) {
      return '${(value / 1e6).toStringAsFixed(2)}M';
    } else if (value >= 1e3) {
      return '${(value / 1e3).toStringAsFixed(2)}K';
    } else {
      return value.toStringAsFixed(2);
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
}

import 'dart:math' as math;