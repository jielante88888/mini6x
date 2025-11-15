import 'package:flutter/material.dart';

import '../../../domain/ai_analysis/models.dart';

/// 信号强度卡片 - 展示信号分析结果
class SignalStrengthCard extends StatelessWidget {
  final SignalInsight signalInsight;

  const SignalStrengthCard({
    Key? key,
    required this.signalInsight,
  }) : super(key: key);

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
                  Icons.speed,
                  color: theme.colorScheme.secondary,
                ),
                const SizedBox(width: 8),
                Text(
                  '信号强度',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 主要信号
            _buildPrimarySignal(context),
            const SizedBox(height: 16),
            
            // 强度和质量指标
            Row(
              children: [
                Expanded(
                  child: _buildSignalStrengthMetric(context),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildSignalQualityMetric(context),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 支持和冲突指标
            if (signalInsight.supportingIndicators.isNotEmpty ||
                signalInsight.conflictingIndicators.isNotEmpty) ..[
              _buildIndicatorsAnalysis(context),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建主要信号
  Widget _buildPrimarySignal(BuildContext context) {
    final theme = Theme.of(context);
    final signal = signalInsight.primarySignal;
    
    Color signalColor;
    IconData signalIcon;
    String signalDescription;
    
    switch (signal) {
      case SignalType.buy:
        signalColor = Colors.green;
        signalIcon = Icons.arrow_upward;
        signalDescription = '买入信号';
        break;
      case SignalType.sell:
        signalColor = Colors.red;
        signalIcon = Icons.arrow_downward;
        signalDescription = '卖出信号';
        break;
      case SignalType.hold:
        signalColor = Colors.grey;
        signalIcon = Icons.pause;
        signalDescription = '持有信号';
        break;
      case SignalType.weakBuy:
        signalColor = Colors.lightGreen;
        signalIcon = Icons.keyboard_arrow_up;
        signalDescription = '谨慎买入';
        break;
      case SignalType.weakSell:
        signalColor = Colors.orange;
        signalIcon = Icons.keyboard_arrow_down;
        signalDescription = '谨慎卖出';
        break;
    }
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: signalColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: signalColor.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Icon(
            signalIcon,
            color: signalColor,
            size: 24,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  signalDescription,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: signalColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '交易对: ${signalInsight.symbol}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// 构建信号强度指标
  Widget _buildSignalStrengthMetric(BuildContext context) {
    final theme = Theme.of(context);
    final strength = signalInsight.signalStrength;
    
    Color strengthColor;
    double strengthValue;
    String strengthText;
    
    switch (strength) {
      case SignalStrength.veryStrong:
        strengthColor = Colors.green;
        strengthValue = 1.0;
        strengthText = '极强';
        break;
      case SignalStrength.strong:
        strengthColor = Colors.lightGreen;
        strengthValue = 0.8;
        strengthText = '强';
        break;
      case SignalStrength.moderate:
        strengthColor = Colors.orange;
        strengthValue = 0.6;
        strengthText = '中等';
        break;
      case SignalStrength.weak:
        strengthColor = Colors.redAccent;
        strengthValue = 0.4;
        strengthText = '弱';
        break;
      case SignalStrength.veryWeak:
        strengthColor = Colors.red;
        strengthValue = 0.2;
        strengthText = '极弱';
        break;
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '信号强度',
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          height: 6,
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceVariant,
            borderRadius: BorderRadius.circular(3),
          ),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: strengthValue,
            child: Container(
              decoration: BoxDecoration(
                color: strengthColor,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          strengthText,
          style: theme.textTheme.bodySmall?.copyWith(
            color: strengthColor,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  /// 构建信号质量指标
  Widget _buildSignalQualityMetric(BuildContext context) {
    final theme = Theme.of(context);
    final quality = signalInsight.quality;
    
    Color qualityColor;
    String qualityText;
    IconData qualityIcon;
    
    switch (quality) {
      case SignalQuality.excellent:
        qualityColor = Colors.green;
        qualityText = '优秀';
        qualityIcon = Icons.star;
        break;
      case SignalQuality.good:
        qualityColor = Colors.lightGreen;
        qualityText = '良好';
        qualityIcon = Icons.star_half;
        break;
      case SignalQuality.fair:
        qualityColor = Colors.orange;
        qualityText = '一般';
        qualityIcon = Icons.star_outline;
        break;
      case SignalQuality.poor:
        qualityColor = Colors.redAccent;
        qualityText = '较差';
        qualityIcon = Icons.star_outline;
        break;
      case SignalQuality.invalid:
        qualityColor = Colors.red;
        qualityText = '无效';
        qualityIcon = Icons.cancel;
        break;
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '信号质量',
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Icon(
              qualityIcon,
              size: 16,
              color: qualityColor,
            ),
            const SizedBox(width: 4),
            Text(
              qualityText,
              style: theme.textTheme.bodySmall?.copyWith(
                color: qualityColor,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// 构建指标分析
  Widget _buildIndicatorsAnalysis(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 支持指标
        if (signalInsight.supportingIndicators.isNotEmpty) ..[
          _buildIndicatorGroup(
            context,
            '支持指标',
            signalInsight.supportingIndicators,
            Colors.green,
            Icons.check_circle,
          ),
          const SizedBox(height: 8),
        ],
        
        // 冲突指标
        if (signalInsight.conflictingIndicators.isNotEmpty) ..[
          _buildIndicatorGroup(
            context,
            '冲突指标',
            signalInsight.conflictingIndicators,
            Colors.red,
            Icons.warning,
          ),
        ],
      ],
    );
  }

  /// 构建指标组
  Widget _buildIndicatorGroup(BuildContext context, String title, 
                              List<String> indicators, Color color, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 16,
              color: color,
            ),
            const SizedBox(width: 4),
            Text(
              title,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: color,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ...indicators.take(2).map((indicator) => Padding(
          padding: const EdgeInsets.only(left: 20, bottom: 2),
          child: Text(
            '• $indicator',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        )),
        if (indicators.length > 2)
          Text(
            '...还有其他 ${indicators.length - 2} 个指标',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
              fontStyle: FontStyle.italic,
            ),
          ),
      ],
    );
  }
}