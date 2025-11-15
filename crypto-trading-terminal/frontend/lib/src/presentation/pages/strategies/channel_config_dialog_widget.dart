import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/notification_provider.dart';

/// 渠道配置对话框Widget
/// 用于编辑和配置通知渠道的设置
class ChannelConfigDialogWidget extends ConsumerStatefulWidget {
  final NotificationChannelConfig? channel;
  final NotificationChannelType? channelType;
  final Function(NotificationChannelConfig) onSaved;
  final VoidCallback? onCancel;

  const ChannelConfigDialogWidget({
    super.key,
    this.channel,
    this.channelType,
    required this.onSaved,
    this.onCancel,
  });

  @override
  ConsumerState<ChannelConfigDialogWidget> createState() => _ChannelConfigDialogWidgetState();
}

class _ChannelConfigDialogWidgetState extends ConsumerState<ChannelConfigDialogWidget> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  
  // 通用设置
  bool _enabled = true;
  int _timeout = 5000;
  String _urgency = 'normal';
  
  // Telegram设置
  final _botTokenController = TextEditingController();
  final _chatIdController = TextEditingController();
  
  // Email设置
  final _smtpHostController = TextEditingController();
  final _smtpPortController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _fromEmailController = TextEditingController();
  final _toEmailController = TextEditingController();
  
  late NotificationChannelType _selectedType;

  @override
  void initState() {
    super.initState();
    final channel = widget.channel;
    
    if (channel != null) {
      _nameController.text = channel.name;
      _descriptionController.text = channel.description;
      _enabled = channel.enabled;
      _selectedType = channel.type;
      
      // 加载现有设置
      _timeout = channel.settings['timeout'] ?? 5000;
      _urgency = channel.settings['urgency'] ?? 'normal';
      
      if (channel.type == NotificationChannelType.telegram) {
        _botTokenController.text = channel.settings['bot_token'] ?? '';
        _chatIdController.text = channel.settings['chat_id'] ?? '';
      } else if (channel.type == NotificationChannelType.email) {
        _smtpHostController.text = channel.settings['smtp_host'] ?? '';
        _smtpPortController.text = channel.settings['smtp_port']?.toString() ?? '';
        _usernameController.text = channel.settings['username'] ?? '';
        _passwordController.text = channel.settings['password'] ?? '';
        _fromEmailController.text = channel.settings['from_email'] ?? '';
        _toEmailController.text = channel.settings['to_email'] ?? '';
      }
    } else {
      _selectedType = widget.channelType ?? NotificationChannelType.popup;
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _botTokenController.dispose();
    _chatIdController.dispose();
    _smtpHostController.dispose();
    _smtpPortController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _fromEmailController.dispose();
    _toEmailController.dispose();
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
                      _selectedType.icon,
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        widget.channel == null ? '配置${_selectedType.displayName}' : '编辑渠道',
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
                        label: '渠道名称 *',
                        hint: '请输入渠道名称',
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return '请输入渠道名称';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      _buildTextFormField(
                        controller: _descriptionController,
                        label: '渠道描述',
                        hint: '请输入渠道描述',
                        maxLines: 3,
                      ),
                      const SizedBox(height: 16),
                      _buildEnableSwitch(),
                      
                      // 渠道特定配置
                      const SizedBox(height: 24),
                      _buildSectionTitle('渠道配置'),
                      _buildChannelSpecificConfig(),
                      
                      // 通用设置
                      const SizedBox(height: 24),
                      _buildSectionTitle('通用设置'),
                      _buildGeneralSettings(),
                      
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
                              onPressed: _saveConfiguration,
                              child: Text(widget.channel == null ? '创建渠道' : '保存配置'),
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

  /// 构建启用开关
  Widget _buildEnableSwitch() {
    return SwitchListTile(
      title: const Text('启用渠道'),
      subtitle: const Text('控制渠道的激活状态'),
      value: _enabled,
      onChanged: (value) {
        setState(() {
          _enabled = value;
        });
      },
      contentPadding: EdgeInsets.zero,
    );
  }

  /// 构建渠道特定配置
  Widget _buildChannelSpecificConfig() {
    switch (_selectedType) {
      case NotificationChannelType.popup:
        return _buildPopupConfig();
      case NotificationChannelType.desktop:
        return _buildDesktopConfig();
      case NotificationChannelType.telegram:
        return _buildTelegramConfig();
      case NotificationChannelType.email:
        return _buildEmailConfig();
    }
  }

  /// 构建弹窗配置
  Widget _buildPopupConfig() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '弹窗通知配置',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            _buildTimeoutConfig(),
          ],
        ),
      ),
    );
  }

  /// 构建桌面配置
  Widget _buildDesktopConfig() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '桌面通知配置',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            _buildTimeoutConfig(),
            const SizedBox(height: 16),
            _buildUrgencyConfig(),
          ],
        ),
      ),
    );
  }

  /// 构建Telegram配置
  Widget _buildTelegramConfig() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Telegram Bot配置',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            _buildTextFormField(
              controller: _botTokenController,
              label: 'Bot Token *',
              hint: '请输入Telegram Bot Token',
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return '请输入Bot Token';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            _buildTextFormField(
              controller: _chatIdController,
              label: 'Chat ID *',
              hint: '请输入聊天ID或频道ID',
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return '请输入Chat ID';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            Text(
              '如何获取：\n1. 向 @BotFather 发送 /newbot 创建机器人\n2. 将 Bot Token 填入上方框\n3. 将机器人添加到聊天或频道\n4. 发送任意消息获取 Chat ID',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                  ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建邮件配置
  Widget _buildEmailConfig() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'SMTP邮件配置',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: _buildTextFormField(
                    controller: _smtpHostController,
                    label: 'SMTP服务器 *',
                    hint: 'smtp.gmail.com',
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return '请输入SMTP服务器';
                      }
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildTextFormField(
                    controller: _smtpPortController,
                    label: '端口 *',
                    hint: '587',
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return '请输入端口';
                      }
                      if (int.tryParse(value) == null) {
                        return '请输入有效端口号';
                      }
                      return null;
                    },
                    keyboardType: TextInputType.number,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildTextFormField(
                    controller: _usernameController,
                    label: '用户名 *',
                    hint: '邮箱地址',
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return '请输入用户名';
                      }
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildTextFormField(
                    controller: _passwordController,
                    label: '密码/应用密码 *',
                    hint: '密码或应用密码',
                    obscureText: true,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return '请输入密码';
                      }
                      return null;
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildTextFormField(
                    controller: _fromEmailController,
                    label: '发送者邮箱 *',
                    hint: 'sender@example.com',
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return '请输入发送者邮箱';
                      }
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildTextFormField(
                    controller: _toEmailController,
                    label: '接收者邮箱 *',
                    hint: 'receiver@example.com',
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return '请输入接收者邮箱';
                      }
                      return null;
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              '安全提示：建议使用应用专用密码而不是登录密码。Gmail用户需要在Google账户中启用两步验证并创建应用密码。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.error,
                  ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建超时配置
  Widget _buildTimeoutConfig() {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('超时时间（毫秒）', style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 8),
              Text(
                '$_timeout ms',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 16),
        SizedBox(
          width: 200,
          child: Slider(
            value: _timeout.toDouble(),
            min: 1000,
            max: 30000,
            divisions: 29,
            label: _timeout.toString(),
            onChanged: (value) {
              setState(() {
                _timeout = value.round();
              });
            },
          ),
        ),
      ],
    );
  }

  /// 构建紧急程度配置
  Widget _buildUrgencyConfig() {
    return DropdownButtonFormField<String>(
      value: _urgency,
      decoration: const InputDecoration(
        labelText: '紧急程度',
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
      items: [
        DropdownMenuItem(
          value: 'low',
          child: Row(
            children: [
              Icon(Icons.info_outline, color: Colors.blue),
              SizedBox(width: 8),
              Text('低'),
            ],
          ),
        ),
        DropdownMenuItem(
          value: 'normal',
          child: Row(
            children: [
              Icon(Icons.notifications, color: Colors.green),
              SizedBox(width: 8),
              Text('正常'),
            ],
          ),
        ),
        DropdownMenuItem(
          value: 'critical',
          child: Row(
            children: [
              Icon(Icons.error, color: Colors.red),
              SizedBox(width: 8),
              Text('紧急'),
            ],
          ),
        ),
      ],
      onChanged: (value) {
        if (value != null) {
          setState(() {
            _urgency = value;
          });
        }
      },
    );
  }

  /// 构建通用设置
  Widget _buildGeneralSettings() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '通用设置',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('启用声音'),
              subtitle: const Text('通知时播放提示音'),
              trailing: Switch(
                value: true, // TODO: 从设置中读取
                onChanged: (value) {
                  // TODO: 更新设置
                },
              ),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('启用震动'),
              subtitle: const Text('移动设备震动提醒'),
              trailing: Switch(
                value: true, // TODO: 从设置中读取
                onChanged: (value) {
                  // TODO: 更新设置
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 保存配置
  void _saveConfiguration() {
    if (_formKey.currentState?.validate() ?? false) {
      final now = DateTime.now();
      
      // 构建设置
      final settings = <String, dynamic>{
        'timeout': _timeout,
        'urgency': _urgency,
      };
      
      // 添加渠道特定设置
      switch (_selectedType) {
        case NotificationChannelType.telegram:
          settings.addAll({
            'bot_token': _botTokenController.text.trim(),
            'chat_id': _chatIdController.text.trim(),
          });
          break;
        case NotificationChannelType.email:
          settings.addAll({
            'smtp_host': _smtpHostController.text.trim(),
            'smtp_port': int.parse(_smtpPortController.text.trim()),
            'username': _usernameController.text.trim(),
            'password': _passwordController.text.trim(),
            'from_email': _fromEmailController.text.trim(),
            'to_email': _toEmailController.text.trim(),
          });
          break;
        default:
          break;
      }
      
      final config = NotificationChannelConfig(
        id: widget.channel?.id ?? '',
        name: _nameController.text.trim(),
        description: _descriptionController.text.trim(),
        type: _selectedType,
        enabled: _enabled,
        status: _enabled ? ChannelStatus.enabled : ChannelStatus.disabled,
        settings: settings,
        templateTypes: _getDefaultTemplateTypes(),
        createdAt: widget.channel?.createdAt ?? now,
        updatedAt: now,
        lastUsed: widget.channel?.lastUsed,
        statistics: widget.channel?.statistics ?? {'total': 0, 'successful': 0, 'failed': 0},
      );
      
      widget.onSaved(config);
    }
  }

  /// 获取默认模板类型
  List<String> _getDefaultTemplateTypes() {
    switch (_selectedType) {
      case NotificationChannelType.popup:
        return ['price_alert', 'volume_alert'];
      case NotificationChannelType.desktop:
        return ['price_alert', 'technical_alert', 'emergency_alert'];
      case NotificationChannelType.telegram:
        return ['price_alert', 'volume_alert', 'technical_alert', 'emergency_alert'];
      case NotificationChannelType.email:
        return ['price_alert', 'volume_alert', 'technical_alert', 'emergency_alert'];
    }
  }
}
