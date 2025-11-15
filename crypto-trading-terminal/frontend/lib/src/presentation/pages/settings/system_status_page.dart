import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../providers/reconnection_provider.dart';
import '../../providers/system_status_provider.dart';
import '../../widgets/reconnection_manager_widget.dart';

/// 交易所状态枚举
enum ExchangeStatus {
  online,
  degraded,
  offline,
  maintenance,
  error
}

/// 连接状态枚举
enum ConnectionStatus {
  connected,
  connecting,
  disconnected,
  reconnecting,
  failed
}

/// 交易所状态信息
class ExchangeStatusInfo {
  final String exchange;
  final ExchangeStatus overallStatus;
  final ExchangeStatus spotStatus;
  final ExchangeStatus futuresStatus;
  final DateTime lastUpdate;
  final double uptimePercentage;
  final int errorCount;
  final double performanceScore;
  final int activeConnections;
  final List<String> apiStatuses;

  ExchangeStatusInfo({
    required this.exchange,
    required this.overallStatus,
    required this.spotStatus,
    required this.futuresStatus,
    required this.lastUpdate,
    required this.uptimePercentage,
    required this.errorCount,
    required this.performanceScore,
    required this.activeConnections,
    required this.apiStatuses,
  });

  factory ExchangeStatusInfo.fromJson(Map<String, dynamic> json) {
    return ExchangeStatusInfo(
      exchange: json['exchange'],
      overallStatus: ExchangeStatus.values.firstWhere(
        (e) => e.toString().split('.').last == json['overall_status']
      ),
      spotStatus: ExchangeStatus.values.firstWhere(
        (e) => e.toString().split('.').last == json['spot_status']
      ),
      futuresStatus: ExchangeStatus.values.firstWhere(
        (e) => e.toString().split('.').last == json['futures_status']
      ),
      lastUpdate: DateTime.parse(json['last_update']),
      uptimePercentage: (json['uptime_percentage'] as num).toDouble(),
      errorCount: json['error_count'],
      performanceScore: (json['performance_score'] as num).toDouble(),
      activeConnections: json['active_connections'],
      apiStatuses: List<String>.from(json['api_statuses'] ?? []),
    );
  }
}

/// 系统状态提供者
class SystemStatusProvider extends StateNotifier<Map<String, ExchangeStatusInfo>> {
  SystemStatusProvider() : super({}) {
    _startMonitoring();
  }

  static const String baseUrl = 'http://localhost:8000/api/v1';
  Timer? _monitoringTimer;
  bool _isMonitoring = false;

  /// 开始监控
  void _startMonitoring() {
    _isMonitoring = true;
    _fetchSystemStatus();
    _monitoringTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _fetchSystemStatus(),
    );
  }

  /// 停止监控
  void stopMonitoring() {
    _isMonitoring = false;
    _monitoringTimer?.cancel();
  }

  /// 重新开始监控
  void restartMonitoring() {
    stopMonitoring();
    _startMonitoring();
  }

  /// 获取系统状态
  Future<void> _fetchSystemStatus() async {
    if (!_isMonitoring) return;

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/exchanges/status'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body) as Map<String, dynamic>;
        final exchangesData = jsonData['exchanges'] as Map<String, dynamic>;

        final newStatus = <String, ExchangeStatusInfo>{};
        
        for (final entry in exchangesData.entries) {
          final exchange = entry.key;
          final data = entry.value as Map<String, dynamic>;
          
          newStatus[exchange] = ExchangeStatusInfo.fromJson(data);
        }

        state = newStatus;
      }
    } catch (e) {
      debugPrint('获取系统状态失败: $e');
    }
  }

  /// 强制刷新
  Future<void> refresh() async {
    await _fetchSystemStatus();
  }

  /// 手动重连交易所
  Future<void> reconnectExchange(String exchange) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/exchanges/$exchange/reconnect'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        // 立即刷新状态
        await _fetchSystemStatus();
      }
    } catch (e) {
      debugPrint('重连交易所失败: $e');
    }
  }
}

/// 系统状态页面
class SystemStatusPage extends ConsumerStatefulWidget {
  const SystemStatusPage({super.key});

  @override
  ConsumerState<SystemStatusPage> createState() => _SystemStatusPageState();
}

class _SystemStatusPageState extends ConsumerState<SystemStatusPage> {
  @override
  void dispose() {
    ref.read(systemStatusProvider.notifier).stopMonitoring();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final systemStatus = ref.watch(systemStatusProvider);
    final systemStatusNotifier = ref.read(systemStatusProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        title: const Text('系统状态'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => systemStatusNotifier.refresh(),
            tooltip: '刷新',
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showSettingsDialog(),
            tooltip: '设置',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => systemStatusNotifier.refresh(),
        child: CustomScrollView(
          slivers: [
            // 系统总体状态卡片
            SliverToBoxAdapter(
              child: _buildOverallStatusCard(systemStatus),
            ),
            // 交易所状态列表
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final exchanges = systemStatus.values.toList();
                  if (index >= exchanges.length) return null;
                  
                  final exchange = exchanges[index];
                  return _buildExchangeStatusCard(exchange, systemStatusNotifier);
                },
                childCount: systemStatus.length,
              ),
            ),
            // 性能统计信息
            SliverToBoxAdapter(
              child: _buildPerformanceStatsCard(systemStatus),
            ),
            // 故障转移日志
            SliverToBoxAdapter(
              child: _buildFailoverLogCard(),
            ),
            // 重连管理
            SliverToBoxAdapter(
              child: _buildReconnectionManagementCard(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOverallStatusCard(Map<String, ExchangeStatusInfo> status) {
    final onlineCount = status.values.where((e) => e.overallStatus == ExchangeStatus.online).length;
    final degradedCount = status.values.where((e) => e.overallStatus == ExchangeStatus.degraded).length;
    final offlineCount = status.values.where((e) => 
      e.overallStatus == ExchangeStatus.offline || 
      e.overallStatus == ExchangeStatus.error
    ).length;
    final totalCount = status.length;

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '系统总体状态',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildStatusIndicator(
                '在线',
                onlineCount,
                Colors.green,
                totalCount,
              ),
              _buildStatusIndicator(
                '降级',
                degradedCount,
                Colors.orange,
                totalCount,
              ),
              _buildStatusIndicator(
                '离线',
                offlineCount,
                Colors.red,
                totalCount,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              const Icon(Icons.update, size: 16),
              const SizedBox(width: 4),
              Text(
                '最后更新: ${DateTime.now().toString().substring(11, 16)}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatusIndicator(String label, int count, Color color, int total) {
    final percentage = total > 0 ? (count / total * 100) : 0.0;
    
    return Column(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            shape: BoxShape.circle,
            border: Border.all(color: color, width: 2),
          ),
          child: Center(
            child: Text(
              count.toString(),
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: color,
            fontWeight: FontWeight.w500,
          ),
        ),
        Text(
          '${percentage.toStringAsFixed(1)}%',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _buildExchangeStatusCard(ExchangeStatusInfo exchange, SystemStatusProvider notifier) {
    final overallColor = _getStatusColor(exchange.overallStatus);
    final spotColor = _getStatusColor(exchange.spotStatus);
    final futuresColor = _getStatusColor(exchange.futuresStatus);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 交易所标题栏
          Row(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: overallColor,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  exchange.exchange.toUpperCase(),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.refresh, size: 16),
                onPressed: () => notifier.reconnectExchange(exchange.exchange),
                tooltip: '重新连接',
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          // 市场状态详情
          Row(
            children: [
              Expanded(
                child: _buildMarketStatusChip(
                  '现货',
                  exchange.spotStatus,
                  spotColor,
                  exchange.uptimePercentage,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildMarketStatusChip(
                  '期货',
                  exchange.futuresStatus,
                  futuresColor,
                  exchange.uptimePercentage,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          // 性能指标
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildMetricItem(
                '运行时间',
                '${exchange.uptimePercentage.toStringAsFixed(1)}%',
              ),
              _buildMetricItem(
                '错误次数',
                exchange.errorCount.toString(),
              ),
              _buildMetricItem(
                '性能得分',
                exchange.performanceScore.toStringAsFixed(2),
              ),
              _buildMetricItem(
                '活跃连接',
                exchange.activeConnections.toString(),
              ),
            ],
          ),
          const SizedBox(height: 8),
          
          // API状态
          Text(
            'API状态: ${exchange.apiStatuses.join(', ')}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          
          // 最后更新
          Text(
            '最后更新: ${_formatTime(exchange.lastUpdate)}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMarketStatusChip(String label, ExchangeStatus status, Color color, double uptime) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color, width: 1),
      ),
      child: Column(
        children: [
          Text(
            label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w500,
              fontSize: 12,
            ),
          ),
          Text(
            status.toString().split('.').last.toUpperCase(),
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricItem(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _buildPerformanceStatsCard(Map<String, ExchangeStatusInfo> status) {
    final avgUptime = status.values.isNotEmpty 
        ? status.values.map((e) => e.uptimePercentage).reduce((a, b) => a + b) / status.values.length
        : 0.0;
    final totalErrors = status.values.fold(0, (sum, e) => sum + e.errorCount);
    final avgPerformance = status.values.isNotEmpty
        ? status.values.map((e) => e.performanceScore).reduce((a, b) => a + b) / status.values.length
        : 0.0;

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '性能统计',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildPerformanceItem(
                '平均运行时间',
                '${avgUptime.toStringAsFixed(1)}%',
                Icons.timeline,
              ),
              _buildPerformanceItem(
                '总错误数',
                totalErrors.toString(),
                Icons.error_outline,
              ),
              _buildPerformanceItem(
                '平均性能得分',
                avgPerformance.toStringAsFixed(2),
                Icons.speed,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceItem(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, size: 32, color: Theme.of(context).primaryColor),
        const SizedBox(height: 8),
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildFailoverLogCard() {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '故障转移日志',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          
          // 模拟故障转移日志
          const _FailoverLogItem(
            time: '14:32:15',
            exchange: 'binance',
            action: '现货市场切换到 OKX',
            status: '成功',
            color: Colors.green,
          ),
          const _FailoverLogItem(
            time: '14:31:45',
            exchange: 'binance',
            action: '检测到连接超时',
            status: '警告',
            color: Colors.orange,
          ),
          const _FailoverLogItem(
            time: '14:30:20',
            exchange: 'okx',
            action: '恢复连接 - binance',
            status: '成功',
            color: Colors.green,
          ),
          
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => _showFailoverLogDialog(),
            child: const Text('查看全部日志'),
          ),
        ],
      ),
    );
  }

  /// 构建重连管理卡片
  Widget _buildReconnectionManagementCard() {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.sync_alt,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                '重连管理',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Binance重连管理
          const ReconnectionManagerWidget(
            exchange: 'binance',
            failureType: FailureType.networkTimeout,
          ),
          
          const SizedBox(height: 12),
          
          // OKX重连管理
          const ReconnectionManagerWidget(
            exchange: 'okx',
            failureType: FailureType.serverError,
          ),
          
          const SizedBox(height: 16),
          
          // 智能重连建议
          const SmartReconnectionSuggestion(
            exchange: 'binance',
            failureType: FailureType.networkTimeout,
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(ExchangeStatus status) {
    switch (status) {
      case ExchangeStatus.online:
        return Colors.green;
      case ExchangeStatus.degraded:
        return Colors.orange;
      case ExchangeStatus.offline:
      case ExchangeStatus.error:
        return Colors.red;
      case ExchangeStatus.maintenance:
        return Colors.blue;
    }
  }

  String _formatTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inMinutes < 1) {
      return '刚刚';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}分钟前';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}小时前';
    } else {
      return '${difference.inDays}天前';
    }
  }

  void _showSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('系统设置'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(Icons.timer),
              title: Text('监控间隔'),
              subtitle: Text('30秒'),
            ),
            ListTile(
              leading: Icon(Icons.notifications),
              title: Text('故障通知'),
              subtitle: Text('已启用'),
            ),
            ListTile(
              leading: Icon(Icons.auto_fix_high),
              title: Text('自动重连'),
              subtitle: Text('已启用'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // 应用设置
            },
            child: const Text('应用'),
          ),
        ],
      ),
    );
  }

  void _showFailoverLogDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('故障转移日志'),
        content: const SizedBox(
          width: double.maxFinite,
          height: 400,
          child: Column(
            children: [
              Expanded(
                child: ListView(
                  children: [
                    _FailoverLogItem(
                      time: '14:32:15',
                      exchange: 'binance',
                      action: '现货市场切换到 OKX',
                      status: '成功',
                      color: Colors.green,
                    ),
                    _FailoverLogItem(
                      time: '14:31:45',
                      exchange: 'binance',
                      action: '检测到连接超时',
                      status: '警告',
                      color: Colors.orange,
                    ),
                    _FailoverLogItem(
                      time: '14:30:20',
                      exchange: 'okx',
                      action: '恢复连接 - binance',
                      status: '成功',
                      color: Colors.green,
                    ),
                  ],
                ),
              ),
            ],
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
}

/// 故障转移日志项
class _FailoverLogItem extends StatelessWidget {
  final String time;
  final String exchange;
  final String action;
  final String status;
  final Color color;

  const _FailoverLogItem({
    required this.time,
    required this.exchange,
    required this.action,
    required this.status,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Container(
            width: 60,
            child: Text(
              time,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontFamily: 'monospace',
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            width: 80,
            child: Text(
              exchange.toUpperCase(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              action,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: color, width: 1),
            ),
            child: Text(
              status,
              style: TextStyle(
                color: color,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 系统状态提供者实例
final systemStatusProvider = StateNotifierProvider<SystemStatusProvider, Map<String, ExchangeStatusInfo>>(
  (ref) => SystemStatusProvider(),
);