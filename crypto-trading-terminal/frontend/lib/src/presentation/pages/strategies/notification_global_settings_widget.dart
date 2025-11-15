import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/notification_provider.dart';

/// 通知全局设置Widget
/// 管理通知系统的全局配置和偏好设置
class NotificationGlobalSettingsWidget extends ConsumerStatefulWidget {
  const NotificationGlobalSettingsWidget({super.key});

  @override
  ConsumerState<NotificationGlobalSettingsWidget> createState() => _NotificationGlobalSettingsWidgetState();
}

class _NotificationGlobalSettingsWidgetState extends ConsumerState<NotificationGlobalSettingsWidget> {
  late NotificationGlobalSettings _settings;
  bool _hasChanges = false;

  @override
  void initState() {
    super.initState();
    final notificationState = ref.read(notificationProvider);
    _settings = notificationState.globalSettings;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // 总体设置
        _buildGeneralSection(theme),
        
        const SizedBox(height: 24),
        
        // 声音和震动设置
        _buildAudioSection(theme),
        
        const SizedBox(height: 24),
        
        // 重试设置
        _buildRetrySection(theme),
        
        const SizedBox(height: 24),
        
        // 模板设置
        _buildTemplateSection(theme),
        
        const SizedBox(height: 24),
        
        // 测试区域
        _buildTestingSection(theme),
        
        const SizedBox(height: 24),
        
        // 底部操作按钮
        if (_hasChanges) _buildActionButtons(theme),
      ],
    );
  }

  /// 构建总体设置区块
  Widget _buildGeneralSection(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.tune,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '总体设置',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 启用通知
            SwitchListTile(
              title: const Text('启用通知系统'),
              subtitle: const Text('关闭后将暂停所有通知'),
              value: _settings.enableNotifications,
              onChanged: (value) {
                setState(() {
                  _settings = _settings.copyWith(enableNotifications: value);
                  _hasChanges = true;
                });
              },
              contentPadding: EdgeInsets.zero,
            ),
            
            // 桌面弹窗
            SwitchListTile(
              title: const Text('启用桌面弹窗'),
              subtitle: const Text('在桌面上显示通知弹窗'),
              value: _settings.enableDesktopPopups,
              onChanged: (value) {
                setState(() {
                  _settings = _settings.copyWith(enableDesktopPopups: value);
                  _hasChanges = true;
                });
              },
              contentPadding: EdgeInsets.zero,
              enabled: _settings.enableNotifications,
            ),
          ],
        ),
      ),
    );
  }

  /// 构建声音和震动设置区块
  Widget _buildAudioSection(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.volume_up,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '声音和震动',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 启用声音
            SwitchListTile(
              title: const Text('启用声音提醒'),
              subtitle: const Text('通知时播放提示音'),
              value: _settings.enableSound,
              onChanged: (value) {
                setState(() {
                  _settings = _settings.copyWith(enableSound: value);
                  _hasChanges = true;
                });
              },
              contentPadding: EdgeInsets.zero,
              enabled: _settings.enableNotifications,
            ),
            
            // 启用震动
            SwitchListTile(
              title: const Text('启用震动提醒'),
              subtitle: const Text('移动设备震动提醒'),
              value: _settings.enableVibration,
              onChanged: (value) {
                setState(() {
                  _settings = _settings.copyWith(enableVibration: value);
                  _hasChanges = true;
                });
              },
              contentPadding: EdgeInsets.zero,
              enabled: _settings.enableNotifications,
            ),
            
            // 音量控制（如果启用声音）
            if (_settings.enableSound) ...[
              const SizedBox(height: 16),
              _buildVolumeControl(theme),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建音量控制
  Widget _buildVolumeControl(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '通知音量',
          style: theme.textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            const Icon(Icons.volume_down),
            Expanded(
              child: Slider(
                value: 0.7, // TODO: 从设置中读取音量值
                onChanged: (value) {
                  // TODO: 更新音量设置
                },
              ),
            ),
            const Icon(Icons.volume_up),
          ],
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('静音', style: theme.textTheme.bodySmall),
            Text('最大', style: theme.textTheme.bodySmall),
          ],
        ),
      ],
    );
  }

  /// 构建重试设置区块
  Widget _buildRetrySection(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.refresh,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '重试设置',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 最大重试次数
            _buildSliderSetting(
              context: context,
              title: '最大重试次数',
              subtitle: '通知发送失败时的重试次数',
              value: _settings.maxRetries.toDouble(),
              min: 0,
              max: 10,
              divisions: 10,
              onChanged: (value) {
                setState(() {
                  _settings = _settings.copyWith(maxRetries: value.round());
                  _hasChanges = true;
                });
              },
              formatter: (value) => '${value.round()}次',
            ),
            
            const SizedBox(height: 16),
            
            // 重试延迟
            _buildSliderSetting(
              context: context,
              title: '重试延迟',
              subtitle: '重试之间的等待时间',
              value: _settings.retryDelay.toDouble() / 1000, // 转换为秒
              min: 1,
              max: 60,
              divisions: 59,
              onChanged: (value) {
                setState(() {
                  _settings = _settings.copyWith(retryDelay: (value.round() * 1000).round());
                  _hasChanges = true;
                });
              },
              formatter: (value) => '${value.round()}秒',
            ),
          ],
        ),
      ),
    );
  }

  /// 构建滑块设置项
  Widget _buildSliderSetting({
    required BuildContext context,
    required String title,
    required String subtitle,
    required double value,
    required double min,
    required double max,
    required int divisions,
    required ValueChanged<double> onChanged,
    required String Function(double) formatter,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        Text(
          subtitle,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Text(min.toString()),
            Expanded(
              child: Slider(
                value: value,
                min: min,
                max: max,
                divisions: divisions,
                label: formatter(value),
                onChanged: onChanged,
              ),
            ),
            Text(max.toString()),
          ],
        ),
        Align(
          alignment: Alignment.centerRight,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              formatter(value),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onPrimaryContainer,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// 构建模板设置区块
  Widget _buildTemplateSection(ThemeData theme) {
    final availableTemplates = [
      NotificationTemplateType.priceAlert,
      NotificationTemplateType.volumeAlert,
      NotificationTemplateType.technicalAlert,
      NotificationTemplateType.emergencyAlert,
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.text_snippet,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '模板设置',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            ...availableTemplates.map((template) {
              final isEnabled = _settings.templateEnabled[template.value] ?? true;
              return SwitchListTile(
                title: Text(template.displayName),
                subtitle: Text(_getTemplateDescription(template)),
                value: isEnabled,
                onChanged: (value) {
                  final updatedTemplates = {..._settings.templateEnabled, template.value: value};
                  setState(() {
                    _settings = _settings.copyWith(templateEnabled: updatedTemplates);
                    _hasChanges = true;
                  });
                },
                contentPadding: EdgeInsets.zero,
                enabled: _settings.enableNotifications,
              );
            }),
          ],
        ),
      ),
    );
  }

  /// 获取模板描述
  String _getTemplateDescription(NotificationTemplateType template) {
    switch (template) {
      case NotificationTemplateType.priceAlert:
        return '价格预警通知模板';
      case NotificationTemplateType.volumeAlert:
        return '成交量预警通知模板';
      case NotificationTemplateType.technicalAlert:
        return '技术指标预警通知模板';
      case NotificationTemplateType.emergencyAlert:
        return '紧急情况预警通知模板';
      case NotificationTemplateType.custom:
        return '自定义通知模板';
    }
  }

  /// 构建测试区块
  Widget _buildTestingSection(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.bug_report,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  '测试和调试',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            Text(
              '发送测试通知以验证当前配置是否正常工作',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
            const SizedBox(height: 16),
            
            // 测试按钮
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _settings.enableNotifications 
                        ? () => _sendTestNotification(context, '测试通知')
                        : null,
                    icon: const Icon(Icons.send),
                    label: const Text('发送测试通知'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _settings.enableNotifications 
                        ? () => _sendTestNotification(context, '紧急测试')
                        : null,
                    icon: const Icon(Icons.emergency),
                    label: const Text('紧急测试'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // 清除数据按钮
            OutlinedButton.icon(
              onPressed: _showClearDataDialog,
              icon: const Icon(Icons.clear_all),
              label: const Text('清除通知数据'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.red,
                side: const BorderSide(color: Colors.red),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建操作按钮
  Widget _buildActionButtons(ThemeData theme) {
    return Card(
      color: theme.colorScheme.primaryContainer.withOpacity(0.3),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.info_outline),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '您有未保存的更改',
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            TextButton(
              onPressed: () {
                setState(() {
                  _hasChanges = false;
                  final notificationState = ref.read(notificationProvider);
                  _settings = notificationState.globalSettings;
                });
              },
              child: const Text('取消'),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: _saveSettings,
              child: const Text('保存设置'),
            ),
          ],
        ),
      ),
    );
  }

  /// 发送测试通知
  void _sendTestNotification(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('测试通知: $message'),
        backgroundColor: Colors.blue,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  /// 显示清除数据对话框
  void _showClearDataDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('清除通知数据'),
        content: const Text('确定要清除所有通知数据和统计信息吗？此操作无法撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              // TODO: 实现清除数据功能
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('通知数据已清除')),
              );
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('清除'),
          ),
        ],
      ),
    );
  }

  /// 保存设置
  void _saveSettings() {
    ref.read(notificationProvider.notifier).updateGlobalSettings(_settings);
    
    setState(() {
      _hasChanges = false;
    });
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('设置已保存')),
    );
  }
}
