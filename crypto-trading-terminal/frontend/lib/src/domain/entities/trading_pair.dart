import 'package:equatable/equatable.dart';
import 'auto_order.dart';

/// 交易对实体
class TradingPair extends Equatable {
  final int id;
  final int accountId;
  final String symbol;
  final String baseAsset;
  final String quoteAsset;
  final MarketType marketType;
  final double minQty;
  final double maxQty;
  final double stepSize;
  final double minPrice;
  final double maxPrice;
  final double tickSize;
  final bool isTradingEnabled;
  final DateTime createdAt;
  final DateTime updatedAt;

  const TradingPair({
    required this.id,
    required this.accountId,
    required this.symbol,
    required this.baseAsset,
    required this.quoteAsset,
    required this.marketType,
    required this.minQty,
    required this.maxQty,
    required this.stepSize,
    required this.minPrice,
    required this.maxPrice,
    required this.tickSize,
    this.isTradingEnabled = true,
    required this.createdAt,
    required this.updatedAt,
  });

  @override
  List<Object?> get props => [
    id,
    accountId,
    symbol,
    baseAsset,
    quoteAsset,
    marketType,
    minQty,
    maxQty,
    stepSize,
    minPrice,
    maxPrice,
    tickSize,
    isTradingEnabled,
    createdAt,
    updatedAt,
  ];

  /// 从 JSON 创建实例
  factory TradingPair.fromJson(Map<String, dynamic> json) {
    return TradingPair(
      id: json['id'] as int,
      accountId: json['account_id'] as int,
      symbol: json['symbol'] as String,
      baseAsset: json['base_asset'] as String,
      quoteAsset: json['quote_asset'] as String,
      marketType: MarketType.values.firstWhere(
        (e) => e.value == json['market_type'],
        orElse: () => MarketType.spot,
      ),
      minQty: (json['min_qty'] as num).toDouble(),
      maxQty: (json['max_qty'] as num).toDouble(),
      stepSize: (json['step_size'] as num).toDouble(),
      minPrice: (json['min_price'] as num).toDouble(),
      maxPrice: (json['max_price'] as num).toDouble(),
      tickSize: (json['tick_size'] as num).toDouble(),
      isTradingEnabled: json['is_trading_enabled'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  /// 转换为 JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'account_id': accountId,
      'symbol': symbol,
      'base_asset': baseAsset,
      'quote_asset': quoteAsset,
      'market_type': marketType.value,
      'min_qty': minQty,
      'max_qty': maxQty,
      'step_size': stepSize,
      'min_price': minPrice,
      'max_price': maxPrice,
      'tick_size': tickSize,
      'is_trading_enabled': isTradingEnabled,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// 创建副本
  TradingPair copyWith({
    int? id,
    int? accountId,
    String? symbol,
    String? baseAsset,
    String? quoteAsset,
    MarketType? marketType,
    double? minQty,
    double? maxQty,
    double? stepSize,
    double? minPrice,
    double? maxPrice,
    double? tickSize,
    bool? isTradingEnabled,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return TradingPair(
      id: id ?? this.id,
      accountId: accountId ?? this.accountId,
      symbol: symbol ?? this.symbol,
      baseAsset: baseAsset ?? this.baseAsset,
      quoteAsset: quoteAsset ?? this.quoteAsset,
      marketType: marketType ?? this.marketType,
      minQty: minQty ?? this.minQty,
      maxQty: maxQty ?? this.maxQty,
      stepSize: stepSize ?? this.stepSize,
      minPrice: minPrice ?? this.minPrice,
      maxPrice: maxPrice ?? this.maxPrice,
      tickSize: tickSize ?? this.tickSize,
      isTradingEnabled: isTradingEnabled ?? this.isTradingEnabled,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// 获取显示名称
  String get displayName => symbol;

  /// 获取市场类型显示文本
  String get marketTypeDisplayText {
    switch (marketType) {
      case MarketType.spot:
        return '现货';
      case MarketType.futures:
        return '期货';
    }
  }

  /// 验证数量是否有效
  bool isValidQuantity(double quantity) {
    if (!isTradingEnabled) return false;
    if (quantity < minQty) return false;
    if (quantity > maxQty) return false;
    
    // 检查步长
    final steps = ((quantity - minQty) / stepSize).round();
    return (steps * stepSize + minQty).roundToDouble() == quantity;
  }

  /// 验证价格是否有效
  bool isValidPrice(double price) {
    if (!isTradingEnabled) return false;
    if (price < minPrice) return false;
    if (price > maxPrice) return false;
    
    // 检查价格精度
    final priceSteps = ((price - minPrice) / tickSize).round();
    return (priceSteps * tickSize + minPrice).roundToDouble() == price;
  }

  /// 格式化数量
  String formatQuantity(double quantity) {
    if (quantity >= 1) {
      return quantity.toStringAsFixed(quantity < 10 ? 4 : 2);
    } else if (quantity >= 0.01) {
      return quantity.toStringAsFixed(4);
    } else {
      return quantity.toStringAsFixed(8);
    }
  }

  /// 格式化价格
  String formatPrice(double price) {
    if (price >= 1000) {
      return price.toStringAsFixed(2);
    } else if (price >= 1) {
      return price.toStringAsFixed(4);
    } else {
      return price.toStringAsFixed(8);
    }
  }
}

/// 市场数据实体
class MarketData extends Equatable {
  final int id;
  final int accountId;
  final int tradingPairId;
  final String symbol;
  final double currentPrice;
  final double previousClose;
  final double high24h;
  final double low24h;
  final double priceChange;
  final double priceChangePercent;
  final double volume24h;
  final double quoteVolume24h;
  final double? fundingRate;
  final double? openInterest;
  final double? indexPrice;
  final double? markPrice;
  final DateTime timestamp;
  final String exchange;
  final String marketType;
  final DateTime createdAt;

  const MarketData({
    required this.id,
    required this.accountId,
    required this.tradingPairId,
    required this.symbol,
    required this.currentPrice,
    required this.previousClose,
    required this.high24h,
    required this.low24h,
    required this.priceChange,
    required this.priceChangePercent,
    required this.volume24h,
    required this.quoteVolume24h,
    this.fundingRate,
    this.openInterest,
    this.indexPrice,
    this.markPrice,
    required this.timestamp,
    required this.exchange,
    required this.marketType,
    required this.createdAt,
  });

  @override
  List<Object?> get props => [
    id,
    accountId,
    tradingPairId,
    symbol,
    currentPrice,
    previousClose,
    high24h,
    low24h,
    priceChange,
    priceChangePercent,
    volume24h,
    quoteVolume24h,
    fundingRate,
    openInterest,
    indexPrice,
    markPrice,
    timestamp,
    exchange,
    marketType,
    createdAt,
  ];

  /// 从 JSON 创建实例
  factory MarketData.fromJson(Map<String, dynamic> json) {
    return MarketData(
      id: json['id'] as int,
      accountId: json['account_id'] as int,
      tradingPairId: json['trading_pair_id'] as int,
      symbol: json['symbol'] as String,
      currentPrice: (json['current_price'] as num).toDouble(),
      previousClose: (json['previous_close'] as num).toDouble(),
      high24h: (json['high_24h'] as num).toDouble(),
      low24h: (json['low_24h'] as num).toDouble(),
      priceChange: (json['price_change'] as num).toDouble(),
      priceChangePercent: (json['price_change_percent'] as num).toDouble(),
      volume24h: (json['volume_24h'] as num).toDouble(),
      quoteVolume24h: (json['quote_volume_24h'] as num).toDouble(),
      fundingRate: json['funding_rate']?.toDouble(),
      openInterest: json['open_interest']?.toDouble(),
      indexPrice: json['index_price']?.toDouble(),
      markPrice: json['mark_price']?.toDouble(),
      timestamp: DateTime.parse(json['timestamp'] as String),
      exchange: json['exchange'] as String,
      marketType: json['market_type'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  /// 转换为 JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'account_id': accountId,
      'trading_pair_id': tradingPairId,
      'symbol': symbol,
      'current_price': currentPrice,
      'previous_close': previousClose,
      'high_24h': high24h,
      'low_24h': low24h,
      'price_change': priceChange,
      'price_change_percent': priceChangePercent,
      'volume_24h': volume24h,
      'quote_volume_24h': quoteVolume24h,
      'funding_rate': fundingRate,
      'open_interest': openInterest,
      'index_price': indexPrice,
      'mark_price': markPrice,
      'timestamp': timestamp.toIso8601String(),
      'exchange': exchange,
      'market_type': marketType,
      'created_at': createdAt.toIso8601String(),
    };
  }

  /// 获取涨跌颜色
  String get changeColor {
    if (priceChange > 0) return 'green';
    if (priceChange < 0) return 'red';
    return 'grey';
  }

  /// 获取涨跌图标
  String get changeIcon {
    if (priceChange > 0) return 'arrow_upward';
    if (priceChange < 0) return 'arrow_downward';
    return 'remove';
  }

  /// 格式化价格变化
  String formatPriceChange() {
    final sign = priceChange > 0 ? '+' : '';
    return '$sign${priceChange.toStringAsFixed(4)} ($sign${priceChangePercent.toStringAsFixed(2)}%)';
  }

  /// 格式化交易量
  String formatVolume() {
    if (volume24h >= 1000000) {
      return '${(volume24h / 1000000).toStringAsFixed(2)}M';
    } else if (volume24h >= 1000) {
      return '${(volume24h / 1000).toStringAsFixed(2)}K';
    } else {
      return volume24h.toStringAsFixed(2);
    }
  }
}