import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// 期货特有资金费率数据
class FundingRateData {
  final String symbol;
  final double fundingRate;
  final double nextFundingRate;
  final DateTime nextFundingTime;
  final DateTime timestamp;
  
  FundingRateData({
    required this.symbol,
    required this.fundingRate,
    required this.nextFundingRate,
    required this.nextFundingTime,
    required this.timestamp,
  });
}

/// 期货特有持仓量数据
class OpenInterestData {
  final String symbol;
  final double openInterest;
  final double openInterestValue;
  final DateTime timestamp;
  
  OpenInterestData({
    required this.symbol,
    required this.openInterest,
    required this.openInterestValue,
    required this.timestamp,
  });
}

/// 期货市场数据（基于现有的MarketData但扩展期货特有功能）
class FuturesMarketData {
  final String symbol;
  final double currentPrice;
  final double previousClose;
  final double high24h;
  final double low24h;
  final double priceChange;
  final double priceChangePercent;
  final double volume24h;
  final double quoteVolume24h;
  final DateTime timestamp;
  
  // 期货特有字段
  final double? fundingRate;
  final double? openInterest;
  final double? indexPrice;
  final double? markPrice;
  
  FuturesMarketData({
    required this.symbol,
    required this.currentPrice,
    required this.previousClose,
    required this.high24h,
    required this.low24h,
    required this.priceChange,
    required this.priceChangePercent,
    required this.volume24h,
    required this.quoteVolume24h,
    required this.timestamp,
    this.fundingRate,
    this.openInterest,
    this.indexPrice,
    this.markPrice,
  });
  
  factory FuturesMarketData.fromJson(Map<String, dynamic> json) {
    return FuturesMarketData(
      symbol: json['symbol'],
      currentPrice: json['current_price'].toDouble(),
      previousClose: json['previous_close'].toDouble(),
      high24h: json['high_24h'].toDouble(),
      low24h: json['low_24h'].toDouble(),
      priceChange: json['price_change'].toDouble(),
      priceChangePercent: json['price_change_percent'].toDouble(),
      volume24h: json['volume_24h'].toDouble(),
      quoteVolume24h: json['quote_volume_24h'].toDouble(),
      timestamp: DateTime.parse(json['timestamp']),
      fundingRate: json['funding_rate']?.toDouble(),
      openInterest: json['open_interest']?.toDouble(),
      indexPrice: json['index_price']?.toDouble(),
      markPrice: json['mark_price']?.toDouble(),
    );
  }
}

/// 期货市场卡片组件
class FuturesMarketCard extends StatelessWidget {
  final FuturesMarketData marketData;
  final FundingRateData? fundingRateData;
  final OpenInterestData? openInterestData;
  final VoidCallback? onTap;
  final bool showFullDetails;
  
  const FuturesMarketCard({
    super.key,
    required this.marketData,
    this.fundingRateData,
    this.openInterestData,
    this.onTap,
    this.showFullDetails = true,
  });

  @override
  Widget build(BuildContext context) {
    final priceChangeColor = marketData.priceChangePercent >= 0 
        ? Colors.green 
        : Colors.red;
    
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
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
                        const SizedBox(height: 4),
                        Text(
                          '\$${_formatPrice(marketData.currentPrice)}',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
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
                          color: priceChangeColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${marketData.priceChange >= 0 ? '+' : ''}\$${_formatPrice(marketData.priceChange)}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: priceChangeColor,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // 期货特有数据区域
              if (showFullDetails && (fundingRateData != null || openInterestData != null))
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.5),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.percent_outlined,
                            size: 16,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '期货特有数据',
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      
                      if (fundingRateData != null) ...[
                        _buildFundingRateInfo(context, fundingRateData!),
                        if (openInterestData != null) const SizedBox(height: 12),
                      ],
                      
                      if (openInterestData != null)
                        _buildOpenInterestInfo(context, openInterestData!),
                    ],
                  ),
                ),
              
              const SizedBox(height: 12),
              
              // 基础市场数据
              Row(
                children: [
                  Expanded(
                    child: _buildInfoItem(
                      context,
                      '24h成交量',
                      _formatVolume(marketData.volume24h),
                      Icons.volume_up_outlined,
                    ),
                  ),
                  Expanded(
                    child: _buildInfoItem(
                      context,
                      '24h最高',
                      '\$${_formatPrice(marketData.high24h)}',
                      Icons.trending_up,
                    ),
                  ),
                  Expanded(
                    child: _buildInfoItem(
                      context,
                      '24h最低',
                      '\$${_formatPrice(marketData.low24h)}',
                      Icons.trending_down,
                    ),
                  ),
                ],
              ),
              
              // 期货特有字段（可选显示）
              if (showFullDetails)
                Column(
                  children: [
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: _buildOptionalInfo(
                            context,
                            '标记价格',
                            marketData.markPrice != null 
                                ? '\$${_formatPrice(marketData.markPrice!)}'
                                : '--',
                            Icons.price_change_outlined,
                          ),
                        ),
                        Expanded(
                          child: _buildOptionalInfo(
                            context,
                            '指数价格',
                            marketData.indexPrice != null 
                                ? '\$${_formatPrice(marketData.indexPrice!)}'
                                : '--',
                            Icons.show_chart,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              
              // 时间戳
              if (showFullDetails) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.access_time,
                      size: 12,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '更新时间: ${DateFormat('HH:mm:ss').format(marketData.timestamp)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
  
  /// 构建资金费率信息
  Widget _buildFundingRateInfo(BuildContext context, FundingRateData data) {
    final isPositive = data.fundingRate >= 0;
    final rateColor = isPositive ? Colors.green : Colors.red;
    final rateIcon = isPositive ? Icons.trending_up : Icons.trending_down;
    
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '资金费率',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Icon(
                    rateIcon,
                    size: 14,
                    color: rateColor,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${(data.fundingRate * 100).toStringAsFixed(4)}%',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: rateColor,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '下次费率',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${(data.nextFundingRate * 100).toStringAsFixed(4)}%',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                DateFormat('HH:mm').format(data.nextFundingTime),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
  
  /// 构建持仓量信息
  Widget _buildOpenInterestInfo(BuildContext context, OpenInterestData data) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '持仓量',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _formatLargeNumber(data.openInterest),
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '持仓价值',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '\$${_formatVolume(data.openInterestValue)}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
  
  /// 构建信息项
  Widget _buildInfoItem(BuildContext context, String label, String value, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 12,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
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
  
  /// 构建可选信息项
  Widget _buildOptionalInfo(BuildContext context, String label, String value, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 12,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
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
  
  /// 格式化价格
  String _formatPrice(double price) {
    if (price >= 1000) {
      return NumberFormat('#,##0.00').format(price);
    } else if (price >= 1) {
      return price.toStringAsFixed(4);
    } else if (price >= 0.01) {
      return price.toStringAsFixed(6);
    } else {
      return price.toStringAsFixed(8);
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
}