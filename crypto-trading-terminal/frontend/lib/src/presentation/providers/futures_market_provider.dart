import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;

/// 期货特有资金费率数据模型
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
  
  factory FundingRateData.fromJson(Map<String, dynamic> json) {
    return FundingRateData(
      symbol: json['symbol'],
      fundingRate: json['funding_rate'].toDouble(),
      nextFundingRate: json['next_funding_rate'].toDouble(),
      nextFundingTime: DateTime.parse(json['next_funding_time']),
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
}

/// 期货特有持仓量数据模型
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
  
  factory OpenInterestData.fromJson(Map<String, dynamic> json) {
    return OpenInterestData(
      symbol: json['symbol'],
      openInterest: json['open_interest'].toDouble(),
      openInterestValue: json['open_interest_value'].toDouble(),
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
}

/// 期货市场数据状态
class FuturesMarketDataState {
  final List<MarketData> marketData;
  final List<MarketData> sortedMarketData;
  final Map<String, FundingRateData> fundingRates;
  final Map<String, OpenInterestData> openInterests;
  final String exchange;
  final MarketType marketType;
  final bool isLoading;
  final bool autoRefresh;
  final String? error;
  final DateTime? lastUpdateTime;
  final Duration? wsLatency;
  final WebSocketConnectionState wsConnectionState;
  final String? wsError;
  final bool realtimeDataEnabled;
  final SortField sortField;
  final SortDirection sortDirection;
  
  const FuturesMarketDataState({
    this.marketData = const [],
    this.sortedMarketData = const [],
    this.fundingRates = const {},
    this.openInterests = const {},
    this.exchange = 'binance',
    this.marketType = MarketType.futures,
    this.isLoading = false,
    this.autoRefresh = true,
    this.error,
    this.lastUpdateTime,
    this.wsLatency,
    this.wsConnectionState = WebSocketConnectionState.disconnected,
    this.wsError,
    this.realtimeDataEnabled = false,
    this.sortField = SortField.volume,
    this.sortDirection = SortDirection.descending,
  });
  
  FuturesMarketDataState copyWith({
    List<MarketData>? marketData,
    List<MarketData>? sortedMarketData,
    Map<String, FundingRateData>? fundingRates,
    Map<String, OpenInterestData>? openInterests,
    String? exchange,
    MarketType? marketType,
    bool? isLoading,
    bool? autoRefresh,
    String? error,
    DateTime? lastUpdateTime,
    Duration? wsLatency,
    WebSocketConnectionState? wsConnectionState,
    String? wsError,
    bool? realtimeDataEnabled,
    SortField? sortField,
    SortDirection? sortDirection,
  }) {
    return FuturesMarketDataState(
      marketData: marketData ?? this.marketData,
      sortedMarketData: sortedMarketData ?? this.sortedMarketData,
      fundingRates: fundingRates ?? this.fundingRates,
      openInterests: openInterests ?? this.openInterests,
      exchange: exchange ?? this.exchange,
      marketType: marketType ?? this.marketType,
      isLoading: isLoading ?? this.isLoading,
      autoRefresh: autoRefresh ?? this.autoRefresh,
      error: error,
      lastUpdateTime: lastUpdateTime ?? this.lastUpdateTime,
      wsLatency: wsLatency,
      wsConnectionState: wsConnectionState ?? this.wsConnectionState,
      wsError: wsError,
      realtimeDataEnabled: realtimeDataEnabled ?? this.realtimeDataEnabled,
      sortField: sortField ?? this.sortField,
      sortDirection: sortDirection ?? this.sortDirection,
    );
  }
  
  /// 获取连接状态颜色
  String getConnectionStatusColor() {
    switch (wsConnectionState) {
      case WebSocketConnectionState.connected:
        return '#4CAF50'; // 绿色
      case WebSocketConnectionState.connecting:
      case WebSocketConnectionState.reconnecting:
        return '#FF9800'; // 橙色
      case WebSocketConnectionState.error:
      case WebSocketConnectionState.disconnected:
        return '#F44336'; // 红色
    }
  }
  
  /// 获取连接状态描述
  String getConnectionStatusDescription() {
    switch (wsConnectionState) {
      case WebSocketConnectionState.connected:
        return '已连接';
      case WebSocketConnectionState.connecting:
        return '连接中';
      case WebSocketConnectionState.reconnecting:
        return '重连中';
      case WebSocketConnectionState.error:
        return '连接错误';
      case WebSocketConnectionState.disconnected:
        return '未连接';
    }
  }
  
  /// 获取按涨跌幅排序的前5个涨幅
  List<MarketData> get topGainers {
    final gainers = marketData.where((item) => item.priceChangePercent > 0).toList();
    gainers.sort((a, b) => b.priceChangePercent.compareTo(a.priceChangePercent));
    return gainers.take(5).toList();
  }
  
  /// 获取按涨跌幅排序的前5个跌幅
  List<MarketData> get topLosers {
    final losers = marketData.where((item) => item.priceChangePercent < 0).toList();
    losers.sort((a, b) => a.priceChangePercent.compareTo(b.priceChangePercent));
    return losers.take(5).toList();
  }
}

/// 期货市场数据Provider
class FuturesMarketProvider extends StateNotifier<FuturesMarketDataState> {
  FuturesMarketProvider() : super(FuturesMarketDataState()) {
    _initializeProvider();
  }
  
  static const String baseUrl = 'http://localhost:8000/api/v1';
  static const String wsUrl = 'ws://localhost:8000/api/v1/market';
  
  WebSocketChannel? _channel;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  final int _maxReconnectAttempts = 5;
  final Duration _reconnectDelay = const Duration(seconds: 3);
  final Duration _heartbeatInterval = const Duration(seconds: 30);
  
  /// 初始化Provider
  void _initializeProvider() {
    // 启动心跳检测
    _startHeartbeat();
  }
  
  /// 获取WebSocket URL
  String _getWebSocketUrl() {
    return '$wsUrl/futures/ws';
  }
  
  /// 启动WebSocket连接
  Future<void> connectWebSocket() async {
    if (state.wsConnectionState == WebSocketConnectionState.connected ||
        state.wsConnectionState == WebSocketConnectionState.connecting) {
      return; // 已经连接或正在连接中
    }
    
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.connecting,
      wsError: null,
    );
    
    try {
      final url = _getWebSocketUrl();
      _channel = WebSocketChannel.connect(Uri.parse(url));
      
      _channel!.stream.listen(
        (data) => _handleWebSocketMessage(data),
        onDone: () => _handleWebSocketDisconnected(),
        onError: (error) => _handleWebSocketError(error),
        cancelOnError: true,
      );
      
      state = state.copyWith(
        wsConnectionState: WebSocketConnectionState.connected,
        wsError: null,
      );
      
    } catch (e) {
      _handleWebSocketError(e);
    }
  }
  
  /// 断开WebSocket连接
  void disconnectWebSocket() {
    _channel?.close();
    _channel = null;
    
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.disconnected,
      wsError: null,
    );
  }
  
  /// 处理WebSocket消息
  void _handleWebSocketMessage(dynamic data) {
    try {
      final jsonData = json.decode(data as String);
      
      // 更新延迟时间
      final now = DateTime.now();
      if (state.lastUpdateTime != null) {
        final latency = now.difference(state.lastUpdateTime!);
        state = state.copyWith(
          wsLatency: latency,
          lastUpdateTime: now,
        );
      } else {
        state = state.copyWith(lastUpdateTime: now);
      }
      
      // 解析市场数据消息
      if (jsonData['type'] == 'ticker') {
        _updateMarketDataFromWebSocket(jsonData);
      }
      
    } catch (e) {
      debugPrint('解析WebSocket消息失败: $e');
    }
  }
  
  /// 处理WebSocket断开连接
  void _handleWebSocketDisconnected() {
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.disconnected,
    );
    
    // 自动重连
    if (state.realtimeDataEnabled) {
      _scheduleReconnect();
    }
  }
  
  /// 处理WebSocket错误
  void _handleWebSocketError(dynamic error) {
    debugPrint('WebSocket错误: $error');
    
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.error,
      wsError: error.toString(),
    );
    
    // 自动重连
    if (state.realtimeDataEnabled) {
      _scheduleReconnect();
    }
  }
  
  /// 安排重连
  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(_reconnectDelay, () {
      if (state.realtimeDataEnabled && 
          state.wsConnectionState != WebSocketConnectionState.connected) {
        connectWebSocket();
      }
    });
  }
  
  /// 启动心跳检测
  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (state.realtimeDataEnabled && 
          state.wsConnectionState == WebSocketConnectionState.connected) {
        // 发送心跳
        _channel?.sink.add(json.encode({
          'type': 'ping',
          'timestamp': DateTime.now().millisecondsSinceEpoch,
        }));
      }
    });
  }
  
  /// 从WebSocket更新市场数据
  void _updateMarketDataFromWebSocket(Map<String, dynamic> jsonData) {
    try {
      final symbol = jsonData['symbol'];
      final index = state.marketData.indexWhere((item) => item.symbol == symbol);
      
      final updatedData = MarketData(
        symbol: jsonData['symbol'],
        currentPrice: jsonData['price'].toDouble(),
        previousClose: jsonData['price'].toDouble() - (jsonData['change']?.toDouble() ?? 0),
        high24h: jsonData['high'].toDouble(),
        low24h: jsonData['low'].toDouble(),
        priceChange: jsonData['change']?.toDouble() ?? 0,
        priceChangePercent: jsonData['change_percent']?.toDouble() ?? 0,
        volume24h: jsonData['volume'].toDouble(),
        quoteVolume24h: (jsonData['price'].toDouble() * jsonData['volume'].toDouble()),
        timestamp: DateTime.fromMillisecondsSinceEpoch(jsonData['timestamp'] ?? DateTime.now().millisecondsSinceEpoch),
        fundingRate: jsonData['funding_rate']?.toDouble(),
        openInterest: jsonData['open_interest']?.toDouble(),
        indexPrice: jsonData['index_price']?.toDouble(),
        markPrice: jsonData['mark_price']?.toDouble(),
      );
      
      if (index >= 0) {
        // 更新现有数据
        final newMarketData = [...state.marketData];
        newMarketData[index] = updatedData;
        state = state.copyWith(
          marketData: newMarketData,
          sortedMarketData: _sortMarketData(newMarketData),
        );
      }
      
    } catch (e) {
      debugPrint('更新市场数据失败: $e');
    }
  }
  
  /// 排序市场数据
  List<MarketData> _sortMarketData(List<MarketData> data) {
    final sortedData = [...data];
    
    sortedData.sort((a, b) {
      switch (state.sortField) {
        case SortField.symbol:
          return state.sortDirection == SortDirection.ascending
              ? a.symbol.compareTo(b.symbol)
              : b.symbol.compareTo(a.symbol);
        case SortField.price:
          return state.sortDirection == SortDirection.ascending
              ? a.currentPrice.compareTo(b.currentPrice)
              : b.currentPrice.compareTo(a.currentPrice);
        case SortField.change:
          return state.sortDirection == SortDirection.ascending
              ? a.priceChangePercent.compareTo(b.priceChangePercent)
              : b.priceChangePercent.compareTo(a.priceChangePercent);
        case SortField.volume:
          return state.sortDirection == SortDirection.ascending
              ? a.volume24h.compareTo(b.volume24h)
              : b.volume24h.compareTo(a.volume24h);
      }
    });
    
    return sortedData;
  }
  
  /// 手动刷新数据
  Future<void> manualRefresh() async {
    await fetchMarketData();
  }
  
  /// 自动刷新数据
  Timer? _autoRefreshTimer;
  void startAutoRefresh() {
    state = state.copyWith(autoRefresh: true);
    
    _autoRefreshTimer?.cancel();
    _autoRefreshTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (state.autoRefresh && !state.realtimeDataEnabled) {
        fetchMarketData();
      }
    });
  }
  
  void stopAutoRefresh() {
    state = state.copyWith(autoRefresh: false);
    _autoRefreshTimer?.cancel();
  }
  
  /// 获取市场数据
  Future<void> fetchMarketData() async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      // 获取市场数据
      await _fetchFuturesMarketData();
      
      // 获取资金费率数据
      await _fetchFundingRates();
      
      // 获取持仓量数据
      await _fetchOpenInterests();
      
    } catch (e) {
      state = state.copyWith(
        error: '获取数据失败: $e',
        isLoading: false,
      );
    }
  }
  
  /// 获取期货市场数据
  Future<void> _fetchFuturesMarketData() async {
    final symbols = ['BTCUSDT-PERP', 'ETHUSDT-PERP', 'BNBUSDT-PERP', 'ADAUSDT-PERP', 'SOLUSDT-PERP'];
    
    final uri = Uri.parse('$baseUrl/futures/tickers?symbols=${symbols.join(',')}&exchange=${state.exchange}');
    final response = await http.get(uri);
    
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      final marketData = data.map((json) => MarketData.fromJson(json)).toList();
      
      state = state.copyWith(
        marketData: marketData,
        sortedMarketData: _sortMarketData(marketData),
        isLoading: false,
        lastUpdateTime: DateTime.now(),
      );
    } else {
      throw Exception('HTTP ${response.statusCode}: ${response.body}');
    }
  }
  
  /// 获取资金费率数据
  Future<void> _fetchFundingRates() async {
    final symbols = ['BTCUSDT-PERP', 'ETHUSDT-PERP', 'BNBUSDT-PERP'];
    
    final Map<String, FundingRateData> fundingRates = {};
    
    for (final symbol in symbols) {
      try {
        final uri = Uri.parse('$baseUrl/futures/funding-rate?symbol=$symbol&exchange=${state.exchange}');
        final response = await http.get(uri);
        
        if (response.statusCode == 200) {
          final jsonData = json.decode(response.body);
          fundingRates[symbol] = FundingRateData.fromJson(jsonData);
        }
      } catch (e) {
        debugPrint('获取资金费率失败 $symbol: $e');
      }
    }
    
    state = state.copyWith(fundingRates: fundingRates);
  }
  
  /// 获取持仓量数据
  Future<void> _fetchOpenInterests() async {
    final symbols = ['BTCUSDT-PERP', 'ETHUSDT-PERP', 'BNBUSDT-PERP'];
    
    final Map<String, OpenInterestData> openInterests = {};
    
    for (final symbol in symbols) {
      try {
        final uri = Uri.parse('$baseUrl/futures/open-interest?symbol=$symbol&exchange=${state.exchange}');
        final response = await http.get(uri);
        
        if (response.statusCode == 200) {
          final jsonData = json.decode(response.body);
          openInterests[symbol] = OpenInterestData.fromJson(jsonData);
        }
      } catch (e) {
        debugPrint('获取持仓量失败 $symbol: $e');
      }
    }
    
    state = state.copyWith(openInterests: openInterests);
  }
  
  /// 设置排序
  void setSorting(SortField sortField, SortDirection direction) {
    state = state.copyWith(
      sortField: sortField,
      sortDirection: direction,
      sortedMarketData: _sortMarketData(state.marketData),
    );
  }
  
  /// 启用实时数据
  void enableRealtimeData() {
    state = state.copyWith(realtimeDataEnabled: true);
    connectWebSocket();
  }
  
  /// 禁用实时数据
  void disableRealtimeData() {
    state = state.copyWith(realtimeDataEnabled: false);
    disconnectWebSocket();
  }
  
  /// 设置交易所
  void setExchange(String exchange) {
    state = state.copyWith(exchange: exchange);
    manualRefresh();
  }
  
  @override
  void dispose() {
    _autoRefreshTimer?.cancel();
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    disconnectWebSocket();
    super.dispose();
  }
}

/// Provider实例
final futuresMarketProvider = StateNotifierProvider<FuturesMarketProvider, FuturesMarketDataState>(
  (ref) => FuturesMarketProvider(),
);