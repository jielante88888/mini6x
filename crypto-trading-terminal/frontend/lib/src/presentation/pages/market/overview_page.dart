import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../providers/market_data_provider.dart';
import '../widgets/common/market_card.dart';

/// 市场概览页面
class MarketOverviewPage extends ConsumerStatefulWidget {
  const MarketOverviewPage({super.key});

  @override
  ConsumerState<MarketOverviewPage> createState() => _MarketOverviewPageState();
}

class _MarketOverviewPageState extends ConsumerState<MarketOverviewPage> {
  @override
  void initState() {
    super.initState();
    
    // 页面初始化时获取市场数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(marketDataProvider.notifier).fetchMarketData();
      ref.read(marketDataProvider.notifier).enableRealtimeData();
      ref.read(marketDataProvider.notifier).startAutoRefresh();
    });
  }

  @override
  void dispose() {
    super.dispose();
    ref.read(marketDataProvider.notifier).dispose();
  }

  @override
  Widget build(BuildContext context) {
    final marketDataState = ref.watch(marketDataProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('市场概览'),
        elevation: 0,
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        actions: [
          _buildConnectionStatusIndicator(marketDataState),
          const SizedBox(width: 8),
          _buildMarketTypeSelector(),
          const SizedBox(width: 8),
          _buildExchangeSelector(marketDataState),
          const SizedBox(width: 16),
        ],
      ),
      body: Column(
        children: [
          _buildStatusCard(marketDataState),
          _buildQuickStats(marketDataState),
          Expanded(
            child: _buildMarketDataTable(marketDataState),
          ),
        ],
      ),
      floatingActionButton: _buildFloatingActionButtons(marketDataState),
    );
  }

  /// 构建连接状态指示器
  Widget _buildConnectionStatusIndicator(MarketDataState state) {
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

  /// 构建市场类型选择器
  Widget _buildMarketTypeSelector() {
    return PopupMenuButton<MarketType>(
      icon: Icon(Icons.account_tree_outlined),
      tooltip: '选择市场类型',
      onSelected: (MarketType type) {
        ref.read(marketDataProvider.notifier).setMarketType(type);
      },
      itemBuilder: (BuildContext context) => [
        PopupMenuItem(
          value: MarketType.spot,
          child: Row(
            children: [
              Icon(Icons.shopping_cart_outlined, size: 18),
              const SizedBox(width: 8),
              Text('现货市场'),
            ],
          ),
        ),
        PopupMenuItem(
          value: MarketType.futures,
          child: Row(
            children: [
              Icon(Icons.trending_up_outlined, size: 18),
              const SizedBox(width: 8),
              Text('合约市场'),
            ],
          ),
        ),
      ],
    );
  }

  /// 构建交易所选择器
  Widget _buildExchangeSelector(MarketDataState state) {
    return PopupMenuButton<String>(
      icon: Icon(Icons.account_balance_outlined),
      tooltip: '选择交易所',
      onSelected: (String exchange) {
        ref.read(marketDataProvider.notifier).setExchange(exchange);
      },
      itemBuilder: (BuildContext context) => [
        PopupMenuItem(
          value: 'binance',
          child: Row(
            children: [
              Icon(Icons.currency_exchange, size: 18, color: Colors.amber),
              const SizedBox(width: 8),
              Text('币安'),
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

  /// 构建状态卡片
  Widget _buildStatusCard(MarketDataState state) {
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
                Icons.info_outline,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                '市场状态',
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
                  '${state.exchange.toUpperCase()} (${state.marketType.name})',
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

  /// 构建快速统计
  Widget _buildQuickStats(MarketDataState state) {
    if (state.marketData.isEmpty) {
      return const SizedBox.shrink();
    }

    final totalMarketCap = state.marketData.fold<double>(
      0,
      (sum, item) => sum + (item.currentPrice * item.volume24h),
    );

    final gainersCount = state.marketData.where((item) => item.priceChangePercent > 0).length;
    final losersCount = state.marketData.where((item) => item.priceChangePercent < 0).length;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(
            child: _buildStatCard(
              '总交易量',
              _formatVolume(totalMarketCap),
              Icons.volume_up_outlined,
              Colors.blue,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildStatCard(
              '上涨',
              '$gainersCount',
              Icons.trending_up,
              Colors.green,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildStatCard(
              '下跌',
              '$losersCount',
              Icons.trending_down,
              Colors.red,
            ),
          ),
        ],
      ),
    );
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

  /// 构建市场数据表格
  Widget _buildMarketDataTable(MarketDataState state) {
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
                ref.read(marketDataProvider.notifier).manualRefresh();
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
            Text('暂无市场数据'),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(marketDataProvider.notifier).manualRefresh();
      },
      child: Column(
        children: [
          _buildSortingHeader(state),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: state.sortedMarketData.length,
              itemBuilder: (context, index) {
                final marketData = state.sortedMarketData[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: MarketCard(marketData: marketData),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  /// 构建排序表头
  Widget _buildSortingHeader(MarketDataState state) {
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
              '成交量',
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
    MarketDataState state, {
    Alignment alignment = Alignment.center,
  }) {
    final isSelected = state.sortField == sortField;
    final sortDirection = isSelected ? state.sortDirection : null;
    
    return InkWell(
      onTap: () {
        final provider = ref.read(marketDataProvider.notifier);
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
  Widget _buildFloatingActionButtons(MarketDataState state) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!state.autoRefresh)
          FloatingActionButton(
            heroTag: 'auto_refresh',
            mini: true,
            onPressed: () {
              ref.read(marketDataProvider.notifier).startAutoRefresh();
            },
            child: const Icon(Icons.autorenew),
          ),
        const SizedBox(height: 8),
        FloatingActionButton(
          heroTag: 'manual_refresh',
          mini: true,
          onPressed: () {
            ref.read(marketDataProvider.notifier).manualRefresh();
          },
          child: const Icon(Icons.refresh),
        ),
        const SizedBox(height: 8),
        FloatingActionButton(
          heroTag: 'realtime_toggle',
          mini: true,
          onPressed: () {
            if (state.realtimeDataEnabled) {
              ref.read(marketDataProvider.notifier).disableRealtimeData();
            } else {
              ref.read(marketDataProvider.notifier).enableRealtimeData();
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

  /// 解析颜色字符串
  Color _parseColor(String hexColor) {
    try {
      return Color(int.parse(hexColor.replaceFirst('#', '0xff')));
    } catch (e) {
      return Colors.grey;
    }
  }

  /// 构建排序表头
  Widget _buildSortingHeader(MarketDataState state) {
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
              '成交量',
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
    MarketDataState state, {
    Alignment alignment = Alignment.center,
  }) {
    final isSelected = state.sortField == sortField;
    final sortDirection = isSelected ? state.sortDirection : null;
    
    return InkWell(
      onTap: () {
        final provider = ref.read(marketDataProvider.notifier);
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
}