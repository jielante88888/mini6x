import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../domain/entities/auto_order.dart';
import '../../../domain/entities/trading_pair.dart';
import '../../../presentation/widgets/common/custom_button.dart';
import '../../../presentation/widgets/common/custom_card.dart';

class AutoOrderFormWidget extends ConsumerStatefulWidget {
  final List<TradingPair> tradingPairs;
  final Function(CreateAutoOrderRequest) onSubmit;
  final VoidCallback onCancel;

  const AutoOrderFormWidget({
    super.key,
    required this.tradingPairs,
    required this.onSubmit,
    required this.onCancel,
  });

  @override
  ConsumerState<AutoOrderFormWidget> createState() => _AutoOrderFormWidgetState();
}

class _AutoOrderFormWidgetState extends ConsumerState<AutoOrderFormWidget> {
  final _formKey = GlobalKey<FormState>();
  final _strategyNameController = TextEditingController();
  final _symbolController = TextEditingController();
  final _quantityController = TextEditingController();
  final _stopLossController = TextEditingController();
  final _takeProfitController = TextEditingController();
  final _maxSlippageController = TextEditingController();
  final _maxSpreadController = TextEditingController();

  OrderSide _orderSide = OrderSide.buy;
  MarketType _marketType = MarketType.spot;
  int _entryConditionId = 1;

  @override
  void initState() {
    super.initState();
    // 设置默认值
    _maxSlippageController.text = '0.01';
    _maxSpreadController.text = '0.005';
  }

  @override
  void dispose() {
    _strategyNameController.dispose();
    _symbolController.dispose();
    _quantityController.dispose();
    _stopLossController.dispose();
    _takeProfitController.dispose();
    _maxSlippageController.dispose();
    _maxSpreadController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return CustomCard(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 表单标题
              Row(
                children: [
                  Icon(
                    Icons.add_circle_outline,
                    color: theme.colorScheme.primary,
                    size: 28,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    '创建自动订单',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 24),

              // 表单内容
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      // 基本信息部分
                      _buildSectionTitle(theme, '基本信息'),
                      const SizedBox(height: 16),
                      
                      // 策略名称
                      TextFormField(
                        controller: _strategyNameController,
                        decoration: const InputDecoration(
                          labelText: '策略名称 *',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.account_tree),
                        ),
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return '请输入策略名称';
                          }
                          if (value.length > 100) {
                            return '策略名称不能超过100个字符';
                          }
                          return null;
                        },
                      ),
                      
                      const SizedBox(height: 16),
                      
                      // 交易对和市场类型
                      Row(
                        children: [
                          Expanded(
                            flex: 2,
                            child: _buildSymbolDropdown(theme),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: _buildMarketTypeDropdown(theme),
                          ),
                        ],
                      ),
                      
                      const SizedBox(height: 16),
                      
                      // 订单方向和数量
                      Row(
                        children: [
                          Expanded(
                            child: _buildOrderSideSelector(theme),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: TextFormField(
                              controller: _quantityController,
                              decoration: const InputDecoration(
                                labelText: '数量 *',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.scale),
                              ),
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                              validator: (value) {
                                if (value == null || value.trim().isEmpty) {
                                  return '请输入数量';
                                }
                                final quantity = double.tryParse(value);
                                if (quantity == null || quantity <= 0) {
                                  return '请输入有效的数量';
                                }
                                return null;
                              },
                            ),
                          ),
                        ],
                      ),
                      
                      const SizedBox(height: 24),

                      // 风险控制部分
                      _buildSectionTitle(theme, '风险控制'),
                      const SizedBox(height: 16),
                      
                      // 止损止盈价格
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _stopLossController,
                              decoration: const InputDecoration(
                                labelText: '止损价格',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.trending_down),
                              ),
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: TextFormField(
                              controller: _takeProfitController,
                              decoration: const InputDecoration(
                                labelText: '止盈价格',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.trending_up),
                              ),
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            ),
                          ),
                        ],
                      ),
                      
                      const SizedBox(height: 16),
                      
                      // 执行参数
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _maxSlippageController,
                              decoration: const InputDecoration(
                                labelText: '最大滑点 (%)',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.timeline),
                              ),
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                              validator: (value) {
                                if (value == null || value.trim().isEmpty) {
                                  return '请输入最大滑点';
                                }
                                final slippage = double.tryParse(value);
                                if (slippage == null || slippage < 0 || slippage > 100) {
                                  return '请输入0-100之间的有效滑点值';
                                }
                                return null;
                              },
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: TextFormField(
                              controller: _maxSpreadController,
                              decoration: const InputDecoration(
                                labelText: '最大点差 (%)',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.grain),
                              ),
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                              validator: (value) {
                                if (value == null || value.trim().isEmpty) {
                                  return '请输入最大点差';
                                }
                                final spread = double.tryParse(value);
                                if (spread == null || spread < 0 || spread > 100) {
                                  return '请输入0-100之间的有效点差值';
                                }
                                return null;
                              },
                            ),
                          ),
                        ],
                      ),
                      
                      const SizedBox(height: 24),

                      // 触发条件部分
                      _buildSectionTitle(theme, '触发条件'),
                      const SizedBox(height: 16),
                      
                      Text(
                        '请先在条件监控页面创建触发条件，然后输入条件ID',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.7),
                        ),
                      ),
                      
                      const SizedBox(height: 8),
                      
                      TextFormField(
                        decoration: const InputDecoration(
                          labelText: '触发条件ID *',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.rule),
                        ),
                        keyboardType: TextInputType.number,
                        onChanged: (value) {
                          setState(() {
                            _entryConditionId = int.tryParse(value) ?? 1;
                          });
                        },
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return '请输入触发条件ID';
                          }
                          if (int.tryParse(value) == null) {
                            return '请输入有效的条件ID';
                          }
                          return null;
                        },
                      ),
                      
                      const SizedBox(height: 32),

                      // 提示信息
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surfaceVariant.withOpacity(0.5),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: theme.colorScheme.outline.withOpacity(0.2),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  Icons.info_outline,
                                  color: theme.colorScheme.primary,
                                  size: 20,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  '创建说明',
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '• 请确保已创建对应的触发条件',
                              style: theme.textTheme.bodySmall,
                            ),
                            Text(
                              '• 止损价格应低于买入价或高于卖出价',
                              style: theme.textTheme.bodySmall,
                            ),
                            Text(
                              '• 止盈价格应高于买入价或低于卖出价',
                              style: theme.textTheme.bodySmall,
                            ),
                            Text(
                              '• 建议根据风险承受能力设置合理的滑点和点差参数',
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // 操作按钮
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: widget.onCancel,
                    icon: const Icon(Icons.cancel_outlined),
                    label: const Text('取消'),
                  ),
                  const SizedBox(width: 16),
                  CustomButton(
                    onPressed: _handleSubmit,
                    icon: Icons.check_circle_outline,
                    label: '创建订单',
                    type: ButtonType.primary,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(ThemeData theme, String title) {
    return Row(
      children: [
        Container(
          width: 4,
          height: 24,
          decoration: BoxDecoration(
            color: theme.colorScheme.primary,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          title,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w600,
            color: theme.colorScheme.onSurface,
          ),
        ),
      ],
    );
  }

  Widget _buildSymbolDropdown(ThemeData theme) {
    return DropdownButtonFormField<String>(
      value: _symbolController.text.isEmpty ? null : _symbolController.text,
      decoration: const InputDecoration(
        labelText: '交易对 *',
        border: OutlineInputBorder(),
        prefixIcon: Icon(Icons.currency_bitcoin),
      ),
      items: widget.tradingPairs.map((pair) {
        return DropdownMenuItem(
          value: pair.symbol,
          child: Text(
            pair.displayName,
            overflow: TextOverflow.ellipsis,
          ),
        );
      }).toList(),
      onChanged: (value) {
        setState(() {
          _symbolController.text = value ?? '';
          // 自动选择市场类型
          final selectedPair = widget.tradingPairs.firstWhere(
            (pair) => pair.symbol == value,
            orElse: () => widget.tradingPairs.first,
          );
          _marketType = selectedPair.marketType;
        });
      },
      validator: (value) {
        if (value == null || value.isEmpty) {
          return '请选择交易对';
        }
        return null;
      },
    );
  }

  Widget _buildMarketTypeDropdown(ThemeData theme) {
    return DropdownButtonFormField<MarketType>(
      value: _marketType,
      decoration: const InputDecoration(
        labelText: '市场类型',
        border: OutlineInputBorder(),
        prefixIcon: Icon(Icons.account_balance_wallet),
      ),
      items: MarketType.values.map((type) {
        return DropdownMenuItem(
          value: type,
          child: Text(_getMarketTypeDisplayText(type)),
        );
      }).toList(),
      onChanged: (value) {
        setState(() {
          _marketType = value ?? MarketType.spot;
        });
      },
    );
  }

  Widget _buildOrderSideSelector(ThemeData theme) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outline),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildOrderSideButton(
              theme,
              OrderSide.buy,
              Icons.arrow_upward,
              '买入',
              Colors.green,
            ),
          ),
          Expanded(
            child: _buildOrderSideButton(
              theme,
              OrderSide.sell,
              Icons.arrow_downward,
              '卖出',
              Colors.red,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrderSideButton(
    ThemeData theme,
    OrderSide side,
    IconData icon,
    String label,
    Color color,
  ) {
    final isSelected = _orderSide == side;
    
    return InkWell(
      onTap: () {
        setState(() {
          _orderSide = side;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? color.withOpacity(0.1) : null,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Column(
          children: [
            Icon(
              icon,
              color: isSelected ? color : theme.colorScheme.onSurface.withOpacity(0.6),
              size: 20,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: isSelected ? color : theme.colorScheme.onSurface.withOpacity(0.6),
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _getMarketTypeDisplayText(MarketType type) {
    switch (type) {
      case MarketType.spot:
        return '现货';
      case MarketType.futures:
        return '期货';
    }
  }

  void _handleSubmit() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final request = CreateAutoOrderRequest(
      strategyName: _strategyNameController.text.trim(),
      symbol: _symbolController.text.trim(),
      marketType: _marketType,
      orderSide: _orderSide,
      quantity: double.parse(_quantityController.text),
      entryConditionId: _entryConditionId,
      stopLossPrice: _stopLossController.text.isEmpty
          ? null
          : double.parse(_stopLossController.text),
      takeProfitPrice: _takeProfitController.text.isEmpty
          ? null
          : double.parse(_takeProfitController.text),
      maxSlippage: double.parse(_maxSlippageController.text) / 100,
      maxSpread: double.parse(_maxSpreadController.text) / 100,
    );

    widget.onSubmit(request);
  }
}