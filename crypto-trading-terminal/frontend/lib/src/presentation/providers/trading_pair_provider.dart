import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../domain/entities/trading_pair.dart';
import '../../domain/repositories/trading_pair_repository.dart';
import '../../infrastructure/repositories/trading_pair_repository_impl.dart';

part 'trading_pair_provider.g.dart';

/// 交易对仓库提供器
@Riverpod(keepAlive: true)
TradingPairRepository tradingPairRepository(TradingPairRepositoryRef ref) {
  return TradingPairRepositoryImpl();
}

/// 交易对状态
class TradingPairState {
  final List<TradingPair> tradingPairs;
  final bool isLoading;
  final String? errorMessage;
  final String filterMarketType;
  final String searchQuery;
  final bool filterEnabledOnly;

  const TradingPairState({
    this.tradingPairs = const [],
    this.isLoading = false,
    this.errorMessage,
    this.filterMarketType = 'all',
    this.searchQuery = '',
    this.filterEnabledOnly = false,
  });

  TradingPairState copyWith({
    List<TradingPair>? tradingPairs,
    bool? isLoading,
    String? errorMessage,
    String? filterMarketType,
    String? searchQuery,
    bool? filterEnabledOnly,
  }) {
    return TradingPairState(
      tradingPairs: tradingPairs ?? this.tradingPairs,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      filterMarketType: filterMarketType ?? this.filterMarketType,
      searchQuery: searchQuery ?? this.searchQuery,
      filterEnabledOnly: filterEnabledOnly ?? this.filterEnabledOnly,
    );
  }

  /// 获取过滤后的交易对列表
  List<TradingPair> get filteredTradingPairs {
    var filtered = tradingPairs;

    // 按市场类型过滤
    if (filterMarketType != 'all') {
      final marketType = MarketType.values.firstWhere(
        (e) => e.value == filterMarketType,
        orElse: () => MarketType.spot,
      );
      filtered = filtered.where((pair) => pair.marketType == marketType).toList();
    }

    // 只显示启用的交易对
    if (filterEnabledOnly) {
      filtered = filtered.where((pair) => pair.isTradingEnabled).toList();
    }

    // 按搜索查询过滤
    if (searchQuery.isNotEmpty) {
      final query = searchQuery.toLowerCase();
      filtered = filtered.where((pair) {
        return pair.symbol.toLowerCase().contains(query) ||
               pair.baseAsset.toLowerCase().contains(query) ||
               pair.quoteAsset.toLowerCase().contains(query);
      }).toList();
    }

    return filtered;
  }

  /// 按市场类型分组
  Map<MarketType, List<TradingPair>> get groupedByMarketType {
    final Map<MarketType, List<TradingPair>> groups = {};
    
    for (final pair in filteredTradingPairs) {
      groups.putIfAbsent(pair.marketType, () => []).add(pair);
    }
    
    return groups;
  }

  /// 获取启用交易对数量
  int get enabledPairsCount => tradingPairs.where((p) => p.isTradingEnabled).length;

  /// 获取现货交易对数量
  int get spotPairsCount => tradingPairs.where((p) => p.marketType == MarketType.spot).length;

  /// 获取期货交易对数量
  int get futuresPairsCount => tradingPairs.where((p) => p.marketType == MarketType.futures).length;
}

/// 交易对状态提供器
@RiverpodNotifier
class TradingPairNotifier extends _$TradingPairNotifier {
  @override
  TradingPairState build() {
    return const TradingPairState();
  }

  /// 加载交易对列表
  Future<void> loadTradingPairs() async {
    if (state.isLoading) return;

    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final repository = ref.read(tradingPairRepositoryProvider);
      final tradingPairs = await repository.getTradingPairs();
      
      state = state.copyWith(
        tradingPairs: tradingPairs,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// 获取单个交易对详情
  Future<TradingPair?> getTradingPairById(int tradingPairId) async {
    try {
      // 先从本地缓存查找
      try {
        final localPair = state.tradingPairs.firstWhere(
          (pair) => pair.id == tradingPairId,
        );
        return localPair;
      } catch (e) {
        // 本地缓存中没有，从服务器获取
        final repository = ref.read(tradingPairRepositoryProvider);
        final tradingPair = await repository.getTradingPairById(tradingPairId);
        
        // 更新本地缓存
        final existingPairs = List<TradingPair>.from(state.tradingPairs);
        final existingIndex = existingPairs.indexWhere((p) => p.id == tradingPairId);
        
        if (existingIndex >= 0) {
          existingPairs[existingIndex] = tradingPair;
        } else {
          existingPairs.add(tradingPair);
        }
        
        state = state.copyWith(tradingPairs: existingPairs);
        
        return tradingPair;
      }
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return null;
    }
  }

  /// 根据符号获取交易对
  Future<TradingPair?> getTradingPairBySymbol(String symbol) async {
    try {
      // 先从本地缓存查找
      try {
        final localPair = state.tradingPairs.firstWhere(
          (pair) => pair.symbol == symbol,
        );
        return localPair;
      } catch (e) {
        // 本地缓存中没有，从服务器获取
        final repository = ref.read(tradingPairRepositoryProvider);
        final tradingPair = await repository.getTradingPairBySymbol(symbol);
        
        if (tradingPair != null) {
          // 更新本地缓存
          final existingPairs = List<TradingPair>.from(state.tradingPairs);
          final existingIndex = existingPairs.indexWhere((p) => p.symbol == symbol);
          
          if (existingIndex >= 0) {
            existingPairs[existingIndex] = tradingPair;
          } else {
            existingPairs.add(tradingPair);
          }
          
          state = state.copyWith(tradingPairs: existingPairs);
        }
        
        return tradingPair;
      }
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return null;
    }
  }

  /// 设置市场类型过滤
  void setFilterMarketType(String marketType) {
    state = state.copyWith(filterMarketType: marketType);
  }

  /// 设置搜索查询
  void setSearchQuery(String query) {
    state = state.copyWith(searchQuery: query);
  }

  /// 设置仅显示启用的交易对
  void setFilterEnabledOnly(bool enabledOnly) {
    state = state.copyWith(filterEnabledOnly: enabledOnly);
  }

  /// 清除错误消息
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }

  /// 验证数量是否有效
  bool isValidQuantity(String symbol, double quantity) {
    final pair = state.tradingPairs.firstWhere(
      (p) => p.symbol == symbol,
      orElse: () => throw StateError('Trading pair not found'),
    );
    
    return pair.isValidQuantity(quantity);
  }

  /// 验证价格是否有效
  bool isValidPrice(String symbol, double price) {
    final pair = state.tradingPairs.firstWhere(
      (p) => p.symbol == symbol,
      orElse: () => throw StateError('Trading pair not found'),
    );
    
    return pair.isValidPrice(price);
  }

  /// 格式化数量
  String formatQuantity(String symbol, double quantity) {
    try {
      final pair = state.tradingPairs.firstWhere(
        (p) => p.symbol == symbol,
        orElse: () => throw StateError('Trading pair not found'),
      );
      
      return pair.formatQuantity(quantity);
    } catch (e) {
      return quantity.toString();
    }
  }

  /// 格式化价格
  String formatPrice(String symbol, double price) {
    try {
      final pair = state.tradingPairs.firstWhere(
        (p) => p.symbol == symbol,
        orElse: () => throw StateError('Trading pair not found'),
      );
      
      return pair.formatPrice(price);
    } catch (e) {
      return price.toString();
    }
  }

  /// 获取交易对显示信息
  Map<String, dynamic> getTradingPairInfo(String symbol) {
    try {
      final pair = state.tradingPairs.firstWhere(
        (p) => p.symbol == symbol,
        orElse: () => throw StateError('Trading pair not found'),
      );
      
      return {
        'id': pair.id,
        'symbol': pair.symbol,
        'baseAsset': pair.baseAsset,
        'quoteAsset': pair.quoteAsset,
        'marketType': pair.marketType.value,
        'marketTypeDisplay': pair.marketTypeDisplayText,
        'minQty': pair.minQty,
        'maxQty': pair.maxQty,
        'stepSize': pair.stepSize,
        'minPrice': pair.minPrice,
        'maxPrice': pair.maxPrice,
        'tickSize': pair.tickSize,
        'isTradingEnabled': pair.isTradingEnabled,
        'displayName': pair.displayName,
      };
    } catch (e) {
      return {};
    }
  }

  /// 获取推荐交易对列表（基于用户偏好或热门交易对）
  Future<List<TradingPair>> getRecommendedTradingPairs({int limit = 10}) async {
    try {
      final repository = ref.read(tradingPairRepositoryProvider);
      return await repository.getRecommendedTradingPairs(limit: limit);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return [];
    }
  }

  /// 搜索交易对
  Future<List<TradingPair>> searchTradingPairs(String query) async {
    try {
      final repository = ref.read(tradingPairRepositoryProvider);
      return await repository.searchTradingPairs(query);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return [];
    }
  }

  /// 获取交易对统计信息
  Map<String, int> getTradingPairStatistics() {
    final total = state.tradingPairs.length;
    final enabled = state.tradingPairs.where((p) => p.isTradingEnabled).length;
    final spot = state.tradingPairs.where((p) => p.marketType == MarketType.spot).length;
    final futures = state.tradingPairs.where((p) => p.marketType == MarketType.futures).length;
    
    return {
      'total': total,
      'enabled': enabled,
      'disabled': total - enabled,
      'spot': spot,
      'futures': futures,
    };
  }
}

/// 交易对状态提供器别名
final tradingPairProvider = StateNotifierProvider<TradingPairNotifier, TradingPairState>(
  (ref) => TradingPairNotifier(ref),
);