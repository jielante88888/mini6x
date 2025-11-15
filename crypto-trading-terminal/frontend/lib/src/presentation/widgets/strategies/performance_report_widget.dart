import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'dart:io';

import '../../providers/strategy_provider.dart';

/// 报告类型
enum ReportType {
  daily('daily', '日报'),
  weekly('weekly', '周报'),
  monthly('monthly', '月报'),
  custom('custom', '自定义');

  const ReportType(this.value, this.displayName);
  final String value;
  final String displayName;
}

/// 性能报告生成器组件
class PerformanceReportWidget extends StatefulWidget {
  final StrategyConfig strategy;
  final StrategyPerformance performance;

  const PerformanceReportWidget({
    super.key,
    required this.strategy,
    required this.performance,
  });

  @override
  State<PerformanceReportWidget> createState() => _PerformanceReportWidgetState();
}

class _PerformanceReportWidgetState extends State<PerformanceReportWidget> {
  ReportType _selectedReportType = ReportType.daily;
  DateTime _startDate = DateTime.now().subtract(const Duration(days: 7));
  DateTime _endDate = DateTime.now();
  bool _includeCharts = true;
  bool _includeTrades = false;
  bool _includeMetrics = true;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            Row(
              children: [
                Icon(
                  Icons.assessment,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '性能报告',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 报告类型选择
            DropdownButtonFormField<ReportType>(
              value: _selectedReportType,
              decoration: const InputDecoration(
                labelText: '报告类型',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: ReportType.values.map((type) {
                return DropdownMenuItem(
                  value: type,
                  child: Text(type.displayName),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedReportType = value ?? ReportType.daily;
                  _updateDateRange();
                });
              },
            ),
            const SizedBox(height: 16),
            
            // 日期范围选择
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    decoration: const InputDecoration(
                      labelText: '开始日期',
                      border: OutlineInputBorder(),
                      suffixIcon: Icon(Icons.calendar_today),
                    ),
                    controller: TextEditingController(
                      text: DateFormat('yyyy-MM-dd').format(_startDate),
                    ),
                    onTap: () => _selectDate(true),
                    readOnly: true,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    decoration: const InputDecoration(
                      labelText: '结束日期',
                      border: OutlineInputBorder(),
                      suffixIcon: Icon(Icons.calendar_today),
                    ),
                    controller: TextEditingController(
                      text: DateFormat('yyyy-MM-dd').format(_endDate),
                    ),
                    onTap: () => _selectDate(false),
                    readOnly: true,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 报告选项
            Text(
              '报告内容',
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            CheckboxListTile(
              title: const Text('包含性能指标'),
              value: _includeMetrics,
              onChanged: (value) {
                setState(() {
                  _includeMetrics = value ?? true;
                });
              },
              contentPadding: EdgeInsets.zero,
              dense: true,
            ),
            CheckboxListTile(
              title: const Text('包含图表'),
              value: _includeCharts,
              onChanged: (value) {
                setState(() {
                  _includeCharts = value ?? true;
                });
              },
              contentPadding: EdgeInsets.zero,
              dense: true,
            ),
            CheckboxListTile(
              title: const Text('包含交易记录'),
              value: _includeTrades,
              onChanged: (value) {
                setState(() {
                  _includeTrades = value ?? false;
                });
              },
              contentPadding: EdgeInsets.zero,
              dense: true,
            ),
            const SizedBox(height: 20),
            
            // 生成按钮
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _generateTextReport,
                    icon: const Icon(Icons.description),
                    label: const Text('文本报告'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _generatePdfReport,
                    icon: const Icon(Icons.picture_as_pdf),
                    label: const Text('PDF报告'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _updateDateRange() {
    final now = DateTime.now();
    switch (_selectedReportType) {
      case ReportType.daily:
        _startDate = DateTime(now.year, now.month, now.day);
        _endDate = now;
        break;
      case ReportType.weekly:
        final startOfWeek = now.subtract(Duration(days: now.weekday - 1));
        _startDate = DateTime(startOfWeek.year, startOfWeek.month, startOfWeek.day);
        _endDate = now;
        break;
      case ReportType.monthly:
        _startDate = DateTime(now.year, now.month, 1);
        _endDate = now;
        break;
      case ReportType.custom:
        // 不更新，保持原有日期
        break;
    }
    setState(() {});
  }

  Future<void> _selectDate(bool isStart) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: isStart ? _startDate : _endDate,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now(),
    );

    if (picked != null) {
      setState(() {
        if (isStart) {
          _startDate = picked;
          if (_startDate.isAfter(_endDate)) {
            _endDate = _startDate;
          }
        } else {
          _endDate = picked;
          if (_endDate.isBefore(_startDate)) {
            _startDate = _endDate;
          }
        }
        _selectedReportType = ReportType.custom;
      });
    }
  }

  void _generateTextReport() async {
    final report = _buildReportContent();
    
    try {
      // 在移动设备上复制到剪贴板
      if (Platform.isAndroid || Platform.isIOS) {
        await Clipboard.setData(ClipboardData(text: report));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('报告已复制到剪贴板')),
          );
        }
      } else {
        // 在桌面设备上保存为文件
        final file = File('strategy_report_${widget.strategy.id}_${DateTime.now().millisecondsSinceEpoch}.txt');
        await file.writeAsString(report);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('报告已保存到: ${file.path}')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('生成报告失败: $e')),
        );
      }
    }
  }

  void _generatePdfReport() {
    // TODO: 实现PDF报告生成
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('PDF报告功能开发中...')),
    );
  }

  String _buildReportContent() {
    final buffer = StringBuffer();
    final dateFormat = DateFormat('yyyy-MM-dd HH:mm:ss');
    final numberFormat = NumberFormat('#,###.##');
    final percentFormat = NumberFormat('#,###.##%');
    
    // 报告头部
    buffer.writeln('策略性能报告');
    buffer.writeln('=' * 50);
    buffer.writeln('生成时间: ${dateFormat.format(DateTime.now())}');
    buffer.writeln();
    
    // 策略基本信息
    buffer.writeln('策略基本信息');
    buffer.writeln('-' * 20);
    buffer.writeln('策略名称: ${widget.strategy.name}');
    buffer.writeln('策略类型: ${widget.strategy.type.displayName}');
    buffer.writeln('交易对: ${widget.strategy.symbol}');
    buffer.writeln('交易所: ${widget.strategy.exchange}');
    buffer.writeln('创建时间: ${dateFormat.format(widget.strategy.createdAt)}');
    buffer.writeln();
    
    // 报告期间
    buffer.writeln('报告期间');
    buffer.writeln('-' * 20);
    buffer.writeln('开始日期: ${dateFormat.format(_startDate)}');
    buffer.writeln('结束日期: ${dateFormat.format(_endDate)}');
    buffer.writeln('报告类型: ${_selectedReportType.displayName}');
    buffer.writeln();
    
    // 性能指标
    if (_includeMetrics) {
      buffer.writeln('性能指标汇总');
      buffer.writeln('-' * 20);
      buffer.writeln('总盈亏: ${numberFormat.format(widget.performance.totalPnL)}');
      buffer.writeln('净盈亏: ${numberFormat.format(widget.performance.netPnL)}');
      buffer.writeln('手续费: ${numberFormat.format(widget.performance.totalCommission)}');
      buffer.writeln('胜率: ${percentFormat.format(widget.performance.winRate)}');
      buffer.writeln('交易次数: ${widget.performance.totalTrades}');
      buffer.writeln('总收益率: ${percentFormat.format(widget.performance.totalReturns)}');
      buffer.writeln('夏普比率: ${widget.performance.sharpeRatio.toStringAsFixed(2)}');
      buffer.writeln('索提诺比率: ${widget.performance.sortinoRatio.toStringAsFixed(2)}');
      buffer.writeln('最大回撤: ${percentFormat.format(widget.performance.maxDrawdown)}');
      buffer.writeln('当前回撤: ${percentFormat.format(widget.performance.currentDrawdown)}');
      buffer.writeln();
    }
    
    // 风险分析
    buffer.writeln('风险分析');
    buffer.writeln('-' * 20);
    final riskLevel = _getRiskLevel();
    buffer.writeln('风险等级: $riskLevel');
    buffer.writeln('风险评价: ${_getRiskAssessment()}');
    buffer.writeln();
    
    // 策略表现评价
    buffer.writeln('策略表现评价');
    buffer.writeln('-' * 20);
    buffer.writeln(_getPerformanceAssessment());
    buffer.writeln();
    
    // 建议
    buffer.writeln('建议');
    buffer.writeln('-' * 20);
    buffer.writeln(_getRecommendations());
    buffer.writeln();
    
    // 报告底部
    buffer.writeln('=' * 50);
    buffer.writeln('报告生成完成');
    
    return buffer.toString();
  }

  String _getRiskLevel() {
    final maxDrawdown = widget.performance.maxDrawdown;
    if (maxDrawdown < 0.05) return '低风险';
    if (maxDrawdown < 0.10) return '中等风险';
    if (maxDrawdown < 0.20) return '高风险';
    return '极高风险';
  }

  String _getRiskAssessment() {
    final sharpe = widget.performance.sharpeRatio;
    if (sharpe > 2.0) return '优秀的风险调整收益';
    if (sharpe > 1.0) return '良好的风险调整收益';
    if (sharpe > 0.5) return '一般的风险调整收益';
    return '较差的风险调整收益';
  }

  String _getPerformanceAssessment() {
    final performance = widget.performance;
    final buffer = StringBuffer();
    
    // 盈利能力评价
    if (performance.netPnL > 0) {
      buffer.writeln('• 策略目前处于盈利状态');
    } else {
      buffer.writeln('• 策略目前处于亏损状态');
    }
    
    // 胜率评价
    if (performance.winRate > 0.7) {
      buffer.writeln('• 胜率较高，策略执行良好');
    } else if (performance.winRate < 0.3) {
      buffer.writeln('• 胜率较低，需要优化策略参数');
    } else {
      buffer.writeln('• 胜率适中，策略执行稳定');
    }
    
    // 交易频率评价
    if (performance.totalTrades < 10) {
      buffer.writeln('• 交易频率较低，可能存在机会未充分利用');
    } else if (performance.totalTrades > 1000) {
      buffer.writeln('• 交易频率较高，需关注手续费成本');
    } else {
      buffer.writeln('• 交易频率适中');
    }
    
    // 回撤评价
    if (performance.maxDrawdown > 0.15) {
      buffer.writeln('• 最大回撤较大，风险控制需要加强');
    } else if (performance.maxDrawdown < 0.05) {
      buffer.writeln('• 最大回撤较小，风险控制良好');
    } else {
      buffer.writeln('• 最大回撤在合理范围内');
    }
    
    return buffer.toString();
  }

  String _getRecommendations() {
    final performance = widget.performance;
    final buffer = StringBuffer();
    
    // 基于性能的推荐
    if (performance.sharpeRatio < 0.5) {
      buffer.writeln('• 考虑优化策略参数以提高风险调整收益');
    }
    
    if (performance.winRate < 0.4) {
      buffer.writeln('• 建议检查入场条件，提高交易胜率');
    }
    
    if (performance.maxDrawdown > 0.15) {
      buffer.writeln('• 建议加强风险控制，降低最大回撤');
    }
    
    if (performance.totalTrades < 10) {
      buffer.writeln('• 可以考虑放宽交易条件，增加交易机会');
    }
    
    if (performance.totalTrades > 1000) {
      buffer.writeln('• 建议优化交易逻辑，减少不必要的交易');
    }
    
    // 策略类型特定建议
    switch (widget.strategy.type) {
      case StrategyType.grid:
        buffer.writeln('• 网格策略建议定期重新平衡网格参数');
        break;
      case StrategyType.martingale:
        buffer.writeln('• 马丁格尔策略建议设置合理的最大步数限制');
        break;
      case StrategyType.arbitrage:
        buffer.writeln('• 套利策略建议监控市场深度变化');
        break;
    }
    
    if (buffer.isEmpty) {
      buffer.writeln('• 策略运行良好，建议继续保持当前设置');
    }
    
    return buffer.toString();
  }
}

/// 报告历史组件
class ReportHistoryWidget extends StatefulWidget {
  final String strategyId;

  const ReportHistoryWidget({
    super.key,
    required this.strategyId,
  });

  @override
  State<ReportHistoryWidget> createState() => _ReportHistoryWidgetState();
}

class _ReportHistoryWidgetState extends State<ReportHistoryWidget> {
  List<Map<String, dynamic>> _reportHistory = [];

  @override
  void initState() {
    super.initState();
    _loadReportHistory();
  }

  void _loadReportHistory() {
    // 模拟报告历史数据
    _reportHistory = [
      {
        'id': '1',
        'type': '日报',
        'date': DateTime.now().subtract(const Duration(days: 1)),
        'size': '2.3 KB',
      },
      {
        'id': '2',
        'type': '周报',
        'date': DateTime.now().subtract(const Duration(days: 7)),
        'size': '15.7 KB',
      },
      {
        'id': '3',
        'type': '月报',
        'date': DateTime.now().subtract(const Duration(days: 30)),
        'size': '48.2 KB',
      },
    ];
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            Row(
              children: [
                Icon(
                  Icons.history,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '报告历史',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 报告列表
            _reportHistory.isEmpty
                ? Center(
                    child: Text(
                      '暂无报告历史',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  )
                : ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: _reportHistory.length,
                    separatorBuilder: (context, index) => const Divider(),
                    itemBuilder: (context, index) {
                      final report = _reportHistory[index];
                      return ListTile(
                        leading: const Icon(Icons.description),
                        title: Text(report['type']),
                        subtitle: Text(DateFormat('yyyy-MM-dd HH:mm').format(report['date'])),
                        trailing: Text(
                          report['size'],
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                        onTap: () => _viewReport(report['id']),
                      );
                    },
                  ),
          ],
        ),
      ),
    );
  }

  void _viewReport(String reportId) {
    // TODO: 实现报告查看功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('报告查看功能开发中...')),
    );
  }
}