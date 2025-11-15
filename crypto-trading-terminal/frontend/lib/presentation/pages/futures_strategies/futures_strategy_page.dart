import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:async';
import 'dart:math' as math;

final futuresStrategyProvider = StateNotifierProvider<FuturesStrategyNotifier, FuturesStrategyState>((ref) {
  return FuturesStrategyNotifier();
});

class FuturesStrategyState {
  final List<FuturesPosition> positions;
  final List<MarginAlert> activeAlerts;
  final Map<String, FuturesMarketData> marketData;
  final double portfolioValue;
  final double totalMarginUsed;
  final double availableMargin;
  final String riskLevel;

  const FuturesStrategyState({
    this.positions = const [],
    this.activeAlerts = const [],
    this.marketData = const {},
    this.portfolioValue = 0.0,
    this.totalMarginUsed = 0.0,
    this.availableMargin = 0.0,
    this.riskLevel = 'LOW',
  });

  FuturesStrategyState copyWith({
    List<FuturesPosition>? positions,
    List<MarginAlert>? activeAlerts,
    Map<String, FuturesMarketData>? marketData,
    double? portfolioValue,
    double? totalMarginUsed,
    double? availableMargin,
    String? riskLevel,
  }) {
    return FuturesStrategyState(
      positions: positions ?? this.positions,
      activeAlerts: activeAlerts ?? this.activeAlerts,
      marketData: marketData ?? this.marketData,
      portfolioValue: portfolioValue ?? this.portfolioValue,
      totalMarginUsed: totalMarginUsed ?? this.totalMarginUsed,
      availableMargin: availableMargin ?? this.availableMargin,
      riskLevel: riskLevel ?? this.riskLevel,
    );
  }
}

class FuturesPosition {
  final String symbol;
  final String side; // 'LONG' or 'SHORT'
  final double size;
  final double entryPrice;
  final double currentPrice;
  final double leverage;
  final double liquidationPrice;
  final double pnl;
  final double marginUsed;
  final double marginRatio;

  const FuturesPosition({
    required this.symbol,
    required this.side,
    required this.size,
    required this.entryPrice,
    required this.currentPrice,
    required this.leverage,
    required this.liquidationPrice,
    required this.pnl,
    required this.marginUsed,
    required this.marginRatio,
  });
}

class FuturesMarketData {
  final String symbol;
  final double currentPrice;
  final double priceChange24h;
  final double volume24h;
  final double fundingRate;
  final double openInterest;

  const FuturesMarketData({
    required this.symbol,
    required this.currentPrice,
    required this.priceChange24h,
    required this.volume24h,
    required this.fundingRate,
    required this.openInterest,
  });
}

class MarginAlert {
  final String id;
  final String type;
  final String message;
  final String riskLevel;
  final DateTime timestamp;

  const MarginAlert({
    required this.id,
    required this.type,
    required this.message,
    required this.riskLevel,
    required this.timestamp,
  });
}

class FuturesStrategyNotifier extends StateNotifier<FuturesStrategyState> {
  FuturesStrategyNotifier() : super(const FuturesStrategyState()) {
    _initializeMockData();
    _startRealTimeUpdates();
  }

  void _initializeMockData() {
    // 模拟初始数据
    state = state.copyWith(
      positions: [
        FuturesPosition(
          symbol: 'BTC/USDT',
          side: 'LONG',
          size: 0.1,
          entryPrice: 50000.0,
          currentPrice: 51000.0,
          leverage: 10.0,
          liquidationPrice: 45000.0,
          pnl: 100.0,
          marginUsed: 500.0,
          marginRatio: 120.0,
        ),
        FuturesPosition(
          symbol: 'ETH/USDT',
          side: 'SHORT',
          size: 1.0,
          entryPrice: 3200.0,
          currentPrice: 3150.0,
          leverage: 5.0,
          liquidationPrice: 3500.0,
          pnl: 50.0,
          marginUsed: 640.0,
          marginRatio: 108.0,
        ),
      ],
      portfolioValue: 12500.0,
      totalMarginUsed: 1140.0,
      availableMargin: 11360.0,
      marketData: {
        'BTC/USDT': FuturesMarketData(
          symbol: 'BTC/USDT',
          currentPrice: 51000.0,
          priceChange24h: 2.5,
          volume24h: 2.5e9,
          fundingRate: 0.01,
          openInterest: 2.1e9,
        ),
        'ETH/USDT': FuturesMarketData(
          symbol: 'ETH/USDT',
          currentPrice: 3150.0,
          priceChange24h: -1.2,
          volume24h: 8.5e8,
          fundingRate: -0.005,
          openInterest: 1.8e9,
        ),
      },
    );
  }

  void _startRealTimeUpdates() {
    Timer.periodic(const Duration(seconds: 5), (timer) {
      _updateMockData();
    });
  }

  void _updateMockData() {
    final random = math.Random();
    final positions = state.positions.map((position) {
      final priceChange = (random.nextDouble() - 0.5) * 200; // -100 to +100
      final newPrice = position.currentPrice + priceChange;
      
      double newPnl;
      if (position.side == 'LONG') {
        newPnl = (newPrice - position.entryPrice) * position.size;
      } else {
        newPnl = (position.entryPrice - newPrice) * position.size;
      }
      
      final newMarginRatio = 100 + (newPnl / position.marginUsed) * 100;
      
      return position.copyWith(
        currentPrice: newPrice,
        pnl: newPnl,
        marginRatio: newMarginRatio,
      );
    }).toList();
    
    final totalMarginUsed = positions.fold(0.0, (sum, p) => sum + p.marginUsed);
    final totalPnl = positions.fold(0.0, (sum, p) => sum + p.pnl);
    final newPortfolioValue = 10000.0 + totalPnl; // 基础余额10000
    
    // 计算整体风险等级
    String riskLevel = 'LOW';
    final minMarginRatio = positions.fold(double.infinity, (min, p) => math.min(min, p.marginRatio));
    if (minMarginRatio < 105) {
      riskLevel = 'CRITICAL';
    } else if (minMarginRatio < 110) {
      riskLevel = 'HIGH';
    } else if (minMarginRatio < 120) {
      riskLevel = 'MEDIUM';
    }
    
    state = state.copyWith(
      positions: positions,
      totalMarginUsed: totalMarginUsed,
      availableMargin: newPortfolioValue - totalMarginUsed,
      portfolioValue: newPortfolioValue,
      riskLevel: riskLevel,
    );
  }

  void updateLeverage(String symbol, double newLeverage) {
    // 更新杠杆倍数
    final positions = state.positions.map((position) {
      if (position.symbol == symbol) {
        return position.copyWith(leverage: newLeverage);
      }
      return position;
    }).toList();
    
    state = state.copyWith(positions: positions);
  }

  void addPosition(FuturesPosition newPosition) {
    final positions = [...state.positions, newPosition];
    state = state.copyWith(positions: positions);
  }

  void closePosition(String symbol) {
    final positions = state.positions.where((p) => p.symbol != symbol).toList();
    state = state.copyWith(positions: positions);
  }

  void acknowledgeAlert(String alertId) {
    // 处理预警确认
    // 这里应该更新后端状态
  }
}

class FuturesStrategyPage extends ConsumerWidget {
  const FuturesStrategyPage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strategyState = ref.watch(futuresStrategyProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('期货策略管理'),
        backgroundColor: _getRiskLevelColor(strategyState.riskLevel),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showStrategySettings(context),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(futuresStrategyProvider.notifier)._updateMockData(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.read(futuresStrategyProvider.notifier)._updateMockData();
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildPortfolioSummary(strategyState),
              const SizedBox(height: 16),
              _buildRiskIndicator(strategyState),
              const SizedBox(height: 16),
              _buildPositionsList(context, strategyState),
              const SizedBox(height: 16),
              _buildActiveAlerts(strategyState),
              const SizedBox(height: 16),
              _buildQuickActions(context, ref),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showNewPositionDialog(context, ref),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildPortfolioSummary(FuturesStrategyState state) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '投资组合概览',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSummaryItem('总资产', '\$${state.portfolioValue.toStringAsFixed(2)}'),
                _buildSummaryItem('已用保证金', '\$${state.totalMarginUsed.toStringAsFixed(2)}'),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSummaryItem('可用保证金', '\$${state.availableMargin.toStringAsFixed(2)}', 
                    color: Colors.green),
                _buildSummaryItem('保证金使用率', '${((state.totalMarginUsed / state.portfolioValue) * 100).toStringAsFixed(1)}%'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, {Color? color}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }

  Widget _buildRiskIndicator(FuturesStrategyState state) {
    Color riskColor = _getRiskLevelColor(state.riskLevel);
    String riskText = _getRiskLevelText(state.riskLevel);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: riskColor,
                shape: BoxShape.circle,
              ),
              child: Icon(
                _getRiskLevelIcon(state.riskLevel),
                color: Colors.white,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '风险等级',
                    style: TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                  Text(
                    riskText,
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: riskColor,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.analytics),
              onPressed: () => _showRiskAnalysis(state),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPositionsList(BuildContext context, FuturesStrategyState state) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  '当前持仓',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                Text(
                  '${state.positions.length} 个持仓',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
          if (state.positions.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(
                child: Text(
                  '暂无持仓',
                  style: TextStyle(color: Colors.grey),
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: state.positions.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final position = state.positions[index];
                return _buildPositionItem(context, position);
              },
            ),
        ],
      ),
    );
  }

  Widget _buildPositionItem(BuildContext context, FuturesPosition position) {
    final pnlColor = position.pnl >= 0 ? Colors.green : Colors.red;
    
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      title: Row(
        children: [
          Text(
            position.symbol,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: position.side == 'LONG' ? Colors.green[100] : Colors.red[100],
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              position.side,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: position.side == 'LONG' ? Colors.green[700] : Colors.red[700],
              ),
            ),
          ),
        ],
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('规模: ${position.size}'),
              Text('杠杆: ${position.leverage}x'),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('开仓价: \$${position.entryPrice.toStringAsFixed(2)}'),
              Text('现价: \$${position.currentPrice.toStringAsFixed(2)}'),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '盈亏: \$${position.pnl.toStringAsFixed(2)}',
                style: TextStyle(color: pnlColor, fontWeight: FontWeight.w600),
              ),
              Text('强平价: \$${position.liquidationPrice.toStringAsFixed(2)}'),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: LinearProgressIndicator(
                  value: math.min(position.marginRatio / 200, 1.0),
                  backgroundColor: Colors.grey[300],
                  valueColor: AlwaysStoppedAnimation<Color>(
                    _getMarginRatioColor(position.marginRatio),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${position.marginRatio.toStringAsFixed(1)}%',
                style: TextStyle(
                  fontSize: 12,
                  color: _getMarginRatioColor(position.marginRatio),
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
      trailing: PopupMenuButton<String>(
        onSelected: (value) => _handlePositionAction(context, value, position),
        itemBuilder: (context) => [
          const PopupMenuItem(
            value: 'edit',
            child: Text('编辑'),
          ),
          const PopupMenuItem(
            value: 'close',
            child: Text('平仓'),
          ),
          const PopupMenuItem(
            value: 'adjust_leverage',
            child: Text('调整杠杆'),
          ),
        ],
      ),
    );
  }

  Widget _buildActiveAlerts(FuturesStrategyState state) {
    if (state.activeAlerts.isEmpty) {
      return const SizedBox.shrink();
    }
    
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  Icons.warning,
                  color: Colors.orange[700],
                  size: 20,
                ),
                const SizedBox(width: 8),
                const Text(
                  '活跃预警',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.orange[100],
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${state.activeAlerts.length}',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Colors.orange[700],
                    ),
                  ),
                ),
              ],
            ),
          ),
          ...state.activeAlerts.take(3).map((alert) => _buildAlertItem(alert)),
          if (state.activeAlerts.length > 3)
            Padding(
              padding: const EdgeInsets.all(16),
              child: TextButton(
                onPressed: () => _showAllAlerts(context, state.activeAlerts),
                child: Text('查看全部 ${state.activeAlerts.length} 个预警'),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildAlertItem(MarginAlert alert) {
    final alertColor = _getAlertColor(alert.riskLevel);
    
    return ListTile(
      leading: Icon(
        _getAlertIcon(alert.type),
        color: alertColor,
        size: 20,
      ),
      title: Text(
        alert.message,
        style: const TextStyle(fontSize: 14),
      ),
      subtitle: Text(
        alert.timestamp.toString().substring(0, 19),
        style: TextStyle(fontSize: 12, color: Colors.grey[600]),
      ),
      trailing: IconButton(
        icon: const Icon(Icons.close, size: 16),
        onPressed: () => _acknowledgeAlert(alert.id),
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context, WidgetRef ref) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '快速操作',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _showNewPositionDialog(context, ref),
                    icon: const Icon(Icons.add),
                    label: const Text('开仓'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _closeAllPositions(context),
                    icon: const Icon(Icons.close_all),
                    label: const Text('一键平仓'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _adjustLeverage(context),
                    icon: const Icon(Icons.tune),
                    label: const Text('批量调杠杆'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _showRiskSettings(context),
                    icon: const Icon(Icons.security),
                    label: const Text('风险设置'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // Helper methods
  Color _getRiskLevelColor(String riskLevel) {
    switch (riskLevel) {
      case 'CRITICAL':
        return Colors.red;
      case 'HIGH':
        return Colors.orange;
      case 'MEDIUM':
        return Colors.amber;
      default:
        return Colors.green;
    }
  }

  String _getRiskLevelText(String riskLevel) {
    switch (riskLevel) {
      case 'CRITICAL':
        return '极高风险';
      case 'HIGH':
        return '高风险';
      case 'MEDIUM':
        return '中等风险';
      default:
        return '低风险';
    }
  }

  IconData _getRiskLevelIcon(String riskLevel) {
    switch (riskLevel) {
      case 'CRITICAL':
        return Icons.dangerous;
      case 'HIGH':
        return Icons.warning;
      case 'MEDIUM':
        return Icons.info;
      default:
        return Icons.check_circle;
    }
  }

  Color _getMarginRatioColor(double ratio) {
    if (ratio < 105) return Colors.red;
    if (ratio < 110) return Colors.orange;
    if (ratio < 120) return Colors.amber;
    return Colors.green;
  }

  Color _getAlertColor(String riskLevel) {
    switch (riskLevel) {
      case 'CRITICAL':
        return Colors.red;
      case 'HIGH':
        return Colors.orange;
      default:
        return Colors.amber;
    }
  }

  IconData _getAlertIcon(String alertType) {
    switch (alertType) {
      case 'margin_call':
        return Icons.warning;
      case 'liquidation_risk':
        return Icons.dangerous;
      default:
        return Icons.info;
    }
  }

  void _showStrategySettings(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('策略设置'),
        content: const Text('策略设置功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showRiskAnalysis(FuturesStrategyState state) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('风险分析'),
        content: const Text('风险分析功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showNewPositionDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('开仓'),
        content: const Text('开仓功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _handlePositionAction(BuildContext context, String action, FuturesPosition position) {
    switch (action) {
      case 'close':
        _closePosition(context, position);
        break;
      case 'adjust_leverage':
        _adjustPositionLeverage(context, position);
        break;
      case 'edit':
        _editPosition(context, position);
        break;
    }
  }

  void _closePosition(BuildContext context, FuturesPosition position) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认平仓'),
        content: Text('确定要平仓 ${position.symbol} 吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // 执行平仓逻辑
            },
            child: const Text('确认'),
          ),
        ],
      ),
    );
  }

  void _adjustPositionLeverage(BuildContext context, FuturesPosition position) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('调整 ${position.symbol} 杠杆'),
        content: const Text('杠杆调整功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _editPosition(BuildContext context, FuturesPosition position) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('编辑 ${position.symbol}'),
        content: const Text('位置编辑功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _closeAllPositions(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('一键平仓'),
        content: const Text('确定要平仓所有持仓吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // 执行一键平仓逻辑
            },
            child: const Text('确认'),
          ),
        ],
      ),
    );
  }

  void _adjustLeverage(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('批量调整杠杆'),
        content: const Text('批量杠杆调整功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showRiskSettings(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('风险设置'),
        content: const Text('风险设置功能开发中...'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showAllAlerts(BuildContext context, List<MarginAlert> alerts) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('所有预警'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: alerts.length,
            itemBuilder: (context, index) {
              final alert = alerts[index];
              return ListTile(
                leading: Icon(_getAlertIcon(alert.type)),
                title: Text(alert.message),
                subtitle: Text(alert.timestamp.toString().substring(0, 19)),
              );
            },
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

  void _acknowledgeAlert(String alertId) {
    // 处理预警确认逻辑
  }
}

// Extension for position copying
extension FuturesPositionCopy on FuturesPosition {
  FuturesPosition copyWith({
    String? symbol,
    String? side,
    double? size,
    double? entryPrice,
    double? currentPrice,
    double? leverage,
    double? liquidationPrice,
    double? pnl,
    double? marginUsed,
    double? marginRatio,
  }) {
    return FuturesPosition(
      symbol: symbol ?? this.symbol,
      side: side ?? this.side,
      size: size ?? this.size,
      entryPrice: entryPrice ?? this.entryPrice,
      currentPrice: currentPrice ?? this.currentPrice,
      leverage: leverage ?? this.leverage,
      liquidationPrice: liquidationPrice ?? this.liquidationPrice,
      pnl: pnl ?? this.pnl,
      marginUsed: marginUsed ?? this.marginUsed,
      marginRatio: marginRatio ?? this.marginRatio,
    );
  }
}