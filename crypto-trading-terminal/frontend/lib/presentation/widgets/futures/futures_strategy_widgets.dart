import 'package:flutter/material.dart';
import 'dart:math' as math;

class LeverageControlWidget extends StatefulWidget {
  final double currentLeverage;
  final double minLeverage;
  final double maxLeverage;
  final Function(double) onLeverageChanged;
  final bool isEnabled;

  const LeverageControlWidget({
    Key? key,
    required this.currentLeverage,
    required this.minLeverage,
    required this.maxLeverage,
    required this.onLeverageChanged,
    this.isEnabled = true,
  }) : super(key: key);

  @override
  State<LeverageControlWidget> createState() => _LeverageControlWidgetState();
}

class _LeverageControlWidgetState extends State<LeverageControlWidget> {
  late double _leverage;

  @override
  void initState() {
    super.initState();
    _leverage = widget.currentLeverage;
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  '杠杆控制',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getLeverageColor(_leverage),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${_leverage.toStringAsFixed(1)}x',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Slider(
              value: _leverage,
              min: widget.minLeverage,
              max: widget.maxLeverage,
              divisions: ((widget.maxLeverage - widget.minLeverage) * 10).round(),
              activeColor: _getLeverageColor(_leverage),
              onChanged: widget.isEnabled ? (value) {
                setState(() {
                  _leverage = value;
                });
              } : null,
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('${widget.minLeverage.toInt()}x'),
                Text('${widget.maxLeverage.toInt()}x'),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: widget.isEnabled ? () {
                      _leverage = 1.0;
                      _emitLeverageChange();
                    } : null,
                    child: const Text('1x'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: widget.isEnabled ? () {
                      _leverage = 5.0;
                      _emitLeverageChange();
                    } : null,
                    child: const Text('5x'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: widget.isEnabled ? () {
                      _leverage = 10.0;
                      _emitLeverageChange();
                    } : null,
                    child: const Text('10x'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: widget.isEnabled ? () {
                      _leverage = 20.0;
                      _emitLeverageChange();
                    } : null,
                    child: const Text('20x'),
                  ),
                ),
              ],
            ),
            if (!widget.isEnabled) ...[
              const SizedBox(height: 8),
              Text(
                '杠杆调整已禁用',
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _getLeverageColor(double leverage) {
    if (leverage <= 5) return Colors.green;
    if (leverage <= 10) return Colors.orange;
    if (leverage <= 20) return Colors.red;
    return Colors.purple;
  }

  void _emitLeverageChange() {
    widget.onLeverageChanged(_leverage);
  }
}

class RiskControlWidget extends StatelessWidget {
  final String riskLevel;
  final double marginRatio;
  final double liquidationDistance;
  final VoidCallback? onRiskSettingsPressed;

  const RiskControlWidget({
    Key? key,
    required this.riskLevel,
    required this.marginRatio,
    required this.liquidationDistance,
    this.onRiskSettingsPressed,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _getRiskIcon(riskLevel),
                  color: _getRiskColor(riskLevel),
                  size: 24,
                ),
                const SizedBox(width: 8),
                const Text(
                  '风险控制',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                if (onRiskSettingsPressed != null)
                  IconButton(
                    icon: const Icon(Icons.settings),
                    onPressed: onRiskSettingsPressed,
                  ),
              ],
            ),
            const SizedBox(height: 16),
            _buildRiskIndicator('保证金比例', marginRatio, '%', _getMarginRatioColor(marginRatio)),
            const SizedBox(height: 12),
            _buildRiskIndicator('距离强平', liquidationDistance, '%', _getLiquidationDistanceColor(liquidationDistance)),
            const SizedBox(height: 16),
            Text(
              '风险等级: ${_getRiskLevelText(riskLevel)}',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: _getRiskColor(riskLevel),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRiskIndicator(String label, double value, String unit, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(fontSize: 14),
            ),
            Text(
              '${value.toStringAsFixed(2)}$unit',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(
          value: _getProgressValue(label, value),
          backgroundColor: Colors.grey[300],
          valueColor: AlwaysStoppedAnimation<Color>(color),
        ),
      ],
    );
  }

  double _getProgressValue(String label, double value) {
    switch (label) {
      case '保证金比例':
        return math.min(value / 200, 1.0);
      case '距离强平':
        return math.min(value / 50, 1.0);
      default:
        return 0.0;
    }
  }

  Color _getRiskColor(String riskLevel) {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL':
        return Colors.red;
      case 'HIGH':
        return Colors.orange;
      case 'MEDIUM':
        return Colors.amber;
      default:
        return Colors.green;
    }
  }

  IconData _getRiskIcon(String riskLevel) {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL':
        return Icons.dangerous;
      case 'HIGH':
        return Icons.warning;
      case 'MEDIUM':
        return Icons.info;
      default:
        return Icons.check_circle;
    }
  }

  String _getRiskLevelText(String riskLevel) {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL':
        return '极高风险';
      case 'HIGH':
        return '高风险';
      case 'MEDIUM':
        return '中等风险';
      default:
        return '低风险';
    }
  }

  Color _getMarginRatioColor(double ratio) {
    if (ratio < 105) return Colors.red;
    if (ratio < 110) return Colors.orange;
    if (ratio < 120) return Colors.amber;
    return Colors.green;
  }

  Color _getLiquidationDistanceColor(double distance) {
    if (distance < 10) return Colors.red;
    if (distance < 25) return Colors.orange;
    if (distance < 50) return Colors.amber;
    return Colors.green;
  }
}

class FundingRateWidget extends StatelessWidget {
  final double fundingRate;
  final DateTime nextFundingTime;
  final List<Map<String, dynamic>> fundingHistory;

  const FundingRateWidget({
    Key? key,
    required this.fundingRate,
    required this.nextFundingTime,
    required this.fundingHistory,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '资金费率',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '当前费率',
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                      Text(
                        '${(fundingRate * 100).toStringAsFixed(4)}%',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: _getFundingRateColor(fundingRate),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '下次结算',
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                      Text(
                        _formatTime(nextFundingTime),
                        style: const TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (fundingRate != 0)
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: _getFundingRateColor(fundingRate).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  children: [
                    Icon(
                      _getFundingRateIcon(fundingRate),
                      color: _getFundingRateColor(fundingRate),
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _getFundingRateText(fundingRate),
                        style: TextStyle(
                          fontSize: 12,
                          color: _getFundingRateColor(fundingRate),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            if (fundingHistory.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text(
                '历史费率',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              SizedBox(
                height: 60,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: math.min(fundingHistory.length, 7),
                  itemBuilder: (context, index) {
                    final history = fundingHistory[fundingHistory.length - 1 - index];
                    return _buildFundingRateItem(context, history);
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFundingRateItem(BuildContext context, Map<String, dynamic> history) {
    final rate = history['rate'] as double;
    final time = history['time'] as DateTime;
    
    return Container(
      width: 80,
      margin: const EdgeInsets.only(right: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        border: Border.all(color: _getFundingRateColor(rate)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${(rate * 100).toStringAsFixed(3)}%',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: _getFundingRateColor(rate),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${time.day}/${time.month}',
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Color _getFundingRateColor(double rate) {
    if (rate > 0) return Colors.red;
    if (rate < 0) return Colors.green;
    return Colors.grey;
  }

  IconData _getFundingRateIcon(double rate) {
    if (rate > 0) return Icons.trending_up;
    if (rate < 0) return Icons.trending_down;
    return Icons.trending_flat;
  }

  String _getFundingRateText(double rate) {
    if (rate > 0) return '多头支付空头资金费率';
    if (rate < 0) return '空头支付多头资金费率';
    return '资金费率为零';
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final difference = time.difference(now);
    
    if (difference.isNegative) {
      return '已结算';
    }
    
    if (difference.inHours > 0) {
      return '${difference.inHours}小时${difference.inMinutes % 60}分钟';
    } else {
      return '${difference.inMinutes}分钟';
    }
  }
}

class PositionDetailsWidget extends StatefulWidget {
  final Map<String, dynamic> position;
  final VoidCallback? onEdit;
  final VoidCallback? onClose;

  const PositionDetailsWidget({
    Key? key,
    required this.position,
    this.onEdit,
    this.onClose,
  }) : super(key: key);

  @override
  State<PositionDetailsWidget> createState() => _PositionDetailsWidgetState();
}

class _PositionDetailsWidgetState extends State<PositionDetailsWidget> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final position = widget.position;
    final symbol = position['symbol'] as String;
    final side = position['side'] as String;
    final size = position['size'] as double;
    final entryPrice = position['entry_price'] as double;
    final currentPrice = position['current_price'] as double;
    final leverage = position['leverage'] as double;
    final pnl = position['pnl'] as double;
    final marginRatio = position['margin_ratio'] as double;

    return Card(
      child: InkWell(
        onTap: () => setState(() => _isExpanded = !_isExpanded),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              symbol,
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: side == 'LONG'
                                    ? Colors.green[100]
                                    : Colors.red[100],
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                side,
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: side == 'LONG'
                                      ? Colors.green[700]
                                      : Colors.red[700],
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text('规模: $size | 杠杆: ${leverage}x'),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '\$${pnl.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: pnl >= 0 ? Colors.green : Colors.red,
                        ),
                      ),
                      Text(
                        '保证金比例: ${marginRatio.toStringAsFixed(1)}%',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              if (_isExpanded) ...[
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _buildDetailItem('开仓价', '\$${entryPrice.toStringAsFixed(2)}'),
                    ),
                    Expanded(
                      child: _buildDetailItem('现价', '\$${currentPrice.toStringAsFixed(2)}'),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: _buildDetailItem('未实现盈亏', '\$${pnl.toStringAsFixed(2)}'),
                    ),
                    Expanded(
                      child: _buildDetailItem('保证金比例', '${marginRatio.toStringAsFixed(1)}%'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    if (widget.onEdit != null) ...[
                      Expanded(
                        child: OutlinedButton(
                          onPressed: widget.onEdit,
                          child: const Text('编辑'),
                        ),
                      ),
                      const SizedBox(width: 8),
                    ],
                    if (widget.onClose != null)
                      Expanded(
                        child: ElevatedButton(
                          onPressed: widget.onClose,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red,
                            foregroundColor: Colors.white,
                          ),
                          child: const Text('平仓'),
                        ),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 8),
              Icon(
                _isExpanded ? Icons.expand_less : Icons.expand_more,
                color: Colors.grey[600],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class MarginAlertWidget extends StatelessWidget {
  final Map<String, dynamic> alert;
  final VoidCallback onDismiss;

  const MarginAlertWidget({
    Key? key,
    required this.alert,
    required this.onDismiss,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final type = alert['type'] as String;
    final message = alert['message'] as String;
    final riskLevel = alert['risk_level'] as String;
    final timestamp = alert['timestamp'] as DateTime;

    return Card(
      color: _getAlertBackgroundColor(riskLevel),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              _getAlertIcon(type),
              color: _getAlertColor(riskLevel),
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _formatTime(timestamp),
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.close, size: 16),
              onPressed: onDismiss,
            ),
          ],
        ),
      ),
    );
  }

  Color _getAlertBackgroundColor(String riskLevel) {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL':
        return Colors.red[50]!;
      case 'HIGH':
        return Colors.orange[50]!;
      default:
        return Colors.amber[50]!;
    }
  }

  Color _getAlertColor(String riskLevel) {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL':
        return Colors.red;
      case 'HIGH':
        return Colors.orange;
      default:
        return Colors.amber;
    }
  }

  IconData _getAlertIcon(String type) {
    switch (type) {
      case 'margin_call':
        return Icons.warning;
      case 'liquidation_risk':
        return Icons.dangerous;
      default:
        return Icons.info;
    }
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);
    
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
}