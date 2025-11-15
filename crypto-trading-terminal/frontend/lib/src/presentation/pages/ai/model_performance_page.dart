import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../../domain/ai_analysis/models.dart';
import '../../../presentation/providers/ai_analysis_provider.dart';
import '../../../presentation/widgets/ai_analysis/loading_card.dart';
import '../../../presentation/widgets/ai_analysis/error_card.dart';
import '../../../presentation/widgets/common/chart_card.dart';
import '../../../presentation/widgets/common/status_indicator.dart';
import '../../../../../../utils/formatters.dart';

class ModelPerformancePage extends ConsumerStatefulWidget {
  const ModelPerformancePage({super.key});

  @override
  ConsumerState<ModelPerformancePage> createState() => _ModelPerformancePageState();
}

class _ModelPerformancePageState extends ConsumerState<ModelPerformancePage>
    with TickerProviderStateMixin {
  late TabController _tabController;
  String? _selectedModelId;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    
    // Load model performance data
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(modelPerformanceProvider.notifier).loadModelPerformance();
      _startAutoRefresh();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      if (mounted) {
        ref.read(modelPerformanceProvider.notifier).refreshData();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final modelPerformanceState = ref.watch(modelPerformanceProvider);
    
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('模型性能监控'),
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        elevation: 0,
        bottom: TabBar(
          controller: _tabController,
          labelColor: Theme.of(context).colorScheme.primary,
          unselectedLabelColor: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
          indicatorColor: Theme.of(context).colorScheme.primary,
          tabs: const [
            Tab(text: '概览'),
            Tab(text: '性能图表'),
            Tab(text: '警报'),
            Tab(text: '版本管理'),
          ],
        ),
      ),
      body: Column(
        children: [
          // Model Selection Card
          _buildModelSelectionCard(modelPerformanceState),
          
          // Tab Bar View
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildOverviewTab(modelPerformanceState),
                _buildPerformanceChartTab(modelPerformanceState),
                _buildAlertsTab(modelPerformanceState),
                _buildVersionManagementTab(modelPerformanceState),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModelSelectionCard(ModelPerformanceState state) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainer,
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
                Icons.model_training,
                color: Theme.of(context).colorScheme.primary,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                '选择模型',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              if (state.isLoading)
                SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _selectedModelId,
            decoration: const InputDecoration(
              hintText: '选择要监控的AI模型',
              border: OutlineInputBorder(),
              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            ),
            items: state.availableModels.map((model) {
              return DropdownMenuItem(
                value: model['modelId'],
                child: Row(
                  children: [
                    StatusIndicator(
                      status: _getStatusFromString(model['status']),
                      size: 12,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        model['modelId'],
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
            onChanged: (value) {
              setState(() {
                _selectedModelId = value;
              });
              if (value != null) {
                ref.read(modelPerformanceProvider.notifier)
                    .selectModel(value);
              }
            },
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab(ModelPerformanceState state) {
    if (_selectedModelId == null) {
      return const Center(
        child: Text('请选择一个模型以查看性能数据'),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(modelPerformanceProvider.notifier).refreshData();
      },
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Model Status Card
            _buildModelStatusCard(state),
            const SizedBox(height: 16),
            
            // Performance Metrics Grid
            _buildPerformanceMetricsGrid(state),
            const SizedBox(height: 16),
            
            // Recent Alerts
            _buildRecentAlertsCard(state),
            const SizedBox(height: 16),
            
            // Quick Actions
            _buildQuickActionsCard(state),
          ],
        ),
      ),
    );
  }

  Widget _buildModelStatusCard(ModelPerformanceState state) {
    final modelData = state.selectedModelPerformance;
    if (modelData == null) return const SizedBox();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                StatusIndicator(
                  status: _getStatusFromString(modelData.status),
                  size: 16,
                ),
                const SizedBox(width: 8),
                Text(
                  '模型状态',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getStatusColor(modelData.status).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    _getStatusText(modelData.status),
                    style: TextStyle(
                      color: _getStatusColor(modelData.status),
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              '最后更新: ${_formatDateTime(modelData.lastUpdated)}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceMetricsGrid(ModelPerformanceState state) {
    final modelData = state.selectedModelPerformance;
    if (modelData == null) return const SizedBox();

    final metrics = modelData.latestMetrics;
    
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.5,
      children: [
        _buildMetricCard(
          '准确率',
          '${(metrics.accuracy * 100).toStringAsFixed(1)}%',
          Icons.trending_up,
          _getMetricColor(metrics.accuracy, 0.8),
        ),
        _buildMetricCard(
          'F1分数',
          '${(metrics.f1Score * 100).toStringAsFixed(1)}%',
          Icons.analytics,
          _getMetricColor(metrics.f1Score, 0.75),
        ),
        _buildMetricCard(
          '预测延迟',
          '${metrics.predictionLatencyMs.toStringAsFixed(0)}ms',
          Icons.speed,
          _getLatencyColor(metrics.predictionLatencyMs),
        ),
        _buildMetricCard(
          '错误率',
          '${(metrics.errorRate * 100).toStringAsFixed(2)}%',
          Icons.error_outline,
          _getErrorColor(metrics.errorRate),
        ),
      ],
    );
  }

  Widget _buildMetricCard(String title, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentAlertsCard(ModelPerformanceState state) {
    final alerts = state.alerts.where((alert) => 
        alert.modelId == _selectedModelId && !alert.acknowledged).take(3).toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  color: Theme.of(context).colorScheme.error,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  '最近警报',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                if (alerts.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.error.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${alerts.length}',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            if (alerts.isEmpty)
              Text(
                '暂无活跃警报',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                ),
              )
            else
              ...alerts.map((alert) => _buildAlertItem(alert)).toList(),
            if (alerts.isNotEmpty) ...[
              const SizedBox(height: 12),
              TextButton(
                onPressed: () {
                  _tabController.animateTo(2); // Switch to alerts tab
                },
                child: const Text('查看所有警报'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAlertItem(ModelAlert alert) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _getAlertLevelColor(alert.level).withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _getAlertLevelColor(alert.level).withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            alert.title,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            alert.message,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _getAlertLevelColor(alert.level),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  alert.level.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                _formatDateTime(alert.timestamp),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActionsCard(ModelPerformanceState state) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '快速操作',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _triggerRetraining(),
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('重新训练'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).colorScheme.primary,
                      foregroundColor: Theme.of(context).colorScheme.onPrimary,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _showPerformanceDetails(),
                    icon: const Icon(Icons.analytics, size: 16),
                    label: const Text('详细分析'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceChartTab(ModelPerformanceState state) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Accuracy Trend Chart
          ChartCard(
            title: '准确率趋势',
            subtitle: '最近24小时准确率变化',
            child: SizedBox(
              height: 200,
              child: _buildAccuracyChart(state),
            ),
          ),
          const SizedBox(height: 16),
          
          // Latency Chart
          ChartCard(
            title: '预测延迟',
            subtitle: '最近24小时延迟变化',
            child: SizedBox(
              height: 200,
              child: _buildLatencyChart(state),
            ),
          ),
          const SizedBox(height: 16),
          
          // Resource Usage Chart
          ChartCard(
            title: '资源使用率',
            subtitle: 'CPU和内存使用情况',
            child: SizedBox(
              height: 200,
              child: _buildResourceUsageChart(state),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAccuracyChart(ModelPerformanceState state) {
    final modelData = state.selectedModelPerformance;
    if (modelData?.trendData == null) {
      return const Center(child: Text('暂无准确率趋势数据'));
    }

    final spots = <FlSpot>[];
    // Generate sample data points for chart
    for (int i = 0; i < 24; i++) {
      spots.add(FlSpot(i.toDouble(), 0.8 + (i * 0.005)));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Theme.of(context).colorScheme.primary,
            barWidth: 3,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: Theme.of(context).colorScheme.primary.withOpacity(0.1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLatencyChart(ModelPerformanceState state) {
    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: List.generate(24, (index) => 
                FlSpot(index.toDouble(), 100 + (index * 5).toDouble())),
            isCurved: true,
            color: Theme.of(context).colorScheme.secondary,
            barWidth: 3,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: Theme.of(context).colorScheme.secondary.withOpacity(0.1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResourceUsageChart(ModelPerformanceState state) {
    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: 100,
        barTouchData: BarTouchData(enabled: false),
        titlesData: FlTitlesData(
          show: true,
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                switch (value.toInt()) {
                  case 0:
                    return const Text('CPU');
                  case 1:
                    return const Text('内存');
                  default:
                    return const Text('');
                }
              },
            ),
          ),
          leftTitles: const AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        barGroups: [
          BarChartGroupData(
            x: 0,
            barRods: [
              BarChartRodData(
                toY: 45,
                color: Theme.of(context).colorScheme.primary,
              ),
            ],
          ),
          BarChartGroupData(
            x: 1,
            barRods: [
              BarChartRodData(
                toY: 65,
                color: Theme.of(context).colorScheme.secondary,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAlertsTab(ModelPerformanceState state) {
    final alerts = state.alerts.where((alert) => 
        _selectedModelId == null || alert.modelId == _selectedModelId).toList();

    return Column(
      children: [
        // Filter Tabs
        Container(
          margin: const EdgeInsets.all(16),
          child: Row(
            children: [
              _buildAlertFilterChip('全部', alerts.length, true),
              const SizedBox(width: 8),
              _buildAlertFilterChip(
                '未确认', 
                alerts.where((a) => !a.acknowledged).length, 
                false
              ),
              const SizedBox(width: 8),
              _buildAlertFilterChip(
                '严重', 
                alerts.where((a) => a.level == 'critical').length, 
                false
              ),
            ],
          ),
        ),
        
        // Alerts List
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: alerts.length,
            itemBuilder: (context, index) {
              final alert = alerts[index];
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: _getAlertLevelColor(alert.level),
                    child: Icon(
                      _getAlertIcon(alert.level),
                      color: Colors.white,
                      size: 16,
                    ),
                  ),
                  title: Text(alert.title),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(alert.message),
                      const SizedBox(height: 4),
                      Text(
                        _formatDateTime(alert.timestamp),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                    ],
                  ),
                  trailing: PopupMenuButton(
                    itemBuilder: (context) => [
                      if (!alert.acknowledged)
                        PopupMenuItem(
                          value: 'acknowledge',
                          child: const Text('确认'),
                        ),
                      PopupMenuItem(
                        value: 'details',
                        child: const Text('详情'),
                      ),
                    ],
                    onSelected: (value) {
                      switch (value) {
                        case 'acknowledge':
                          _acknowledgeAlert(alert.alertId);
                          break;
                        case 'details':
                          _showAlertDetails(alert);
                          break;
                      }
                    },
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildAlertFilterChip(String label, int count, bool isSelected) {
    return FilterChip(
      label: Text('$label ($count)'),
      selected: isSelected,
      onSelected: (selected) {
        // Implement filtering logic
      },
      backgroundColor: Theme.of(context).colorScheme.surfaceContainer,
      selectedColor: Theme.of(context).colorScheme.primary.withOpacity(0.2),
    );
  }

  Widget _buildVersionManagementTab(ModelPerformanceState state) {
    final versions = state.modelVersions.where((version) => 
        _selectedModelId == null || version.modelId == _selectedModelId).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.history,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                '版本历史',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              ElevatedButton.icon(
                onPressed: () => _showRetrainingDialog(),
                icon: const Icon(Icons.add, size: 16),
                label: const Text('创建新版本'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Version List
          ...versions.map((version) => _buildVersionItem(version)).toList(),
        ],
      ),
    );
  }

  Widget _buildVersionItem(ModelVersion version) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: version.isActive 
                        ? Theme.of(context).colorScheme.primary.withOpacity(0.1)
                        : Theme.of(context).colorScheme.outline.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    version.versionNumber,
                    style: TextStyle(
                      color: version.isActive 
                          ? Theme.of(context).colorScheme.primary
                          : Theme.of(context).colorScheme.outline,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                if (version.isActive)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.green.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '活跃',
                      style: TextStyle(
                        color: Colors.green,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                const Spacer(),
                PopupMenuButton(
                  itemBuilder: (context) => [
                    if (!version.isActive)
                      PopupMenuItem(
                        value: 'activate',
                        child: const Text('激活'),
                      ),
                    PopupMenuItem(
                      value: 'details',
                      child: const Text('详情'),
                    ),
                    PopupMenuItem(
                      value: 'rollback',
                      child: const Text('回滚'),
                    ),
                  ],
                  onSelected: (value) {
                    switch (value) {
                      case 'activate':
                        _activateVersion(version.versionId);
                        break;
                      case 'details':
                        _showVersionDetails(version);
                        break;
                      case 'rollback':
                        _rollbackVersion(version.versionId);
                        break;
                    }
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '准确率: ${(version.accuracy * 100).toStringAsFixed(1)}%',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 4),
            Text(
              '创建时间: ${_formatDateTime(version.creationTime)}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
            if (version.notes.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                version.notes,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.8),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // Helper methods

  Status _getStatusFromString(String status) {
    switch (status.toLowerCase()) {
      case 'healthy':
        return Status.healthy;
      case 'degraded':
        return Status.warning;
      case 'critical':
        return Status.error;
      case 'retraining':
        return Status.loading;
      default:
        return Status.unknown;
    }
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'healthy':
        return Colors.green;
      case 'degraded':
        return Colors.orange;
      case 'critical':
        return Colors.red;
      case 'retraining':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  String _getStatusText(String status) {
    switch (status.toLowerCase()) {
      case 'healthy':
        return '健康';
      case 'degraded':
        return '降级';
      case 'critical':
        return '严重';
      case 'retraining':
        return '训练中';
      default:
        return '未知';
    }
  }

  Color _getMetricColor(double value, double threshold) {
    if (value >= threshold) return Colors.green;
    if (value >= threshold * 0.8) return Colors.orange;
    return Colors.red;
  }

  Color _getLatencyColor(double latency) {
    if (latency <= 500) return Colors.green;
    if (latency <= 1000) return Colors.orange;
    return Colors.red;
  }

  Color _getErrorColor(double errorRate) {
    if (errorRate <= 0.01) return Colors.green;
    if (errorRate <= 0.05) return Colors.orange;
    return Colors.red;
  }

  Color _getAlertLevelColor(String level) {
    switch (level.toLowerCase()) {
      case 'critical':
        return Colors.red;
      case 'warning':
        return Colors.orange;
      case 'info':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  IconData _getAlertIcon(String level) {
    switch (level.toLowerCase()) {
      case 'critical':
        return Icons.error;
      case 'warning':
        return Icons.warning;
      case 'info':
        return Icons.info;
      default:
        return Icons.notifications;
    }
  }

  String _formatDateTime(DateTime dateTime) {
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

  // Action methods

  void _triggerRetraining() {
    if (_selectedModelId == null) return;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('重新训练模型'),
        content: const Text('确定要触发模型重新训练吗？这可能需要较长时间。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              ref.read(modelPerformanceProvider.notifier)
                  .triggerRetraining(_selectedModelId!);
              Navigator.of(context).pop();
              
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('重新训练已触发'),
                  backgroundColor: Colors.green,
                ),
              );
            },
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  void _showPerformanceDetails() {
    // Navigate to detailed performance page
  }

  void _acknowledgeAlert(String alertId) {
    ref.read(modelPerformanceProvider.notifier).acknowledgeAlert(alertId);
  }

  void _showAlertDetails(ModelAlert alert) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(alert.title),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(alert.message),
            const SizedBox(height: 16),
            Text('时间: ${_formatDateTime(alert.timestamp)}'),
            Text('级别: ${alert.level}'),
            Text('模型: ${alert.modelId}'),
            if (alert.metadata.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text('元数据:'),
              ...alert.metadata.entries.map((entry) => 
                Text('${entry.key}: ${entry.value}')
              ).toList(),
            ],
          ],
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

  void _showRetrainingDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('触发重新训练'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('选择重新训练触发原因：'),
            SizedBox(height: 16),
            TextField(
              decoration: InputDecoration(
                labelText: '触发原因说明',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              // Trigger retraining
            },
            child: const Text('开始训练'),
          ),
        ],
      ),
    );
  }

  void _activateVersion(String versionId) {
    ref.read(modelPerformanceProvider.notifier).activateVersion(versionId);
  }

  void _showVersionDetails(ModelVersion version) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('版本详情 - ${version.versionNumber}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('准确率: ${(version.accuracy * 100).toStringAsFixed(1)}%'),
            Text('F1分数: ${(version.f1Score * 100).toStringAsFixed(1)}%'),
            Text('预测延迟: ${version.predictionLatencyMs.toStringAsFixed(0)}ms'),
            Text('创建时间: ${_formatDateTime(version.creationTime)}'),
            Text('模型文件: ${version.modelFilePath}'),
            if (version.notes.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text('备注:'),
              Text(version.notes),
            ],
          ],
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

  void _rollbackVersion(String versionId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('版本回滚'),
        content: const Text('确定要回滚到指定版本吗？这将影响当前活跃的模型版本。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              ref.read(modelPerformanceProvider.notifier).rollbackVersion(versionId);
              Navigator.of(context).pop();
            },
            child: const Text('确定回滚'),
          ),
        ],
      ),
    );
  }
}