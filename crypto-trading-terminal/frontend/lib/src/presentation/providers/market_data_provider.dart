import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;

/// 市场数据类型
enum MarketType { spot, futures }

/// WebSocket连接状态
enum WebSocketConnectionState {
  disconnected,
  connecting,
  connected,
  error,
  reconnecting,
}

/// 排序类型
enum SortField { price, change, volume, symbol }

/// 排序方向
enum SortDirection { ascending, descending }

/// 市场数据模型
class MarketData {
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
  
  MarketData({
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
  
  factory MarketData.fromJson(Map<String, dynamic> json) {
    return MarketData(
      symbol: json['symbol'],
      currentPrice: (json['current_price'] as num).toDouble(),
      previousClose: (json['previous_close'] as num).toDouble(),
      high24h: (json['high_24h'] as num).toDouble(),
      low24h: (json['low_24h'] as num).toDouble(),
      priceChange: (json['price_change'] as num).toDouble(),
      priceChangePercent: (json['price_change_percent'] as num).toDouble(),
      volume24h: (json['volume_24h'] as num).toDouble(),
      quoteVolume24h: (json['quote_volume_24h'] as num).toDouble(),
      timestamp: DateTime.parse(json['timestamp']),
      fundingRate: json['funding_rate'] != null ? (json['funding_rate'] as num).toDouble() : null,
      openInterest: json['open_interest'] != null ? (json['open_interest'] as num).toDouble() : null,
      indexPrice: json['index_price'] != null ? (json['index_price'] as num).toDouble() : null,
      markPrice: json['mark_price'] != null ? (json['mark_price'] as num).toDouble() : null,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'current_price': currentPrice,
      'previous_close': previousClose,
      'high_24h': high24h,
      'low_24h': low24h,
      'price_change': priceChange,
      'price_change_percent': priceChangePercent,
      'volume_24h': volume24h,
      'quote_volume_24h': quoteVolume24h,
      'timestamp': timestamp.toIso8601String(),
      if (fundingRate != null) 'funding_rate': fundingRate,
      if (openInterest != null) 'open_interest': openInterest,
      if (indexPrice != null) 'index_price': indexPrice,
      if (markPrice != null) 'mark_price': markPrice,
    };
  }
  
  /// 复制MarketData对象
  MarketData copyWith({
    String? symbol,
    double? currentPrice,
    double? previousClose,
    double? high24h,
    double? low24h,
    double? priceChange,
    double? priceChangePercent,
    double? volume24h,
    double? quoteVolume24h,
    DateTime? timestamp,
    double? fundingRate,
    double? openInterest,
    double? indexPrice,
    double? markPrice,
  }) {
    return MarketData(
      symbol: symbol ?? this.symbol,
      currentPrice: currentPrice ?? this.currentPrice,
      previousClose: previousClose ?? this.previousClose,
      high24h: high24h ?? this.high24h,
      low24h: low24h ?? this.low24h,
      priceChange: priceChange ?? this.priceChange,
      priceChangePercent: priceChangePercent ?? this.priceChangePercent,
      volume24h: volume24h ?? this.volume24h,
      quoteVolume24h: quoteVolume24h ?? this.quoteVolume24h,
      timestamp: timestamp ?? this.timestamp,
      fundingRate: fundingRate ?? this.fundingRate,
      openInterest: openInterest ?? this.openInterest,
      indexPrice: indexPrice ?? this.indexPrice,
      markPrice: markPrice ?? this.markPrice,
    );
  }
  
  /// 格式化的价格字符串
  String get formattedPrice {
    if (currentPrice >= 1) {
      return currentPrice.toStringAsFixed(2);
    } else if (currentPrice >= 0.01) {
      return currentPrice.toStringAsFixed(4);
    } else {
      return currentPrice.toStringAsFixed(6);
    }
  }
  
  /// 格式化的24h交易量字符串
  String get formattedVolume {
    if (volume24h >= 1e9) {
      return '${(volume24h / 1e9).toStringAsFixed(1)}B';
    } else if (volume24h >= 1e6) {
      return '${(volume24h / 1e6).toStringAsFixed(1)}M';
    } else if (volume24h >= 1e3) {
      return '${(volume24h / 1e3).toStringAsFixed(1)}K';
    } else {
      return volume24h.toStringAsFixed(0);
    }
  }
  
  /// 格式化的涨跌幅百分比字符串
  String get formattedChange {
    final sign = priceChangePercent >= 0 ? '+' : '';
    return '$sign${priceChangePercent.toStringAsFixed(2)}%';
  }
  
  /// 涨跌幅颜色
  String get changeColorHex {
    if (priceChangePercent > 0) {
      return '#4CAF50'; // 绿色
    } else if (priceChangePercent < 0) {
      return '#F44336'; // 红色
    } else {
      return '#9E9E9E'; // 灰色
    }
  }
}

/// MarketDataProvider状态
class MarketDataState {
  final List<MarketData> marketData;
  final bool isLoading;
  final String? error;
  final String exchange;
  final MarketType marketType;
  final SortField sortField;
  final SortDirection sortDirection;
  final bool autoRefresh;
  final Duration refreshInterval;
  final Timer? refreshTimer;
  
  // WebSocket相关状态
  final WebSocketConnectionState wsConnectionState;
  final String? wsError;
  final int connectionAttempts;
  final bool realtimeDataEnabled;
  final DateTime? lastUpdateTime;
  final Duration? wsLatency;
  
  MarketDataState({
    this.marketData = const [],
    this.isLoading = false,
    this.error,
    this.exchange = 'binance',
    this.marketType = MarketType.spot,
    this.sortField = SortField.price,
    this.sortDirection = SortDirection.descending,
    this.autoRefresh = false,
    this.refreshInterval = const Duration(seconds: 5),
    this.refreshTimer,
    this.wsConnectionState = WebSocketConnectionState.disconnected,
    this.wsError,
    this.connectionAttempts = 0,
    this.realtimeDataEnabled = false,
    this.lastUpdateTime,
    this.wsLatency,
  });
  
  MarketDataState copyWith({
    List<MarketData>? marketData,
    bool? isLoading,
    String? error,
    String? exchange,
    MarketType? marketType,
    SortField? sortField,
    SortDirection? sortDirection,
    bool? autoRefresh,
    Duration? refreshInterval,
    Timer? refreshTimer,
    WebSocketConnectionState? wsConnectionState,
    String? wsError,
    int? connectionAttempts,
    bool? realtimeDataEnabled,
    DateTime? lastUpdateTime,
    Duration? wsLatency,
  }) {
    return MarketDataState(
      marketData: marketData ?? this.marketData,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      exchange: exchange ?? this.exchange,
      marketType: marketType ?? this.marketType,
      sortField: sortField ?? this.sortField,
      sortDirection: sortDirection ?? this.sortDirection,
      autoRefresh: autoRefresh ?? this.autoRefresh,
      refreshInterval: refreshInterval ?? this.refreshInterval,
      refreshTimer: refreshTimer ?? this.refreshTimer,
      wsConnectionState: wsConnectionState ?? this.wsConnectionState,
      wsError: wsError,
      connectionAttempts: connectionAttempts ?? this.connectionAttempts,
      realtimeDataEnabled: realtimeDataEnabled ?? this.realtimeDataEnabled,
      lastUpdateTime: lastUpdateTime ?? this.lastUpdateTime,
      wsLatency: wsLatency,
    );
  }
  
  /// 获取排序后的市场数据
  List<MarketData> get sortedMarketData {
    final sorted = [...marketData];
    sorted.sort((a, b) {
      int comparison;
      switch (sortField) {
        case SortField.price:
          comparison = a.currentPrice.compareTo(b.currentPrice);
          break;
        case SortField.change:
          comparison = a.priceChangePercent.compareTo(b.priceChangePercent);
          break;
        case SortField.volume:
          comparison = a.volume24h.compareTo(b.volume24h);
          break;
        case SortField.symbol:
          comparison = a.symbol.compareTo(b.symbol);
          break;
      }
      return sortDirection == SortDirection.descending ? -comparison : comparison;
    });
    return sorted;
  }
  
  /// 获取热门上涨交易对
  List<MarketData> get topGainers {
    final gainers = marketData.where((data) => data.priceChangePercent > 0).toList();
    gainers.sort((a, b) => b.priceChangePercent.compareTo(a.priceChangePercent));
    return gainers;
  }
  
  /// 获取热门下跌交易对
  List<MarketData> get topLosers {
    final losers = marketData.where((data) => data.priceChangePercent < 0).toList();
    losers.sort((a, b) => a.priceChangePercent.compareTo(b.priceChangePercent));
    return losers;
  }
}

/// MarketDataProvider
class MarketDataProvider extends StateNotifier<MarketDataState> {
  MarketDataProvider() : super(MarketDataState()) {
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
    return '$wsUrl/${state.marketType.name}/ws';
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
        onError: (error) => _handleWebSocketError(error),
        onDone: _handleWebSocketDisconnected,
        cancelOnError: true,
      );
      
      state = state.copyWith(
        wsConnectionState: WebSocketConnectionState.connected,
        wsError: null,
        connectionAttempts: 0,
        realtimeDataEnabled: true,
      );
      
      _startHeartbeat();
      
      // 发送订阅消息
      _subscribeToMarketData();
      
    } catch (e) {
      _handleWebSocketError(e);
    }
  }
  
  /// 断开WebSocket连接
  void disconnectWebSocket() {
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    
    _channel?.sink.close(ws_status.normalClosure);
    _channel = null;
    
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.disconnected,
      realtimeDataEnabled: false,
    );
  }
  
  /// 处理WebSocket消息
  void _handleWebSocketMessage(dynamic data) {
    try {
      final message = json.decode(data as String) as Map<String, dynamic>;
      
      final messageType = message['type'] as String?;
      
      switch (messageType) {
        case 'heartbeat':
          _handleHeartbeatResponse();
          break;
        case 'data':
          _handleMarketDataUpdate(message['data']);
          break;
        case 'order_update':
          // 处理订单更新
          break;
        case 'trade_update':
          // 处理交易更新
          break;
        case 'error':
          _handleWebSocketError(message['error']);
          break;
        default:
          if (kDebugMode) {
            print('未知的WebSocket消息类型: $messageType');
          }
      }
    } catch (e) {
      if (kDebugMode) {
        print('WebSocket消息解析失败: $e');
      }
    }
  }
  
  /// 处理市场数据更新
  void _handleMarketDataUpdate(Map<String, dynamic>? data) {
    if (data == null) return;
    
    try {
      final marketData = MarketData.fromJson(data);
      final currentTime = DateTime.now();
      
      // 更新市场数据
      final updatedMarketData = [...state.marketData];
      final existingIndex = updatedMarketData.indexWhere(
        (item) => item.symbol == marketData.symbol,
      );
      
      if (existingIndex >= 0) {
        updatedMarketData[existingIndex] = marketData;
      } else {
        updatedMarketData.add(marketData);
      }
      
      state = state.copyWith(
        marketData: updatedMarketData,
        lastUpdateTime: currentTime,
      );
      
    } catch (e) {
      if (kDebugMode) {
        print('市场数据更新失败: $e');
      }
    }
  }
  
  /// 处理WebSocket错误
  void _handleWebSocketError(dynamic error) {
    final errorMessage = error.toString();
    
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.error,
      wsError: errorMessage,
    );
    
    if (kDebugMode) {
      print('WebSocket错误: $errorMessage');
    }
    
    // 开始重连
    _startReconnection();
  }
  
  /// 处理WebSocket断开连接
  void _handleWebSocketDisconnected() {
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.disconnected,
      realtimeDataEnabled: false,
    );
    
    if (state.realtimeDataEnabled) {
      _startReconnection();
    }
  }
  
  /// 开始重连
  void _startReconnection() {
    if (state.connectionAttempts >= _maxReconnectAttempts) {
      state = state.copyWith(
        wsConnectionState: WebSocketConnectionState.error,
        wsError: '达到最大重连次数，请检查网络连接',
      );
      return;
    }
    
    _reconnectTimer?.cancel();
    
    final nextAttempt = state.connectionAttempts + 1;
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.reconnecting,
      connectionAttempts: nextAttempt,
    );
    
    _reconnectTimer = Timer(_reconnectDelay, () {
      if (kDebugMode) {
        print('尝试WebSocket重连 (第${nextAttempt}次)');
      }
      connectWebSocket();
    });
  }
  
  /// 订阅市场数据
  void _subscribeToMarketData() {
    if (_channel == null) return;
    
    final subscribeMessage = {
      'type': 'subscribe',
      'data': {
        'type': 'market_data',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'],
        'exchange': state.exchange,
      },
    };
    
    _channel!.sink.add(json.encode(subscribeMessage));
  }
  
  /// 取消订阅市场数据
  void _unsubscribeFromMarketData() {
    if (_channel == null) return;
    
    final unsubscribeMessage = {
      'type': 'unsubscribe',
      'data': {
        'type': 'market_data',
        'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'],
        'exchange': state.exchange,
      },
    };
    
    _channel!.sink.add(json.encode(unsubscribeMessage));
  }
  
  /// 启动心跳
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) {
      if (state.wsConnectionState == WebSocketConnectionState.connected) {
        _sendHeartbeat();
      }
    });
  }
  
  /// 发送心跳
  void _sendHeartbeat() {
    if (_channel == null) return;
    
    final heartbeatMessage = {
      'type': 'heartbeat',
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    final startTime = DateTime.now();
    
    _channel!.sink.add(json.encode(heartbeatMessage));
    
    // 设置超时检测
    Timer(const Duration(seconds: 10), () {
      final latency = DateTime.now().difference(startTime);
      state = state.copyWith(wsLatency: latency);
    });
  }
  
  /// 处理心跳响应
  void _handleHeartbeatResponse() {
    final latency = state.wsLatency;
    if (kDebugMode && latency != null) {
      print('WebSocket心跳响应延迟: ${latency.inMilliseconds}ms');
    }
  }
  
  /// 启用/禁用实时数据
  void setRealtimeDataEnabled(bool enabled) {
    if (enabled && state.wsConnectionState != WebSocketConnectionState.connected) {
      connectWebSocket();
    } else if (!enabled && state.wsConnectionState == WebSocketConnectionState.connected) {
      _unsubscribeFromMarketData();
    }
    
    state = state.copyWith(realtimeDataEnabled: enabled);
  }
  
  /// 重置连接状态
  void resetConnectionState() {
    _reconnectTimer?.cancel();
    disconnectWebSocket();
    
    state = state.copyWith(
      wsConnectionState: WebSocketConnectionState.disconnected,
      wsError: null,
      connectionAttempts: 0,
    );
  }
  
  /// 获取市场数据
  Future<void> fetchMarketData({
    List<String>? symbols,
    String? exchange,
    MarketType? marketType,
  }) async {
    state = state.copyWith(
      isLoading: true,
      error: null,
      exchange: exchange ?? state.exchange,
      marketType: marketType ?? state.marketType,
    );
    
    try {
      final exchangeParam = state.exchange;
      final symbolsQuery = symbols != null 
          ? symbols.map((s) => 'symbols=$s').join('&')
          : '';
      
      final uri = Uri.parse(
        '$baseUrl/market/${state.marketType.name}/tickers'
      ).replace(
        queryParameters: {
          if (symbols != null) 'symbols': symbols,
          'exchange': state.exchange,
        },
      );
      
      final response = await http.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as List;
        final marketData = jsonData
            .map((json) => MarketData.fromJson(json as Map<String, dynamic>))
            .toList();
        
        final currentTime = DateTime.now();
        
        state = state.copyWith(
          marketData: marketData,
          isLoading: false,
          lastUpdateTime: currentTime,
        );
      } else {
        throw Exception('API请求失败: ${response.statusCode}');
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: '获取市场数据失败: $e',
      );
    }
  }
  
  /// 设置排序
  void setSorting(SortField field, SortDirection direction) {
    state = state.copyWith(
      sortField: field,
      sortDirection: direction,
    );
  }
  
  /// 设置交易所
  void setExchange(String exchange) {
    if (state.exchange != exchange) {
      state = state.copyWith(exchange: exchange);
      fetchMarketData(exchange: exchange);
    }
  }
  
  /// 设置市场类型
  void setMarketType(MarketType marketType) {
    if (state.marketType != marketType) {
      state = state.copyWith(marketType: marketType);
      fetchMarketData(marketType: marketType);
    }
  }
  
  /// 启动自动刷新
  void startAutoRefresh({Duration? interval}) {
    stopAutoRefresh();
    
    final duration = interval ?? state.refreshInterval;
    final timer = Timer.periodic(duration, (_) {
      fetchMarketData();
    });
    
    state = state.copyWith(
      autoRefresh: true,
      refreshInterval: duration,
      refreshTimer: timer,
    );
  }
  
  /// 停止自动刷新
  void stopAutoRefresh() {
    state.refreshTimer?.cancel();
    state = state.copyWith(
      autoRefresh: false,
      refreshTimer: null,
    );
  }
  
  /// 清理错误
  void clearError() {
    state = state.copyWith(error: null);
  }
  
  /// 启用实时数据
  void enableRealtimeData() {
    setRealtimeDataEnabled(true);
  }
  
  /// 禁用实时数据
  void disableRealtimeData() {
    setRealtimeDataEnabled(false);
  }
  
  /// 手动刷新数据
  Future<void> manualRefresh() async {
    await fetchMarketData();
  }
  
  /// 重连WebSocket
  void reconnectWebSocket() {
    resetConnectionState();
    if (state.realtimeDataEnabled) {
      connectWebSocket();
    }
  }
  
  /// 获取连接状态描述
  String getConnectionStatusDescription() {
    switch (state.wsConnectionState) {
      case WebSocketConnectionState.disconnected:
        return '已断开';
      case WebSocketConnectionState.connecting:
        return '连接中...';
      case WebSocketConnectionState.connected:
        return '已连接';
      case WebSocketConnectionState.error:
        return '连接错误';
      case WebSocketConnectionState.reconnecting:
        return '重连中...';
    }
  }
  
  /// 获取连接状态颜色
  String getConnectionStatusColor() {
    switch (state.wsConnectionState) {
      case WebSocketConnectionState.disconnected:
        return '#9E9E9E'; // 灰色
      case WebSocketConnectionState.connecting:
        return '#FF9800'; // 橙色
      case WebSocketConnectionState.connected:
        return '#4CAF50'; // 绿色
      case WebSocketConnectionState.error:
        return '#F44336'; // 红色
      case WebSocketConnectionState.reconnecting:
        return '#2196F3'; // 蓝色
    }
  }
  
  @override
  void dispose() {
    stopAutoRefresh();
    disconnectWebSocket();
    super.dispose();
  }
}

/// Provider实例
final marketDataProvider = StateNotifierProvider<MarketDataProvider, MarketDataState>(
  (ref) => MarketDataProvider(),
);