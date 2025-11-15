import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

/// 期货图表数据类型
enum FuturesChartType {
  price,
  volume,
  fundingRate,
  openInterest,
  markPrice,
  indexPrice,
}

/// 期货K线数据
class FuturesKlineData {
  final DateTime timestamp;
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;
  final double? fundingRate;
  final double? openInterest;
  final double? markPrice;
  final double? indexPrice;
  
  FuturesKlineData({
    required this.timestamp,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
    this.fundingRate,
    this.openInterest,
    this.markPrice,
    this.indexPrice,
  });
}

/// 期货图表组件
class FuturesChartWidget extends StatefulWidget {
  final List<FuturesKlineData> klineData;
  final FuturesChartType selectedChartType;
  final String symbol;
  final VoidCallback? onTap;
  
  const FuturesChartWidget({
    super.key,
    required this.klineData,
    this.selectedChartType = FuturesChartType.price,
    required this.symbol,
    this.onTap,
  });

  @override
  State<FuturesChartWidget> createState() => _FuturesChartWidgetState();
}

class _FuturesChartWidgetState extends State<FuturesChartWidget> {
  FuturesChartType _selectedChartType = FuturesChartType.price;
  final PageController _pageController = PageController();
  int _currentPage = 0;
  
  @override
  void initState() {
    super.initState();
    _selectedChartType = widget.selectedChartType;
  }
  
  @override
  void didUpdateWidget(FuturesChartWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.klineData != widget.klineData) {
      // 数据更新时的处理
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.klineData.isEmpty) {
      return _buildEmptyChart();
    }
    
    return Column(
      children: [
        // 图表类型选择器
        _buildChartTypeSelector(),
        const SizedBox(height: 8),
        
        // 图表显示区域
        Expanded(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
              ),
            ),
            child: Column(
              children: [
                // 图表头部信息
                _buildChartHeader(),
                const Divider(height: 1),
                
                // 图表内容
                Expanded(
                  child: _buildChartContent(),
                ),
                
                const Divider(height: 1),
                
                // 图表底部信息
                _buildChartFooter(),
              ],
            ),
          ),
        ),
      ],
    );
  }
  
  /// 构建空图表
  Widget _buildEmptyChart() {
    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.show_chart_outlined,
              size: 48,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              '暂无图表数据',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '等待期货数据加载...',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  /// 构建图表类型选择器
  Widget _buildChartTypeSelector() {
    final chartTypes = [
      FuturesChartType.price,
      FuturesChartType.volume,
      FuturesChartType.fundingRate,
      FuturesChartType.openInterest,
    ];
    
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: chartTypes.map((type) {
                  final isSelected = _selectedChartType == type;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text(_getChartTypeTitle(type)),
                      selected: isSelected,
                      onSelected: (selected) {
                        if (selected) {
                          setState(() {
                            _selectedChartType = type;
                          });
                        }
                      },
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.fullscreen),
            onPressed: _showFullScreenChart,
            tooltip: '全屏显示',
          ),
        ],
      ),
    );
  }
  
  /// 构建图表头部信息
  Widget _buildChartHeader() {
    final latestData = widget.klineData.isNotEmpty 
        ? widget.klineData.last 
        : null;
    
    if (latestData == null) return const SizedBox.shrink();
    
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.symbol,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _getCurrentPrice(),
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: _getPriceChangeColor(),
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                _getPriceChangeInfo(),
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: _getPriceChangeColor(),
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                DateFormat('HH:mm').format(latestData.timestamp),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  /// 构建图表内容
  Widget _buildChartContent() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: _buildChartVisualization(),
    );
  }
  
  /// 构建图表可视化
  Widget _buildChartVisualization() {
    switch (_selectedChartType) {
      case FuturesChartType.price:
        return _buildPriceChart();
      case FuturesChartType.volume:
        return _buildVolumeChart();
      case FuturesChartType.fundingRate:
        return _buildFundingRateChart();
      case FuturesChartType.openInterest:
        return _buildOpenInterestChart();
      case FuturesChartType.markPrice:
        return _buildMarkPriceChart();
      case FuturesChartType.indexPrice:
        return _buildIndexPriceChart();
    }
  }
  
  /// 构建价格图表
  Widget _buildPriceChart() {
    if (widget.klineData.isEmpty) {
      return const Center(child: Text('无价格数据'));
    }
    
    return Container(
      height: 200,
      child: CustomPaint(
        painter: PriceChartPainter(
          data: widget.klineData,
          lineColor: Colors.blue,
          fillColor: Colors.blue.withOpacity(0.1),
        ),
        child: Container(),
      ),
    );
  }
  
  /// 构建成交量图表
  Widget _buildVolumeChart() {
    if (widget.klineData.isEmpty) {
      return const Center(child: Text('无成交量数据'));
    }
    
    return Container(
      height: 200,
      child: CustomPaint(
        painter: VolumeChartPainter(
          data: widget.klineData,
          barColor: Colors.green,
        ),
        child: Container(),
      ),
    );
  }
  
  /// 构建资金费率图表
  Widget _buildFundingRateChart() {
    final fundingRateData = widget.klineData
        .where((kline) => kline.fundingRate != null)
        .toList();
    
    if (fundingRateData.isEmpty) {
      return const Center(child: Text('无资金费率数据'));
    }
    
    return Container(
      height: 200,
      child: CustomPaint(
        painter: FundingRateChartPainter(
          data: fundingRateData,
          lineColor: Colors.orange,
          fillColor: Colors.orange.withOpacity(0.1),
        ),
        child: Container(),
      ),
    );
  }
  
  /// 构建持仓量图表
  Widget _buildOpenInterestChart() {
    final oiData = widget.klineData
        .where((kline) => kline.openInterest != null)
        .toList();
    
    if (oiData.isEmpty) {
      return const Center(child: Text('无持仓量数据'));
    }
    
    return Container(
      height: 200,
      child: CustomPaint(
        painter: OpenInterestChartPainter(
          data: oiData,
          lineColor: Colors.purple,
          fillColor: Colors.purple.withOpacity(0.1),
        ),
        child: Container(),
      ),
    );
  }
  
  /// 构建标记价格图表
  Widget _buildMarkPriceChart() {
    final markPriceData = widget.klineData
        .where((kline) => kline.markPrice != null)
        .toList();
    
    if (markPriceData.isEmpty) {
      return const Center(child: Text('无标记价格数据'));
    }
    
    return Container(
      height: 200,
      child: CustomPaint(
        painter: MarkPriceChartPainter(
          data: markPriceData,
          lineColor: Colors.indigo,
          fillColor: Colors.indigo.withOpacity(0.1),
        ),
        child: Container(),
      ),
    );
  }
  
  /// 构建指数价格图表
  Widget _buildIndexPriceChart() {
    final indexPriceData = widget.klineData
        .where((kline) => kline.indexPrice != null)
        .toList();
    
    if (indexPriceData.isEmpty) {
      return const Center(child: Text('无指数价格数据'));
    }
    
    return Container(
      height: 200,
      child: CustomPaint(
        painter: IndexPriceChartPainter(
          data: indexPriceData,
          lineColor: Colors.teal,
          fillColor: Colors.teal.withOpacity(0.1),
        ),
        child: Container(),
      ),
    );
  }
  
  /// 构建图表底部信息
  Widget _buildChartFooter() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Icon(
            Icons.access_time,
            size: 16,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 8),
          Text(
            '数据点: ${widget.klineData.length}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const Spacer(),
          Text(
            _getCurrentChartTypeDescription(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
  
  /// 显示全屏图表
  void _showFullScreenChart() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => _FullScreenChartPage(
          symbol: widget.symbol,
          klineData: widget.klineData,
          selectedChartType: _selectedChartType,
        ),
      ),
    );
  }
  
  /// 获取图表类型标题
  String _getChartTypeTitle(FuturesChartType type) {
    switch (type) {
      case FuturesChartType.price:
        return '价格';
      case FuturesChartType.volume:
        return '成交量';
      case FuturesChartType.fundingRate:
        return '资金费率';
      case FuturesChartType.openInterest:
        return '持仓量';
      case FuturesChartType.markPrice:
        return '标记价格';
      case FuturesChartType.indexPrice:
        return '指数价格';
    }
  }
  
  /// 获取当前价格
  String _getCurrentPrice() {
    if (widget.klineData.isEmpty) return '--';
    final latest = widget.klineData.last;
    
    switch (_selectedChartType) {
      case FuturesChartType.price:
      case FuturesChartType.markPrice:
      case FuturesChartType.indexPrice:
        return '\$${latest.close.toStringAsFixed(4)}';
      case FuturesChartType.volume:
        return _formatVolume(latest.volume);
      case FuturesChartType.fundingRate:
        return latest.fundingRate != null 
            ? '${(latest.fundingRate! * 100).toStringAsFixed(4)}%'
            : '--';
      case FuturesChartType.openInterest:
        return latest.openInterest != null 
            ? _formatLargeNumber(latest.openInterest!)
            : '--';
    }
  }
  
  /// 获取价格变化颜色
  Color _getPriceChangeColor() {
    if (widget.klineData.isEmpty) return Colors.grey;
    if (widget.klineData.length < 2) return Colors.grey;
    
    final latest = widget.klineData.last;
    final previous = widget.klineData[widget.klineData.length - 2];
    
    if (latest.close > previous.close) {
      return Colors.green;
    } else if (latest.close < previous.close) {
      return Colors.red;
    } else {
      return Colors.grey;
    }
  }
  
  /// 获取价格变化信息
  String _getPriceChangeInfo() {
    if (widget.klineData.isEmpty) return '';
    if (widget.klineData.length < 2) return '';
    
    final latest = widget.klineData.last;
    final previous = widget.klineData[widget.klineData.length - 2];
    
    final change = latest.close - previous.close;
    final changePercent = (change / previous.close) * 100;
    
    final sign = change >= 0 ? '+' : '';
    return '${sign}${change.toStringAsFixed(4)} (${sign}${changePercent.toStringAsFixed(2)}%)';
  }
  
  /// 获取当前图表类型描述
  String _getCurrentChartTypeDescription() {
    switch (_selectedChartType) {
      case FuturesChartType.price:
        return 'K线价格走势';
      case FuturesChartType.volume:
        return '交易量变化';
      case FuturesChartType.fundingRate:
        return '资金费率变化';
      case FuturesChartType.openInterest:
        return '持仓量变化';
      case FuturesChartType.markPrice:
        return '标记价格';
      case FuturesChartType.indexPrice:
        return '指数价格';
    }
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
  
  /// 格式化大数字
  String _formatLargeNumber(double value) {
    if (value >= 1e12) {
      return '${(value / 1e12).toStringAsFixed(2)}T';
    } else if (value >= 1e9) {
      return '${(value / 1e9).toStringAsFixed(2)}B';
    } else if (value >= 1e6) {
      return '${(value / 1e6).toStringAsFixed(2)}M';
    } else if (value >= 1e3) {
      return '${(value / 1e3).toStringAsFixed(2)}K';
    } else {
      return value.toStringAsFixed(0);
    }
  }
  
  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
}

/// 全屏图表页面
class _FullScreenChartPage extends StatelessWidget {
  final String symbol;
  final List<FuturesKlineData> klineData;
  final FuturesChartType selectedChartType;
  
  const _FullScreenChartPage({
    required this.symbol,
    required this.klineData,
    required this.selectedChartType,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('$symbol - 全屏图表'),
        actions: [
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
      body: FuturesChartWidget(
        symbol: symbol,
        klineData: klineData,
        selectedChartType: selectedChartType,
      ),
    );
  }
}

/// 基础图表绘制器
abstract class ChartDataPainter extends CustomPainter {
  final List<FuturesKlineData> data;
  final Color lineColor;
  final Color? fillColor;
  
  ChartDataPainter({
    required this.data,
    required this.lineColor,
    this.fillColor,
  });
}

/// 价格图表绘制器
class PriceChartPainter extends ChartDataPainter {
  PriceChartPainter({
    required super.data,
    required super.lineColor,
    super.fillColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // TODO: 实现价格图表绘制
    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0;
    
    if (data.isNotEmpty) {
      final path = Path();
      path.moveTo(0, size.height / 2);
      for (int i = 0; i < data.length; i++) {
        final x = (size.width / (data.length - 1)) * i;
        final y = size.height / 2 - (data[i].close - data[i].open) * 10;
        path.lineTo(x, y);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// 成交量图表绘制器
class VolumeChartPainter extends ChartDataPainter {
  VolumeChartPainter({
    required super.data,
    required super.lineColor,
    super.fillColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = lineColor;
    
    if (data.isNotEmpty) {
      final barWidth = size.width / data.length;
      for (int i = 0; i < data.length; i++) {
        final barHeight = (data[i].volume / 1000000) * 10; // 缩放因子
        final x = barWidth * i;
        final y = size.height - barHeight;
        
        canvas.drawRect(
          Rect.fromPoints(Offset(x, y), Offset(x + barWidth * 0.8, size.height)),
          paint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// 资金费率图表绘制器
class FundingRateChartPainter extends ChartDataPainter {
  FundingRateChartPainter({
    required super.data,
    required super.lineColor,
    super.fillColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0;
    
    if (data.isNotEmpty) {
      final path = Path();
      path.moveTo(0, size.height / 2);
      for (int i = 0; i < data.length; i++) {
        final x = (size.width / (data.length - 1)) * i;
        final y = size.height / 2 - (data[i].fundingRate! * 1000); // 缩放因子
        path.lineTo(x, y);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// 持仓量图表绘制器
class OpenInterestChartPainter extends ChartDataPainter {
  OpenInterestChartPainter({
    required super.data,
    required super.lineColor,
    super.fillColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0;
    
    if (data.isNotEmpty) {
      final path = Path();
      path.moveTo(0, size.height / 2);
      for (int i = 0; i < data.length; i++) {
        final x = (size.width / (data.length - 1)) * i;
        final y = size.height / 2 - (data[i].openInterest! / 100000) * 10; // 缩放因子
        path.lineTo(x, y);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// 标记价格图表绘制器
class MarkPriceChartPainter extends ChartDataPainter {
  MarkPriceChartPainter({
    required super.data,
    required super.lineColor,
    super.fillColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0;
    
    if (data.isNotEmpty) {
      final path = Path();
      path.moveTo(0, size.height / 2);
      for (int i = 0; i < data.length; i++) {
        final x = (size.width / (data.length - 1)) * i;
        final y = size.height / 2 - (data[i].markPrice! - 40000) * 10; // 假设基准价格
        path.lineTo(x, y);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// 指数价格图表绘制器
class IndexPriceChartPainter extends ChartDataPainter {
  IndexPriceChartPainter({
    required super.data,
    required super.lineColor,
    super.fillColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0;
    
    if (data.isNotEmpty) {
      final path = Path();
      path.moveTo(0, size.height / 2);
      for (int i = 0; i < data.length; i++) {
        final x = (size.width / (data.length - 1)) * i;
        final y = size.height / 2 - (data[i].indexPrice! - 40000) * 10; // 假设基准价格
        path.lineTo(x, y);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}