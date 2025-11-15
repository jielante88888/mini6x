import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../domain/entities/risk_control.dart';
import '../../widgets/common/custom_card.dart';
import '../../widgets/common/loading_overlay.dart';

/// 仓位风险组件
class PositionRiskWidget extends StatefulWidget {
  final List<PositionRisk> positions;
  final Function(String)? onPositionSelected;

  const PositionRiskWidget({
    super.key,
    required this.positions,
    this.onPositionSelected,
  });

  @override
  State<PositionRiskWidget> createState() => _PositionRiskWidgetState();
}

class _PositionRiskWidgetState extends State<PositionRiskWidget> {
  String _sortBy = 'risk_level';
  bool _sortAscending = false;
  String _filterRiskLevel = 'all';
  String _filterMarketType = 'all';

  @override
  Widget build(BuildContext context) {
    final filteredPositions = _getFilteredAndSortedPositions();
    
    return Column(
      children: [
        // 过滤和排序栏
        _buildFilterSortBar(),
        
        // 仓位列表
        Expanded(
          child: filteredPositions.isEmpty
              ? const Center(
                  child: Text('暂无仓位数据'),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: filteredPositions.length,
                  itemBuilder: (context, index) {
                    final position = filteredPositions[index];
                    return _buildPositionCard(context, position);
                  },
                ),
        ),
      ],
    );
  }

  /// 构建过滤排序栏
  Widget _buildFilterSortBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Theme.of(context).colorScheme.surface,
      child: Column(
        children: [
          // 第一行：过滤器
          Row(
            children: [
              // 风险等级过滤
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filterRiskLevel,
                  decoration: const InputDecoration(
                    labelText: '风险等级',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('全部风险')),
                    DropdownMenuItem(value: 'LOW', child: Text('低风险')),
                    DropdownMenuItem(value: 'MEDIUM', child: Text('中风险')),
                    DropdownMenuItem(value: 'HIGH', child: Text('高风险')),
                    DropdownMenuItem(value: 'CRITICAL', child: Text('极高风险')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _filterRiskLevel = value!;
                    });
                  },
                ),
              ),
              const SizedBox(width: 16),
              
              // 市场类型过滤
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filterMarketType,
                  decoration: const InputDecoration(
                    labelText: '市场类型',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('全部市场')),
                    DropdownMenuItem(value: 'spot', child: Text('现货')),
                    DropdownMenuItem(value: 'futures', child: Text('合约')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _filterMarketType = value!;
                    });
                  },
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 12),
          
          // 第二行：排序
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _sortBy,
                  decoration: const InputDecoration(
                    labelText: '排序依据',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'risk_level', child: Text('风险等级')),
                    DropdownMenuItem(value: 'symbol', child: Text('交易对')),
                    DropdownMenuItem(value: 'unrealized_pnl', child: Text('未实现盈亏')),
                    DropdownMenuItem(value: 'quantity', child: Text('仓位数量')),
                    DropdownMenuItem(value: 'exposure', child: Text('风险暴露')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _sortBy = value!;
                    });
                  },
                ),
              ),
              const SizedBox(width: 16),
              
              // 排序方向
              IconButton(
                onPressed: () {
                  setState(() {
                    _sortAscending = !_sortAscending;
                  });
                },
                icon: Icon(
                  _sortAscending ? Icons.arrow_upward : Icons.arrow_downward,
                  color: Theme.of(context).colorScheme.primary,
                ),
                tooltip: _sortAscending ? '升序' : '降序',
              ),
              
              const SizedBox(width: 8),
              
              // 清除过滤器按钮
              ElevatedButton.icon(
                onPressed: _clearFilters,
                icon: const Icon(Icons.clear, size: 16),
                label: const Text('清除'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 获取过滤和排序后的仓位列表
  List<PositionRisk> _getFilteredAndSortedPositions() {
    var filtered = widget.positions.where((position) {
      // 风险等级过滤
      if (_filterRiskLevel != 'all' && position.riskLevel != _filterRiskLevel) {
        return false;
      }
      
      // 市场类型过滤
      if (_filterMarketType != 'all' && position.marketType != _filterMarketType) {
        return false;
      }
      
      return true;
    }).toList();

    // 排序
    filtered.sort((a, b) {
      int comparison;
      switch (_sortBy) {
        case 'risk_level':
          comparison = _getRiskLevelScore(a.riskLevel).compareTo(_getRiskLevelScore(b.riskLevel));
          break;
        case 'symbol':
          comparison = a.symbol.compareTo(b.symbol);
          break;
        case 'unrealized_pnl':
          comparison = a.unrealizedPnl.compareTo(b.unrealizedPnl);
          break;
        case 'quantity':
          comparison = a.quantity.compareTo(b.quantity);
          break;
        case 'exposure':
          comparison = a.exposurePercent.compareTo(b.exposurePercent);
          break;
        default:
          comparison = 0;
      }
      return _sortAscending ? comparison : -comparison;
    });

    return filtered;
  }

  /// 获取风险等级分数（用于排序）
  int _getRiskLevelScore(String riskLevel) {
    switch (riskLevel) {
      case 'LOW':
        return 1;
      case 'MEDIUM':
        return 2;
      case 'HIGH':
        return 3;
      case 'CRITICAL':
        return 4;
      default:
        return 0;
    }
  }

  /// 清除过滤器
  void _clearFilters() {
    setState(() {
      _filterRiskLevel = 'all';
      _filterMarketType = 'all';
      _sortBy = 'risk_level';
      _sortAscending = false;
    });
  }

  /// 构建仓位卡片
  Widget _buildPositionCard(BuildContext context, PositionRisk position) {
    final theme = Theme.of(context);
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => widget.onPositionSelected?.call(position.positionId.toString()),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 仓位基本信息
              _buildPositionHeader(theme, position),
              
              const SizedBox(height: 12),
              
              // 风险指标
              _buildRiskMetrics(theme, position),
              
              const SizedBox(height: 12),
              
              // 详细信息
              _buildPositionDetails(theme, position),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建仓位头部信息
  Widget _buildPositionHeader(ThemeData theme, PositionRisk position) {
    final pnlColor = position.unrealizedPnl >= 0 ? Colors.green : Colors.red;
    final riskColor = _getRiskLevelColor(position.riskLevel);
    
    return Row(
      children: [
        // 交易对和方向
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: theme.colorScheme.outline,
              width: 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                position.symbol,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: position.isLong ? Colors.green : Colors.red,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${position.marketType.toUpperCase()} ${position.isLong ? 'LONG' : 'SHORT'}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: position.isLong ? Colors.green : Colors.red,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        
        const SizedBox(width: 16),
        
        // 风险等级
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: riskColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: riskColor,
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _getRiskLevelIcon(position.riskLevel),
                size: 14,
                color: riskColor,
              ),
              const SizedBox(width: 4),
              Text(
                _getRiskLevelText(position.riskLevel),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: riskColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        
        const Spacer(),
        
        // 未实现盈亏
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              '未实现盈亏',
              style: theme.textTheme.bodySmall,
            ),
            Text(
              '\$${position.unrealizedPnl.toStringAsFixed(2)}',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: pnlColor,
              ),
            ),
            Text(
              '${position.pnlPercent.toStringAsFixed(2)}%',
              style: theme.textTheme.bodySmall?.copyWith(
                color: pnlColor,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// 构建风险指标
  Widget _buildRiskMetrics(ThemeData theme, PositionRisk position) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withOpacity(0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          // 风险暴露
          Expanded(
            child: _buildRiskMetric(
              theme,
              '风险暴露',
              '${position.exposurePercent.toStringAsFixed(1)}%',
              Icons.exposure,
              Colors.blue,
            ),
          ),
          
          // 保证金比例
          if (position.leverage != null) ...[
            const SizedBox(width: 16),
            Expanded(
              child: _buildRiskMetric(
                theme,
                '保证金比例',
                '${position.marginRatio.toStringAsFixed(1)}%',
                Icons.account_balance_wallet,
                Colors.orange,
              ),
            ),
          ],
          
          // 杠杆倍数
          if (position.leverage != null) ...[
            const SizedBox(width: 16),
            Expanded(
              child: _buildRiskMetric(
                theme,
                '杠杆',
                '${position.leverage}x',
                Icons.trending_up,
                Colors.purple,
              ),
            ),
          ],
          
          // 仓位数量
          if (position.leverage == null) ...[
            const SizedBox(width: 16),
            Expanded(
              child: _buildRiskMetric(
                theme,
                '数量',
                position.quantity.toStringAsFixed(4),
                Icons.inventory_2,
                Colors.indigo,
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// 构建风险指标项
  Widget _buildRiskMetric(
    ThemeData theme,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }

  /// 构建仓位详细信息
  Widget _buildPositionDetails(ThemeData theme, PositionRisk position) {
    return Column(
      children: [
        const Divider(),
        Row(
          children: [
            Expanded(
              child: _buildDetailItem(
                theme,
                '平均价格',
                '\$${position.avgPrice.toStringAsFixed(4)}',
              ),
            ),
            Expanded(
              child: _buildDetailItem(
                theme,
                '入场价格',
                '\$${position.entryPrice.toStringAsFixed(4)}',
              ),
            ),
            Expanded(
              child: _buildDetailItem(
                theme,
                '可用数量',
                position.quantityAvailable.toStringAsFixed(4),
              ),
            ),
            if (position.liquidationPrice != null)
              Expanded(
                child: _buildDetailItem(
                  theme,
                  '强平价格',
                  '\$${position.liquidationPrice!.toStringAsFixed(4)}',
                ),
              ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: Text(
                '状态: ${position.status}',
                style: theme.textTheme.bodySmall,
              ),
            ),
            Text(
              '更新时间: ${DateFormat('MM/dd HH:mm').format(DateTime.parse(position.updatedAt))}',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ],
    );
  }

  /// 构建详细信息项
  Widget _buildDetailItem(ThemeData theme, String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
        Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  /// 获取风险等级颜色
  Color _getRiskLevelColor(String riskLevel) {
    switch (riskLevel) {
      case 'LOW':
        return Colors.green;
      case 'MEDIUM':
        return Colors.orange;
      case 'HIGH':
        return Colors.red;
      case 'CRITICAL':
        return Colors.red.shade700;
      default:
        return Colors.grey;
    }
  }

  /// 获取风险等级图标
  IconData _getRiskLevelIcon(String riskLevel) {
    switch (riskLevel) {
      case 'LOW':
        return Icons.check_circle;
      case 'MEDIUM':
        return Icons.warning;
      case 'HIGH':
        return Icons.error;
      case 'CRITICAL':
        return Icons.emergency;
      default:
        return Icons.help;
    }
  }

  /// 获取风险等级文本
  String _getRiskLevelText(String riskLevel) {
    switch (riskLevel) {
      case 'LOW':
        return '低风险';
      case 'MEDIUM':
        return '中风险';
      case 'HIGH':
        return '高风险';
      case 'CRITICAL':
        return '极高风险';
      default:
        return '未知';
    }
  }
}
