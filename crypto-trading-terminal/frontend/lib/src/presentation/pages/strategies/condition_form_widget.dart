import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/conditions_provider.dart';

/// 条件创建/编辑表单Widget
/// 用于创建和编辑交易条件的表单组件
class ConditionFormWidget extends ConsumerStatefulWidget {
  final Condition? condition;
  final Function(Condition) onSaved;
  final VoidCallback? onCancel;

  const ConditionFormWidget({
    super.key,
    this.condition,
    required this.onSaved,
    this.onCancel,
  });

  @override
  ConsumerState<ConditionFormWidget> createState() => _ConditionFormWidgetState();
}

class _ConditionFormWidgetState extends ConsumerState<ConditionFormWidget> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _valueController = TextEditingController();
  final _symbolController = TextEditingController();

  late ConditionType _selectedType;
  late ConditionOperator _selectedOperator;
  late int _selectedPriority;
  bool _isEnabled = true;

  @override
  void initState() {
    super.initState();
    final condition = widget.condition;
    
    if (condition != null) {
      _nameController.text = condition.name;
      _descriptionController.text = condition.description ?? '';
      _valueController.text = condition.value.toString();
      _symbolController.text = condition.symbol;
      _selectedType = condition.type;
      _selectedOperator = condition.operator;
      _selectedPriority = condition.priority;
      _isEnabled = condition.enabled;
    } else {
      _selectedType = ConditionType.price;
      _selectedOperator = ConditionOperator.greaterThan;
      _selectedPriority = 2;
      _symbolController.text = 'BTC/USDT';
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _valueController.dispose();
    _symbolController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return DraggableScrollableSheet(
      initialChildSize: 0.9,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // 顶部栏
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
                ),
                child: Row(
                  children: [
                    Icon(
                      _getConditionIcon(_selectedType),
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        widget.condition == null ? '创建条件' : '编辑条件',
                        style: theme.textTheme.headlineSmall?.copyWith(
                          color: theme.colorScheme.onPrimaryContainer,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: Icon(
                        Icons.close,
                        color: theme.colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ],
                ),
              ),
              
              // 表单内容
              Expanded(
                child: Form(
                  key: _formKey,
                  child: ListView(
                    controller: scrollController,
                    padding: const EdgeInsets.all(16),
                    children: [
                      // 基本信息
                      _buildSectionTitle('基本信息'),
                      _buildTextFormField(
                        controller: _nameController,
                        label: '条件名称 *',
                        hint: '请输入条件的名称',
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return '请输入条件名称';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      _buildTextFormField(
                        controller: _descriptionController,
                        label: '条件描述',
                        hint: '请输入条件的详细描述',
                        maxLines: 3,
                      ),
                      const SizedBox(height: 16),
                      _buildTextFormField(
                        controller: _symbolController,
                        label: '交易对 *',
                        hint: '例如：BTC/USDT',
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return '请输入交易对';
                          }
                          return null;
                        },
                      ),
                      
                      // 条件设置
                      const SizedBox(height: 24),
                      _buildSectionTitle('条件设置'),
                      _buildTypeSelector(),
                      const SizedBox(height: 12),
                      _buildOperatorAndValueRow(),
                      
                      // 高级设置
                      const SizedBox(height: 24),
                      _buildSectionTitle('高级设置'),
                      _buildPrioritySelector(),
                      const SizedBox(height: 16),
                      _buildEnableSwitch(),
                      
                      // 底部按钮
                      const SizedBox(height: 32),
                      Row(
                        children: [
                          if (widget.onCancel != null) ...[
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () {
                                  widget.onCancel?.call();
                                  Navigator.of(context).pop();
                                },
                                child: const Text('取消'),
                              ),
                            ),
                            const SizedBox(width: 12),
                          ],
                          Expanded(
                            flex: 2,
                            child: ElevatedButton(
                              onPressed: _saveCondition,
                              child: Text(widget.condition == null ? '创建条件' : '保存修改'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  /// 构建区块标题
  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
      ),
    );
  }

  /// 构建文本表单字段
  Widget _buildTextFormField({
    required TextEditingController controller,
    required String label,
    required String hint,
    String? Function(String?)? validator,
    int maxLines = 1,
    TextInputType? keyboardType,
    List<TextInputFormatter>? inputFormatters,
  }) {
    return TextFormField(
      controller: controller,
      validator: validator,
      maxLines: maxLines,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
      ),
    );
  }

  /// 构建条件类型选择器
  Widget _buildTypeSelector() {
    return DropdownButtonFormField<ConditionType>(
      value: _selectedType,
      decoration: const InputDecoration(
        labelText: '条件类型 *',
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
      items: ConditionType.values.map((type) {
        return DropdownMenuItem(
          value: type,
          child: Row(
            children: [
              Icon(_getConditionIcon(type), size: 20),
              const SizedBox(width: 8),
              Text(type.displayName),
            ],
          ),
        );
      }).toList(),
      onChanged: (value) {
        if (value != null) {
          setState(() {
            _selectedType = value;
            _updateKeyboardType();
          });
        }
      },
    );
  }

  /// 构建操作符和数值输入行
  Widget _buildOperatorAndValueRow() {
    return Row(
      children: [
        Expanded(
          flex: 1,
          child: DropdownButtonFormField<ConditionOperator>(
            value: _selectedOperator,
            decoration: const InputDecoration(
              labelText: '操作符 *',
              border: OutlineInputBorder(),
              contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
            items: ConditionOperator.values.map((op) {
              return DropdownMenuItem(
                value: op,
                child: Text(op.displayName),
              );
            }).toList(),
            onChanged: (value) {
              if (value != null) {
                setState(() {
                  _selectedOperator = value;
                });
              }
            },
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          flex: 2,
          child: _buildTextFormField(
            controller: _valueController,
            label: '阈值 *',
            hint: '请输入阈值',
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return '请输入阈值';
              }
              if (double.tryParse(value) == null) {
                return '请输入有效的数值';
              }
              return null;
            },
            keyboardType: _getKeyboardType(),
            inputFormatters: _getInputFormatters(),
          ),
        ),
      ],
    );
  }

  /// 构建优先级选择器
  Widget _buildPrioritySelector() {
    return DropdownButtonFormField<int>(
      value: _selectedPriority,
      decoration: const InputDecoration(
        labelText: '优先级',
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
      items: [1, 2, 3, 4, 5].map((priority) {
        final priorityEnum = ConditionPriority.values.firstWhere((p) => p.value == priority);
        return DropdownMenuItem(
          value: priority,
          child: Row(
            children: [
              Text(priorityEnum.emoji),
              const SizedBox(width: 8),
              Text(priorityEnum.displayName),
            ],
          ),
        );
      }).toList(),
      onChanged: (value) {
        if (value != null) {
          setState(() {
            _selectedPriority = value;
          });
        }
      },
    );
  }

  /// 构建启用开关
  Widget _buildEnableSwitch() {
    return SwitchListTile(
      title: const Text('启用条件'),
      subtitle: const Text('控制条件的激活状态'),
      value: _isEnabled,
      onChanged: (value) {
        setState(() {
          _isEnabled = value;
        });
      },
      contentPadding: EdgeInsets.zero,
    );
  }

  /// 获取条件类型图标
  IconData _getConditionIcon(ConditionType type) {
    switch (type) {
      case ConditionType.price:
        return Icons.attach_money;
      case ConditionType.volume:
        return Icons.bar_chart;
      case ConditionType.time:
        return Icons.schedule;
      case ConditionType.technical:
        return Icons.trending_up;
      case ConditionType.market:
        return Icons.public;
    }
  }

  /// 获取键盘类型
  TextInputType _getKeyboardType() {
    switch (_selectedType) {
      case ConditionType.price:
      case ConditionType.volume:
        return TextInputType.number;
      case ConditionType.time:
      case ConditionType.technical:
      case ConditionType.market:
        return TextInputType.text;
    }
  }

  /// 获取输入格式化器
  List<TextInputFormatter>? _getInputFormatters() {
    switch (_selectedType) {
      case ConditionType.price:
      case ConditionType.volume:
        return [
          FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,8}')),
        ];
      default:
        return null;
    }
  }

  /// 更新键盘类型
  void _updateKeyboardType() {
    _valueController.clear();
  }

  /// 保存条件
  void _saveCondition() {
    if (_formKey.currentState?.validate() ?? false) {
      final now = DateTime.now();
      final condition = Condition(
        id: widget.condition?.id ?? '',
        name: _nameController.text.trim(),
        description: _descriptionController.text.trim().isNotEmpty 
            ? _descriptionController.text.trim() 
            : null,
        type: _selectedType,
        operator: _selectedOperator,
        value: _selectedType == ConditionType.price || _selectedType == ConditionType.volume
            ? double.parse(_valueController.text)
            : _valueController.text,
        symbol: _symbolController.text.trim(),
        enabled: _isEnabled,
        priority: _selectedPriority,
        status: _isEnabled ? ConditionStatus.enabled : ConditionStatus.disabled,
        createdAt: widget.condition?.createdAt ?? now,
        updatedAt: now,
        lastTriggered: widget.condition?.lastTriggered,
        triggerCount: widget.condition?.triggerCount ?? 0,
        metadata: widget.condition?.metadata ?? {},
      );

      widget.onSaved(condition);
    }
  }
}
